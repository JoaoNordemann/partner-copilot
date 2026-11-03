from datetime import date
from unittest.mock import Mock

import pytest

from partner_copilot.config import Settings
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.retrieval.retriever import Retriever
from partner_copilot.schemas import RetrievedDoc, Review


def review(identifier="review", **changes):
    return Review.model_validate(
        {
            "id": identifier,
            "restaurant_id": "rest_001",
            "text": "O pedido chegou atrasado.",
            "rating": 2,
            "created_at": "2026-11-01",
            "category": "pizza",
            "bairro": "Centro",
            "aspects": {"tempo_entrega": "neg"},
            **changes,
        }
    )


def test_candidate_budget_threshold_inclusive_and_fewer_than_k():
    store = Mock()
    store.query.return_value = [
        RetrievedDoc(review=review(str(i)), score=score)
        for i, score in enumerate([0.9, 0.5, 0.49, -0.2])
    ]
    retriever = Retriever(store, k=3, min_score=0.5)
    result = retriever.retrieve("entrega", "rest_001")
    store.query.assert_called_once_with("entrega", 6, {"restaurant_id": "rest_001"})
    assert [doc.score for doc in result] == [0.9, 0.5]
    store.query.return_value = [RetrievedDoc(review=review(str(i)), score=0.9) for i in range(6)]
    assert len(retriever.retrieve("entrega", "rest_001")) == 3
    store.query.return_value = [RetrievedDoc(review=review(), score=0.1)]
    assert retriever.retrieve("entrega", "rest_001") == []


def test_settings_and_combined_filters():
    store = Mock()
    store.query.return_value = []
    retriever = Retriever(store, settings=Settings(retrieval_k=4, retrieval_min_score=0.6))
    retriever.retrieve(
        "entrega",
        "rest_001",
        "tempo_entrega",
        start_date=date(2026, 10, 19),
        end_date=date(2026, 11, 1),
        category="pizza",
        city="São Paulo",
        bairro="Centro",
    )
    assert retriever.min_score == 0.6
    store.query.assert_called_once_with(
        "entrega",
        8,
        {
            "$and": [
                {"restaurant_id": "rest_001"},
                {"aspect_tempo_entrega": "neg"},
                {"category": "pizza"},
                {"city": "São Paulo"},
                {"bairro": "Centro"},
                {"created_at_int": {"$gte": 20261019}},
                {"created_at_int": {"$lte": 20261101}},
            ]
        },
    )


class GeometryEmbedder:
    model_name = "test/cosine-geometry"
    document_prefix = query_prefix = ""

    def embed_documents(self, texts):
        vectors = {"parallel": [1.0, 0.0], "orthogonal": [0.0, 1.0], "opposite": [-1.0, 0.0]}
        return [vectors[text] for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def test_cosine_scores_have_known_geometry_and_wrong_metric_is_rejected(tmp_path):
    store = ChromaStore(tmp_path / "vectors", embedder=GeometryEmbedder())
    store.upsert([review(name, text=name) for name in ["parallel", "orthogonal", "opposite"]])
    docs = store.query("query", 3)
    assert [doc.review.id for doc in docs] == ["parallel", "orthogonal", "opposite"]
    assert [doc.score for doc in docs] == pytest.approx([1.0, 0.0, -1.0], abs=1e-6)
    store.client.create_collection(
        "wrong_metric",
        metadata={
            "hnsw:space": "l2",
            "embedding_model": GeometryEmbedder.model_name,
        },
    )
    with pytest.raises(ValueError, match="cosine"):
        ChromaStore(tmp_path / "vectors", collection="wrong_metric", embedder=GeometryEmbedder())


def test_date_boundaries_restaurant_isolation_and_pipeline_abstention(tmp_path):
    store = ChromaStore(tmp_path / "dates", embedder=GeometryEmbedder())
    store.upsert(
        [
            review(identifier, text="parallel", created_at=day, restaurant_id=restaurant)
            for identifier, day, restaurant in [
                ("before", "2026-10-18", "rest_001"),
                ("start", "2026-10-19", "rest_001"),
                ("end", "2026-11-01", "rest_001"),
                ("after", "2026-11-02", "rest_001"),
                ("other", "2026-11-01", "rest_002"),
            ]
        ]
    )
    retriever = Retriever(store, k=8)
    dates = {"start_date": date(2026, 10, 19), "end_date": date(2026, 11, 1)}
    assert {doc.review.id for doc in retriever.retrieve("entrega", "rest_001", **dates)} == {
        "start",
        "end",
    }
    assert {
        doc.review.id
        for doc in retriever.retrieve("entrega", "rest_001", start_date=date(2026, 11, 2))
    } == {"after"}
    assert {
        doc.review.id
        for doc in retriever.retrieve("entrega", "rest_001", end_date=date(2026, 10, 18))
    } == {"before"}
    assert retriever.retrieve("entrega", "rest_001", category="sushi") == []
    llm = Mock()
    pipeline = RAGPipeline(retriever, llm)
    answer = pipeline.ask("entrega", "rest_001", start_date=date(2030, 1, 1))
    assert answer.sources == [] and answer.answer == "Sem avaliações relevantes para responder."
    llm.generate.assert_not_called()
    llm.generate.return_value = "Diagnóstico"
    assert set(pipeline.ask("entrega", "rest_001", **dates).sources) == {"start", "end"}


def test_inverted_date_window_fails_before_query():
    store = Mock()
    with pytest.raises(ValueError, match="start_date"):
        Retriever(store).retrieve(
            "entrega", "rest_001", start_date=date(2026, 11, 2), end_date=date(2026, 11, 1)
        )
    store.query.assert_not_called()
