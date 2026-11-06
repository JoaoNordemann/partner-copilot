import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from partner_copilot.api import create_app
from partner_copilot.api_models import APIError, APISettings, AskRequest, Timings
from partner_copilot.api_runtime import Resources, where_for
from partner_copilot.schemas import RetrievedDoc, Review


@pytest.fixture
def doc():
    return RetrievedDoc(
        review=Review(
            id="fixture_review",
            restaurant_id="rest_fixture",
            text="A tampa chegou aberta.",
            rating=2,
            created_at="2026-01-01",
            category="teste",
            bairro="Centro",
        ),
        score=0.8,
    )


def raw(identifier="fixture_review", quote="A tampa chegou aberta."):
    return json.dumps(
        {
            "abstem": False,
            "afirmacoes": [
                {
                    "texto": "A tampa chegou aberta.",
                    "fontes": [{"review_id": identifier, "trecho": quote}],
                }
            ],
        }
    )


class Index:
    def __init__(self, docs):
        self.docs = docs
        self.calls = 0

    def retrieve(self, request, timings):
        self.calls += 1
        timings.embedding_ms = 1
        timings.search_ms = 2
        timings.embedding_search_ms = 3
        return self.docs


class Model:
    def __init__(self, text, delay=0):
        self.text = text
        self.calls = 0
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.entered = threading.Event()

    def generate(self, prompt):
        self.calls += 1
        self.active += 1
        self.peak = max(self.active, self.peak)
        self.entered.set()
        try:
            time.sleep(self.delay)
            return self.text
        finally:
            self.active -= 1


def factory(index, model, backend_error=None):
    state = {}

    def build(settings, api):
        r = Resources(settings, api)
        r.index = index
        r.llm = model
        r.backend_error = backend_error
        r.menu = [{"restaurant_id": "rest_fixture", "name": "Fixture", "items": ["Item fixture"]}]
        r.components = {
            "index": {"status": "ready"},
            "embedder": {"status": "ready"},
            "llm": {"status": "unavailable" if backend_error else "ready"},
            "replay": {"status": "not_required"},
        }
        r.start = Mock()
        state["resources"] = r
        return r

    return build, state


def settings(**kw):
    return APISettings(_env_file=None, llm_backend="fake", **kw)


BODY = {"restaurant_id": "rest_fixture", "question": "O que houve com a tampa?"}


def test_startup_once_routes_metadata_and_menus(doc):
    index, model = Index([doc]), Model(raw())
    build, state = factory(index, model)
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/restaurants").json()["restaurants"][0]["items"] == ["Item fixture"]
        assert client.get("/restaurants/rest_fixture/items").json()["items"] == ["Item fixture"]
        for path in ["/ask", "/v1/ask"]:
            response = client.post(path, json=BODY)
            assert response.status_code == 200
            body = response.json()
            assert body["result"]["afirmacoes"][0]["fontes"][0]["review_id"] == "fixture_review"
            assert (
                body["metadata"]["is_simulation"] is True
                and body["metadata"]["llm_called"] is False
            )
            assert body["metadata"]["backend_called"] is True
            assert body["metadata"]["timings_ms"]["embedding_ms"] == 1
            assert response.headers["X-Request-ID"] == body["metadata"]["request_id"]
        state["resources"].start.assert_called_once()
        assert model.calls == index.calls == 2


@pytest.mark.parametrize(
    "change",
    [
        {"question": " "},
        {"question": "x" * 2001},
        {"k": 13},
        {"k": True},
        {"k": "8"},
        {"filters": {"aspect": "unknown"}},
        {"filters": {"item": " "}},
        {"filters": {"start_date": "2026-02-02", "end_date": "2026-01-01"}},
        {"filters": {"start_date": 123}},
        {"backend": "real"},
    ],
)
def test_boundary_rejects_before_retrieval(doc, change):
    index, model = Index([doc]), Model(raw())
    build, _ = factory(index, model)
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        response = client.post("/ask", json={**BODY, **change})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        assert index.calls == model.calls == 0


def test_missing_restaurant_and_malformed_json(doc):
    index, model = Index([doc]), Model(raw())
    build, _ = factory(index, model)
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        assert client.post("/ask", json={"question": "teste"}).status_code == 422
        assert (
            client.post(
                "/ask", content="{invalid", headers={"Content-Type": "application/json"}
            ).status_code
            == 422
        )
        assert index.calls == model.calls == 0


def test_empty_context_skips_unavailable_model(doc):
    index, model = Index([]), Model(raw())
    build, _ = factory(index, model, APIError(503, "model_unavailable"))
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        assert client.get("/health").status_code == 503
        response = client.post("/ask", json=BODY)
        assert response.status_code == 200
        assert response.json()["abstention_reason"] == "retriever_empty"
        assert not response.json()["metadata"]["backend_called"]
        assert model.calls == 0


@pytest.mark.parametrize(
    "text,reason",
    [
        (raw("invented"), "invalid_source_id"),
        (raw(quote="invented"), "quote_mismatch"),
        ("SECRET_RAW_INVALID_JSON", "invalid_schema"),
    ],
)
def test_contract_rejection_never_returns_raw(doc, text, reason):
    build, _ = factory(Index([doc]), Model(text))
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        response = client.post("/ask", json=BODY)
        assert response.status_code == 502
        assert response.json()["error"]["details"]["reason"] == reason
        assert "result" not in response.json() and "raw_response" not in response.text
        assert "SECRET_RAW" not in response.text and "invented" not in response.text


def test_real_backend_unavailable_without_fallback(doc):
    build, _ = factory(Index([doc]), None, APIError(503, "model_unavailable"))
    with TestClient(
        create_app(APISettings(_env_file=None, llm_backend="real"), resources_factory=build)
    ) as client:
        response = client.post("/ask", json=BODY)
        assert response.status_code == 503
        assert response.json()["backend"] == "real"
        assert response.json()["error"]["code"] == "model_unavailable"


def test_startup_attempts_each_component_once_and_survives_gpu_failure(monkeypatch):
    from partner_copilot import api_runtime
    from partner_copilot.config import Settings

    embedder = Mock()
    index = SimpleNamespace(store=SimpleNamespace(count=lambda: 1), restaurants=lambda: [])
    e = Mock(return_value=embedder)
    i = Mock(return_value=index)
    llm = Mock(side_effect=RuntimeError("SECRET_CUDA_DETAIL"))
    monkeypatch.setattr(api_runtime, "load_embedder", e)
    monkeypatch.setattr(api_runtime, "load_index", i)
    monkeypatch.setattr(api_runtime, "load_backend", llm)
    r = Resources(Settings(_env_file=None), APISettings(_env_file=None, llm_backend="real"))
    r.start()
    r.start()
    assert not r.healthy() and r.components["llm"]["error"] == "model_unavailable"
    assert "SECRET_CUDA_DETAIL" not in json.dumps(r.components)
    e.assert_called_once()
    i.assert_called_once()
    llm.assert_called_once()


def test_concurrent_generation_is_serialized(doc):
    model = Model(raw(), delay=0.03)
    build, _ = factory(Index([doc]), model)
    with (
        TestClient(create_app(settings(), resources_factory=build)) as client,
        ThreadPoolExecutor(3) as pool,
    ):
        responses = list(pool.map(lambda _: client.post("/ask", json=BODY), range(3)))
        assert all(r.status_code == 200 for r in responses)
        assert model.calls == 3 and model.peak == 1


def test_timeout_does_not_release_gpu_or_start_expired_queued_request(doc):
    model = Model(raw(), delay=0.3)
    build, _ = factory(Index([doc]), model)
    with TestClient(
        create_app(settings(api_request_timeout_s=0.04), resources_factory=build)
    ) as client:
        first = client.post("/ask", json=BODY)
        assert first.status_code == 504 and model.calls == 1
        second = client.post("/ask", json=BODY)
        assert second.status_code == 504 and model.calls == 1
        time.sleep(0.35)
        assert model.calls == 1 and model.peak == 1
        assert client.get("/health").json()["active_requests"] == 0


def test_queue_capacity_is_bounded(doc):
    model = Model(raw(), delay=0.1)
    build, _ = factory(Index([doc]), model)
    with (
        TestClient(create_app(settings(api_max_pending=1), resources_factory=build)) as client,
        ThreadPoolExecutor(1) as pool,
    ):
        first = pool.submit(client.post, "/ask", json=BODY)
        assert model.entered.wait(1)
        second = client.post("/ask", json=BODY)
        assert second.status_code == 429 and second.json()["error"]["code"] == "resource_busy"
        assert first.result().status_code == 200


def test_logs_have_metadata_but_no_question_or_output(doc, monkeypatch):
    from partner_copilot import api

    logs = []
    monkeypatch.setattr(api.logger, "info", lambda message: logs.append(json.loads(message)))
    build, _ = factory(Index([doc]), Model(raw()))
    with TestClient(create_app(settings(), resources_factory=build)) as client:
        client.post("/ask", json={**BODY, "question": "UNIQUE_PRIVATE_QUESTION"})
    serialized = json.dumps(logs)
    assert "UNIQUE_PRIVATE_QUESTION" not in serialized and "A tampa chegou aberta" not in serialized
    assert logs[-1]["request_id"] and logs[-1]["restaurant_id"] == "rest_fixture"
    assert logs[-1]["prompt_version"] == "partner-copilot-v3"


def test_temporal_and_aspect_filters_are_numeric_and_scoped():
    r = AskRequest(
        **BODY,
        filters={
            "aspect": "embalagem",
            "item": "Caixa",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    )
    filters = where_for(r)["$and"]
    assert {"restaurant_id": "rest_fixture"} in filters
    assert {"aspect_embalagem": "neg"} in filters
    assert {"created_at_int": {"$gte": 20260101}} in filters
    assert {"created_at_int": {"$lte": 20260131}} in filters


def test_cpu_stage_timers_measure_each_interval_directly(doc, monkeypatch):
    from partner_copilot import api_runtime
    from partner_copilot.config import Settings

    clock = iter([1.0, 2.0, 5.0, 7.0, 11.0, 15.0])
    monkeypatch.setattr(api_runtime, "perf_counter", lambda: next(clock))
    embedder = SimpleNamespace(embed_query=Mock(return_value=[1.0, 0.0]))
    metadata = doc.review.model_dump(mode="json")
    metadata["aspects_json"] = "{}"
    collection = SimpleNamespace(
        query=Mock(
            return_value={
                "ids": [["fixture_review"]],
                "documents": [[doc.review.text]],
                "metadatas": [[metadata]],
                "distances": [[0.2]],
            }
        )
    )
    store = SimpleNamespace(count=lambda: 1, col=collection)
    index = api_runtime.CPUIndex(store, embedder, Settings(_env_file=None))
    timing = Timings()
    result = index.retrieve(AskRequest(**BODY), timing)
    assert len(result) == 1
    assert timing.embedding_ms == 3000 and timing.search_ms == 4000
    assert timing.embedding_search_ms == 14000
    assert collection.query.call_args.kwargs["where"] == {"restaurant_id": "rest_fixture"}
    embedder.embed_query.assert_called_once()
