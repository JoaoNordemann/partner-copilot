import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from partner_copilot.api import create_app
from partner_copilot.api_models import APISettings
from partner_copilot.generation.output import parse_generation, parser_identity
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.schemas import RetrievedDoc, Review


def dump(path, value, jsonl=False):
    text = (
        (json.dumps(value, ensure_ascii=False) + "\n")
        if not jsonl
        else "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in value)
    )
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def recording(tmp_path):
    review = Review(
        id="fixture_source",
        restaurant_id="rest_fixture",
        item="Caixa",
        text="A caixa chegou aberta.",
        rating=2,
        created_at="2026-01-01",
        category="teste",
        bairro="Centro",
    )
    raw = (
        json.dumps(
            {
                "abstem": False,
                "afirmacoes": [
                    {
                        "texto": "A caixa chegou aberta.",
                        "fontes": [{"review_id": review.id, "trecho": review.text}],
                    }
                ],
            }
        )
        + "."
    )
    parsed = parse_generation(
        raw, [RetrievedDoc(review=review, score=0.9)], parser_version="parser-v3"
    )
    corpus_sha = dump(tmp_path / "corpus.jsonl", [review.model_dump(mode="json")], True)
    row = {
        "backend": "real_mistral_nf4",
        "cohort": "new",
        "experiment_id": "fixture-run",
        "question_id": "n99",
        "pergunta": "Como estava a caixa?",
        "filtros": {"restaurant_id": "rest_fixture", "item": "Caixa"},
        "settings": {
            "prompt_version": "partner-copilot-v3",
            "parser_version": "parser-v3",
            "retrieval_k": 8,
            "context_k": 8,
            "retrieval_min_score": 0.25,
            "max_new_tokens": 512,
            "temperature": 0,
            "generation_seed": 42,
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "embedding_prefix_mode": "auto",
            "llm_model_id": "mistralai/Mistral-7B-Instruct-v0.2",
        },
        "prompt_sha256": hashlib.sha256(
            load_prompt_template("partner-copilot-v3").encode()
        ).hexdigest(),
        "parser_sha256": parser_identity("parser-v3")["parser_sha256"],
        "snapshot_sha256_lf": {
            "corpus": hashlib.sha256(
                (tmp_path / "corpus.jsonl").read_text(encoding="utf-8").encode()
            ).hexdigest()
        },
        "llm_called": True,
        "context": [{"review_id": review.id, "text": review.text, "score": 0.9}],
        "retrieved": [{"review_id": review.id}],
        "raw_response": raw,
        "error": None,
        "answer": {
            "answer": parsed.answer,
            "sources": parsed.sources,
            "abstained": False,
            "abstention_reason": None,
        },
        "environment": {"source_commit": "fixture-commit", "gpu_names": ["Tesla T4"]},
        "generation_metrics": {"latency_ms": 8000},
    }
    source_sha = dump(tmp_path / "source.jsonl", [row], True)
    approval = {
        "experiment": "v3-new",
        "question_id": "n99",
        "status": "completed",
        "origin": "human",
        "support": "sustentada",
        "answers_question": "sim",
        "reviewer": "Fixture reviewer",
        "method": "Invented unit-test fixture, not a real human approval",
    }
    approval_sha = dump(tmp_path / "approval.jsonl", [approval], True)
    entry = {
        "source_file": "source.jsonl",
        "source_sha256": source_sha,
        "question_id": "n99",
        "approval_file": "approval.jsonl",
        "approval_sha256": approval_sha,
        "corpus_file": "corpus.jsonl",
        "corpus_sha256": corpus_sha,
    }
    catalog = tmp_path / "catalog.json"
    dump(catalog, {"schema_version": "replay-catalog-v1", "entries": [entry]})
    return catalog, entry, row, approval


def app_for(path):
    return create_app(APISettings(_env_file=None, llm_backend="replay", api_replay_catalog=path))


BODY = {
    "restaurant_id": "rest_fixture",
    "question": "Como estava a caixa?",
    "filters": {"item": "Caixa"},
}


def test_replay_is_labelled_and_uses_saved_context_not_live_models(recording, monkeypatch):
    from partner_copilot import api_runtime

    catalog, _, _, _ = recording
    monkeypatch.setattr(
        api_runtime, "load_embedder", lambda *a: pytest.fail("Embedding must not load")
    )
    monkeypatch.setattr(api_runtime, "load_backend", lambda *a: pytest.fail("Model must not load"))
    with TestClient(app_for(catalog)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/restaurants").json()["restaurants"][0]["items"] == ["Caixa"]
        response = client.post("/ask", json=BODY)
        assert response.status_code == 200
        meta = response.json()["metadata"]
        assert meta["is_replay"] and not meta["llm_called"] and meta["backend_called"]
        assert meta["context_origin"] == "recorded_eval_snapshot"
        assert meta["timings_ms"]["embedding_search_ms"] is None
        assert meta["timings_ms"]["generation_ms"] is None
        assert meta["source_run"]["historical_metrics"]["latency_ms"] == 8000
        assert meta["timings_ms"]["total_ms"] < 8000
        assert "REPLAY" in meta["mode_label"]
        # Files are cached once at startup; disk changes cannot replace the in-memory recording.
        (catalog.parent / "source.jsonl").write_text("broken after startup", encoding="utf-8")
        assert client.post("/ask", json=BODY).status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        {"question": "Outra pergunta"},
        {"k": 5},
        {"filters": {"item": "Outro"}},
        {"restaurant_id": "rest_other"},
    ],
)
def test_replay_requires_exact_full_request_key(recording, change):
    with TestClient(app_for(recording[0])) as client:
        response = client.post("/ask", json={**BODY, **change})
        assert (
            response.status_code == 404 and response.json()["error"]["code"] == "replay_not_found"
        )


def test_replay_rejects_wrong_hash_or_unapproved_content(recording):
    catalog, entry, row, approval = recording
    entry["source_sha256"] = "0" * 64
    dump(catalog, {"schema_version": "replay-catalog-v1", "entries": [entry]})
    with TestClient(app_for(catalog)) as client:
        assert client.get("/health").status_code == 503
        assert client.post("/ask", json=BODY).status_code == 409
    entry["source_sha256"] = dump(catalog.parent / "source.jsonl", [row], True)
    approval["support"] = "sem_suporte"
    entry["approval_sha256"] = dump(catalog.parent / "approval.jsonl", [approval], True)
    dump(catalog, {"schema_version": "replay-catalog-v1", "entries": [entry]})
    with TestClient(app_for(catalog)) as client:
        response = client.post("/ask", json=BODY)
        assert (
            response.status_code == 503 and response.json()["error"]["code"] == "replay_unavailable"
        )


def test_empty_catalog_is_unavailable_not_fake_success(tmp_path):
    catalog = tmp_path / "empty.json"
    dump(catalog, {"schema_version": "replay-catalog-v1", "entries": []})
    with TestClient(app_for(catalog)) as client:
        assert client.get("/health").status_code == 503
        assert client.post("/ask", json=BODY).status_code == 503
