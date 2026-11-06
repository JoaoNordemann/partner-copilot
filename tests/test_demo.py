"""UI presentation and API client tests without Gradio, torch or downloads."""

import json
import runpy
from pathlib import Path

import httpx

from partner_copilot.demo import DemoClient, cards, load_history, render_answer, render_history

ROOT = Path(__file__).resolve().parents[1]


def response():
    return {
        "result": {
            "abstem": False,
            "afirmacoes": [
                {
                    "texto": "Boa compra.",
                    "fontes": [{"review_id": "fixture", "trecho": "Boa compra."}],
                }
            ],
        },
        "answer": "Boa compra. [fixture]",
        "sources": ["fixture"],
        "source_reviews": [
            {
                "id": "fixture",
                "restaurant_id": "rest_fixture",
                "rating": 2,
                "created_at": "2026-01-01",
                "category": "teste",
                "bairro": "Centro",
                "text": "Boa compra. Mas o gosto ficou ruim no final.",
            }
        ],
        "abstained": False,
        "abstention_reason": None,
        "metadata": {
            "request_id": "fixture",
            "backend": "replay",
            "is_replay": True,
            "is_simulation": False,
            "mode_label": "REPLAY",
            "backend_called": True,
            "llm_called": False,
            "context_origin": "recorded_eval_snapshot",
            "retrieved_documents": 1,
            "context_documents": 1,
            "timings_ms": {},
        },
    }


def test_each_claim_shows_complete_review_not_only_quote():
    value = response()
    html = render_answer(value)
    assert "Boa compra." in html and "Mas o gosto ficou ruim no final." in html
    assert "Review completa" in html and "RESPOSTA GRAVADA" in html
    assert "DADOS SINTÉTICOS" in html and "partner-copilot-v3" in html


def test_html_is_escaped_in_reviews_and_claims():
    html = cards(
        [{"texto": "<script>alert(1)</script>", "review_ids": ["fixture"]}],
        [
            {
                "id": "fixture",
                "text": '<img src=x onerror="alert(1)">',
                "rating": 2,
                "created_at": "2026-01-01",
            }
        ],
    )
    assert "<script>" not in html and "<img " not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html


def test_abstention_is_explicit():
    value = response()
    value.update(
        result={"abstem": True, "afirmacoes": []},
        sources=[],
        source_reviews=[],
        abstained=True,
        abstention_reason="llm_insufficient_evidence",
    )
    assert "ABSTENÇÃO" in render_answer(value)


def test_client_sends_scoped_filters_and_renders(monkeypatch):
    seen = []

    def handle(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=response())

    client = DemoClient("http://fixture", transport=httpx.MockTransport(handle))
    html, value = client.ask("rest_fixture", "Pergunta", "2026-01-01", "", "embalagem", "Item", 5)
    assert seen[0]["restaurant_id"] == "rest_fixture"
    assert seen[0]["filters"] == {
        "start_date": "2026-01-01",
        "end_date": None,
        "aspect": "embalagem",
        "item": "Item",
    }
    assert value["sources"] == ["fixture"] and "Review completa" in html


def test_contract_errors_are_not_rendered_as_answers():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            502,
            json={"error": {"code": "generation_contract_failed"}, "raw_response": "PRIVATE_RAW"},
        )
    )
    html, data = DemoClient("http://fixture", transport=transport).ask(
        "rest_fixture", "P", "", "", None, None, 8
    )
    assert data["error"] == "generation_contract_failed"
    assert "PRIVATE_RAW" not in html and "PRIVATE_RAW" not in str(data)


def test_history_is_reproducible_and_failure_retains_entire_context():
    generated = runpy.run_path(str(ROOT / "scripts/build_demo_examples.py"))["render"]()
    assert generated == (ROOT / "configs/demo-examples.json").read_text(encoding="utf-8")
    history = load_history(ROOT / "configs/demo-examples.json")
    assert set(history) == {"success", "abstention", "failure"}
    html = render_history(history["failure"])
    assert "Falha confirmada por João" in html and "rev_001172" in html
    for review in history["failure"]["full_context_reviews"]:
        from html import escape

        assert escape(review["text"], quote=True) in html
    assert "ABSTENÇÃO" in render_history(history["abstention"])


def test_unavailable_api_keeps_history_accessible():
    transport = httpx.MockTransport(lambda _: httpx.Response(503, json={"backend": "replay"}))
    menu, status = DemoClient("http://fixture", transport=transport).menu()
    assert menu == [] and "históricos" in status
