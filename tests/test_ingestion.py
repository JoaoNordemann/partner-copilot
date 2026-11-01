import json
from datetime import date

import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from partner_copilot.ingestion.indexer import ingest_reviews
from partner_copilot.ingestion.loaders import load_reviews
from partner_copilot.retrieval.store import ChromaStore
from partner_copilot.schemas import Review


class TinyEmbedding(EmbeddingFunction[Documents]):
    def __init__(self) -> None:
        pass

    def get_config(self) -> dict[str, str]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, str]) -> "TinyEmbedding":
        return TinyEmbedding()

    def __call__(self, input: Documents) -> Embeddings:
        return [[1.0, 0.5, 0.25] for _ in input]

    @staticmethod
    def name() -> str:
        return "tiny-test-embedding"


def make_review(review_id="rev_001", **changes):
    payload = {
        "id": review_id,
        "restaurant_id": "rest_002",
        "text": "Entrega atrasada.",
        "rating": 2,
        "created_at": "2026-10-30",
        "category": "hamburguer",
        "bairro": "Vila Ema",
        "aspects": {"tempo_entrega": "neg"},
    }
    return Review.model_validate(payload | changes)


def write_reviews(path, reviews):
    path.write_text("\n".join(row.model_dump_json() for row in reviews), encoding="utf-8")


def test_date_is_derived_and_aspects_are_independent():
    first, second = make_review(), make_review(aspects={})
    assert first.created_at_int == 20261030
    assert first.model_copy(update={"created_at": date(2026, 11, 1)}).created_at_int == 20261101
    assert second.aspects == {}
    assert first.aspects == {"tempo_entrega": "neg"}


def test_persistent_ingestion_is_idempotent_and_filters_metadata(tmp_path):
    path = tmp_path / "reviews.jsonl"
    rows = [
        make_review(),
        make_review("rev_002", created_at="2026-09-01"),
        make_review("rev_003", restaurant_id="rest_001", category="pizza"),
    ]
    write_reviews(path, rows)
    store = ChromaStore(tmp_path / "chroma", "tiny", embedding_function=TinyEmbedding())
    assert ingest_reviews(path, store, batch_size=2) == 3
    assert ingest_reviews(path, store, batch_size=2) == 3
    assert store.col.count() == 3
    reopened = ChromaStore(tmp_path / "chroma", "tiny", embedding_function=TinyEmbedding())
    docs = reopened.query(
        "atraso",
        8,
        {
            "$and": [
                {"restaurant_id": "rest_002"},
                {"category": "hamburguer"},
                {"bairro": "Vila Ema"},
                {"created_at_int": {"$gte": 20261001}},
                {"created_at_int": {"$lte": 20261031}},
                {"aspect_tempo_entrega": "neg"},
            ]
        },
    )
    assert [doc.review for doc in docs] == [rows[0]]
    assert docs[0].score == pytest.approx(1.0)
    assert reopened.query("atraso", 8, {"restaurant_id": "absent"}) == []
    changed = make_review(text="Nova avaliação.", aspects={"sabor": "pos"})
    reopened.upsert([changed])
    assert (
        reopened.query("nova", 8, {"restaurant_id": "rest_002", "created_at_int": 20261030})[
            0
        ].review
        == changed
    )
    assert (
        reopened.query(
            "atraso",
            8,
            {
                "aspect_tempo_entrega": "neg",
                "created_at_int": 20261030,
                "restaurant_id": "rest_002",
            },
        )
        == []
    )
    assert reopened.col.count() == 3
    with pytest.raises(ValueError, match="embedding model"):
        ChromaStore(tmp_path / "chroma", "other-model", embedding_function=TinyEmbedding())


def test_empty_store_and_empty_upsert(tmp_path):
    store = ChromaStore(tmp_path / "empty", "tiny", embedding_function=TinyEmbedding())
    store.upsert([])
    assert store.query("anything", 5) == []
    with pytest.raises(ValueError, match="positive"):
        store.query("anything", 0)


def test_loader_reports_file_and_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("\n" + json.dumps({"id": "invalid"}), encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad.jsonl: line 2"):
        list(load_reviews(path))
    path.write_text("{broken json", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        list(load_reviews(path))


def test_duplicate_ids_fail_and_invalid_batch_is_rejected(tmp_path):
    class MemoryStore:
        def upsert(self, reviews):
            pass

    path = tmp_path / "duplicates.jsonl"
    write_reviews(path, [make_review(), make_review()])
    with pytest.raises(ValueError, match="duplicate review id"):
        ingest_reviews(path, MemoryStore())
    with pytest.raises(ValueError, match="positive"):
        ingest_reviews(path, MemoryStore(), batch_size=0)
