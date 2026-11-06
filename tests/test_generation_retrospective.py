import json

import pytest

from partner_copilot.evaluation.retrospective import inspect_saved, summarize_saved
from partner_copilot.schemas import Review


def fixture_row(raw, *, accepted=False, called=True):
    review = Review(
        id="rev_000001",
        restaurant_id="rest_001",
        text="Sabor ruim. Bom custo-beneficio.",
        rating=2,
        created_at="2026-11-01",
        category="comida",
        bairro="Centro",
    )
    row = {
        "question_id": "q01",
        "llm_called": called,
        "raw_response": raw,
        "context": [{"review_id": review.id, "text": review.text, "score": 0.5}] if called else [],
        "context_ids": [review.id] if called else [],
        "relevant_ids": [review.id],
        "deve_abster": False,
        "answer": {"abstained": False} if accepted else None,
        "error": None if accepted else {"type": "GenerationContractError"},
    }
    return row, {review.id: review}


def test_valid_ids_do_not_imply_valid_output_contract():
    row, reviews = fixture_row("Afirmacao sem fonte\nOutra afirmacao [rev_000001]")
    result = inspect_saved(row, reviews, "parser-v1")
    assert result["ids_in_context"] is True
    assert result["parser_accepted"] is False
    assert result["schema_valid"] is None


def test_literal_quote_does_not_certify_factual_support():
    raw = json.dumps(
        {
            "abstem": False,
            "afirmacoes": [
                {
                    "texto": "O sabor e bom.",
                    "fontes": [{"review_id": "rev_000001", "trecho": "Bom custo-beneficio."}],
                }
            ],
        }
    )
    row, reviews = fixture_row(raw, accepted=True)
    result = inspect_saved(row, reviews, "parser-v3")
    assert result["schema_valid"] and result["ids_in_context"] and result["quotes_literal"]
    assert result["parser_accepted"] is True
    assert result["content_supported"] is None


def test_no_llm_does_not_inflate_model_or_id_denominators():
    row, reviews = fixture_row(None, called=False)
    result = summarize_saved([row], reviews, "parser-v1")
    assert result["no_llm"] == 1 and result["llm_outputs"] == 0
    assert result["accepted"] == {"passed": 0, "applicable": 0}
    assert result["ids"] == {"passed": 0, "applicable": 0}


def test_abstention_has_no_vacuously_valid_sources():
    row, reviews = fixture_row('{"abstem":true,"afirmacoes":[]}', accepted=True)
    result = inspect_saved(row, reviews, "parser-v3")
    assert result["parser_accepted"] is True
    assert result["ids_in_context"] is result["quotes_literal"] is None


def test_saved_acceptance_and_duplicate_ids_must_match():
    row, reviews = fixture_row("Afirmacao [rev_000001]", accepted=False)
    with pytest.raises(ValueError, match="Saved acceptance"):
        summarize_saved([row], reviews, "parser-v1")
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_saved([row, row], reviews, "parser-v1")
