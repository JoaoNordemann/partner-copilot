import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from partner_copilot.evaluation import final_v3
from partner_copilot.evaluation.structured import VerificationQuestion
from partner_copilot.generation.contracts import GenerationContractError, InvalidCitationError
from partner_copilot.generation.output import parse_generation, parser_identity
from partner_copilot.generation.output_v3 import (
    QuoteMismatchError,
    decode_output,
    inspect_generation,
)
from partner_copilot.schemas import RetrievedDoc
from test_generation_evaluation import FakeLLM
from test_generation_versions import document

ROOT = Path(__file__).resolve().parents[1]


def payload(text="O adesivo se soltou.", identifier="fonte_a", quote="O adesivo se soltou"):
    return json.dumps(
        {
            "abstem": False,
            "afirmacoes": [{"texto": text, "fontes": [{"review_id": identifier, "trecho": quote}]}],
        }
    )


def test_first_complete_object_preserves_nested_braces_and_records_suffix():
    raw = payload(text="O adesivo se soltou; caractere literal }.") + "\nFonte adicional ignorada"
    result = parse_generation(raw, [document()], parser_version="parser-v3")
    assert result.sources == ["fonte_a"]
    assert "caractere literal }" in result.answer
    d = inspect_generation(raw, [document()])
    assert d["schema_valid"] and d["parser_accepted"] and d["quotes_literal"]
    assert d["trailing_text_ignored"] and d["ignored_suffix_chars"] > 0
    assert decode_output(raw).ignored_suffix == "\nFonte adicional ignorada"


@pytest.mark.parametrize(
    "raw",
    [
        'prefix {"abstem":true,"afirmacoes":[]}',
        '```json\n{"abstem":true,"afirmacoes":[]}\n```',
        '{"abstem":false,"afirmacoes":[]}',
        '{"abstem":"true","afirmacoes":[]}',
        '{"abstem":true,"abstem":false,"afirmacoes":[]}',
        '{"abstem":true,"afirmacoes":NaN}',
        '{"abstem":true,"afirmacoes":[],"extra":1}',
        (
            '{"abstem":true,"afirmacoes":[{"texto":"x","fontes":'
            '[{"review_id":"fonte_a","trecho":"O adesivo"}]}]}'
        ),
    ],
)
def test_invalid_schema_or_inconsistent_abstention_is_rejected(raw):
    with pytest.raises(GenerationContractError):
        parse_generation(raw, [document()], parser_version="parser-v3")


def test_literal_quote_must_belong_to_the_cited_sent_review():
    with pytest.raises(QuoteMismatchError):
        parse_generation(
            payload(quote="o adesivo se soltou"), [document()], parser_version="parser-v3"
        )
    second = document().model_copy(
        update={
            "review": document().review.model_copy(
                update={"id": "fonte_b", "text": "A tampa veio solta."}
            )
        }
    )
    with pytest.raises(QuoteMismatchError):
        parse_generation(
            payload(quote="A tampa veio solta"), [document(), second], parser_version="parser-v3"
        )
    with pytest.raises(InvalidCitationError):
        parse_generation(payload(identifier="fora"), [document()], parser_version="parser-v3")
    with pytest.raises(GenerationContractError):
        parse_generation(payload(quote=" "), [document()], parser_version="parser-v3")


def test_quote_existence_does_not_prove_entailment_or_semantic_abstention():
    raw = payload(text="Houve um exame laboratorial.")
    d = inspect_generation(raw, [document()])
    assert d["parser_accepted"] and d["quotes_literal"]
    assert d["content_supported"] is None  # Real excerpt can still be irrelevant.
    # Structural consistency cannot infer abstention from natural-language prose.
    result = parse_generation(
        payload(text="Nao ha informacao do CNPJ."), [document()], parser_version="parser-v3"
    )
    assert not result.abstained


def test_final_runner_uses_eight_docs_and_no_retry_with_invented_fixtures(tmp_path, monkeypatch):
    docs = [
        RetrievedDoc(review=document().review.model_copy(update={"id": f"fonte_{i}"}), score=0.8)
        for i in range(1, 10)
    ]
    questions = [
        VerificationQuestion(
            id="n11",
            pergunta="Fixture adesivo",
            filtros={"restaurant_id": "rest_fixture"},
            relevantes=["fonte_8"],
            deve_abster=False,
            criterio="Fixture",
        ),
        VerificationQuestion(
            id="n12",
            pergunta="Fixture sem dados",
            filtros={"restaurant_id": "rest_fixture"},
            relevantes=[],
            deve_abster=True,
            criterio="Fixture",
        ),
    ]
    settings = final_v3.final_settings()
    manifest = {
        "prompt_version": settings.prompt_version,
        "parser_version": settings.parser_version,
    }
    (tmp_path / "manifest.json").write_text("{}")
    monkeypatch.setattr(
        final_v3,
        "load_final_set",
        lambda *args: (questions, [d.review for d in docs], manifest, {}),
    )
    retriever = Mock()
    retriever.retrieve.side_effect = lambda query, *args, **kwargs: (
        docs if query == "Fixture adesivo" else []
    )

    class FixtureLLM(FakeLLM):
        def generate_with_metrics(self, prompt, max_new_tokens=None):
            result = super().generate_with_metrics(prompt, max_new_tokens)
            return type(result)(payload(identifier="fonte_8") + "\nEXTRA", result.metrics)

    llm = FixtureLLM()
    output = tmp_path / "result.jsonl"
    rows = final_v3.run_final_v3(
        "new", output, tmp_path, tmp_path, settings, retriever, lambda: llm, environment={}
    )
    assert llm.calls == 1 and len(rows[0]["context_ids"]) == 8
    assert rows[0]["context_ids"][-1] == "fonte_8" and rows[0]["diagnostics"]["quotes_literal"]
    assert rows[1]["answer"]["abstained"] and not rows[1]["llm_called"]
    assert all(row["corrective_calls"] == 0 and not row["contaminated"] for row in rows)
    summary = final_v3.summarize_final(rows, ["n11", "n12"], 1)
    assert summary["complete"] and summary["quotes_literal"]["numerator"] == 1
    assert summary["trailing_text_ignored"] == 1 and summary["content_supported"] is None
    before = output.read_bytes()
    final_v3.run_final_v3(
        "new",
        output,
        tmp_path,
        tmp_path,
        settings,
        retriever,
        lambda: pytest.fail("Must not load"),
        environment={},
        resume=True,
    )
    assert output.read_bytes() == before and llm.calls == 1


def test_frozen_protocol_counts_without_exploratory_generation():
    folder = ROOT / "data/eval/v3-final-check"
    old = ROOT / "data/eval/human-v2"
    for cohort, size in (("new", 10), ("contaminated", 30)):
        questions, corpus, _, _ = final_v3.load_final_set(cohort, folder, old)
        assert len(questions) == size and len(corpus) == 100
    assert parser_identity("parser-v3")["parser_sha256"]


def test_diagnostics_validate_only_sent_chunk_not_unsent_full_review(tmp_path, monkeypatch):
    sent = document()
    full = sent.review.model_copy(update={"text": "Texto fora do chunk. O adesivo se soltou."})
    question = VerificationQuestion(
        id="n11",
        pergunta="Fixture chunk",
        filtros={"restaurant_id": "rest_fixture"},
        relevantes=["fonte_a"],
        deve_abster=False,
        criterio="Fixture",
    )
    settings = final_v3.final_settings()
    manifest = {
        "prompt_version": settings.prompt_version,
        "parser_version": settings.parser_version,
    }
    (tmp_path / "manifest.json").write_text("{}")
    monkeypatch.setattr(
        final_v3, "load_final_set", lambda *args: ([question], [full], manifest, {})
    )
    retriever = Mock()
    retriever.retrieve.return_value = [sent]

    class FixtureLLM(FakeLLM):
        def generate_with_metrics(self, prompt, max_new_tokens=None):
            result = super().generate_with_metrics(prompt, max_new_tokens)
            return type(result)(payload(quote="Texto fora do chunk."), result.metrics)

    rows = final_v3.run_final_v3(
        "new",
        tmp_path / "result.jsonl",
        tmp_path,
        tmp_path,
        settings,
        retriever,
        lambda: FixtureLLM(),
        environment={},
    )
    assert rows[0]["error"]["code"] == "evidence_quote_not_found"
    assert rows[0]["diagnostics"]["quotes_literal"] is False
