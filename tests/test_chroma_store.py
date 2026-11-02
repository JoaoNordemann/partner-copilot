import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from partner_copilot.config import Settings
from partner_copilot.ingestion.chroma_store import ChromaStore, model_collection_name
from partner_copilot.retrieval.store import ChromaStore as LegacyChromaStore
from partner_copilot.schemas import Review


class FixedEmbedder:
    def __init__(self, model="test/multilingual", document_prefix="", query_prefix=""):
        self.model_name = model
        self.document_prefix = document_prefix
        self.query_prefix = query_prefix
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        self.calls += 1
        return [1.0, 0.0, 0.0]


def review(review_id="rev_001", **changes):
    return Review.model_validate(
        {
            "id": review_id,
            "restaurant_id": "rest_001",
            "text": "Entrega atrasada.",
            "rating": 2,
            "created_at": "2026-11-01",
            "category": "pizza",
            "bairro": "Centro",
            **changes,
        }
    )


def test_default_path_and_model_aware_name_come_from_settings(tmp_path):
    settings = Settings(chroma_path=tmp_path / "configured", chroma_collection="restaurant_reviews")
    store = ChromaStore(settings=settings)
    assert store.path == settings.chroma_path
    assert "paraphrase-multilingual-minilm" in store.collection_name
    assert 3 <= len(store.collection_name) <= 63
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*[a-z0-9]", store.collection_name)
    assert store.count() == 0
    assert store.reset() == 0
    assert store.embedder._encoder is None


def test_reset_is_collection_scoped_preserves_configuration_and_allows_reingestion(tmp_path):
    embedder = FixedEmbedder()
    store = ChromaStore(tmp_path / "chroma", collection="target_reviews", embedder=embedder)
    other = ChromaStore(tmp_path / "chroma", collection="other_reviews", embedder=FixedEmbedder())
    store.upsert([review(), review("rev_002")])
    other.upsert([review("other_id")])
    reopened = ChromaStore(
        tmp_path / "chroma", collection=store.collection_name, embedder=FixedEmbedder()
    )
    assert reopened.count() == 2
    collection_id, metadata = store.col.id, store.col.metadata
    calls_before = embedder.calls
    assert store.reset() == 2
    assert store.reset() == 0
    assert embedder.calls == calls_before
    assert store.count() == reopened.count() == 0
    assert other.count() == 1
    assert store.col.id == collection_id
    assert store.col.metadata == metadata
    store.upsert([review()])
    assert store.count() == reopened.count() == 1
    assert reopened.query("Atraso", 1)[0].review.id == "rev_001"


def test_reset_removes_more_than_one_page(tmp_path):
    store = ChromaStore(tmp_path / "paged", embedder=FixedEmbedder())
    store.upsert([review(f"rev_{index}") for index in range(1002)])
    assert store.count() == 1002
    assert store.reset() == 1002
    assert store.count() == 0


def test_filterable_metadata_is_scalar_and_city_round_trips_and_is_removable(tmp_path):
    store = ChromaStore(tmp_path / "metadata", embedder=FixedEmbedder())
    known = review(city=" São José dos Campos ", aspects={"tempo_entrega": "neg"})
    unknown = review("rev_002")
    store.upsert([known, unknown])
    metadata = store.col.get(ids=[known.id], include=["metadatas"])["metadatas"][0]
    assert set(metadata) >= {
        "restaurant_id",
        "city",
        "category",
        "bairro",
        "rating",
        "created_at",
        "created_at_int",
    }
    assert all(type(value) in (str, int, float, bool) for value in metadata.values())
    assert type(metadata["rating"]) is int
    assert type(metadata["created_at_int"]) is int
    assert metadata["city"] == "São José dos Campos"
    results = store.query(
        "Atraso",
        10,
        {
            "$and": [
                {"restaurant_id": "rest_001"},
                {"city": "São José dos Campos"},
                {"category": "pizza"},
                {"rating": {"$lte": 2}},
                {"created_at_int": {"$gte": 20261101}},
            ]
        },
    )
    assert [doc.review for doc in results] == [known]
    assert "city" not in store.col.get(ids=[unknown.id], include=["metadatas"])["metadatas"][0]
    store.upsert([review()])
    metadata = store.col.get(ids=[known.id], include=["metadatas"])["metadatas"][0]
    assert "city" not in metadata
    assert not any(key.startswith("aspect_") for key in metadata)
    assert all(type(value) in (str, int, float, bool) for value in metadata.values())
    assert store.query("Atraso", 10, {"city": "São José dos Campos"}) == []


def test_automatic_names_separate_models_namespaces_and_prefix_contracts(tmp_path):
    first = ChromaStore(tmp_path / "isolated", embedder=FixedEmbedder("org_a/same-model"))
    second = ChromaStore(tmp_path / "isolated", embedder=FixedEmbedder("org_b/same-model"))
    prefixed = ChromaStore(
        tmp_path / "isolated",
        embedder=FixedEmbedder(
            "org_a/same-model", document_prefix="passage: ", query_prefix="query: "
        ),
    )
    assert len({first.collection_name, second.collection_name, prefixed.collection_name}) == 3
    first.upsert([review()])
    assert second.count() == prefixed.count() == 0
    assert model_collection_name("r" * 63, "x/" + "m" * 200, None) == model_collection_name(
        "r" * 63, "x/" + "m" * 200, None
    )
    assert len(model_collection_name("r" * 63, "x/" + "m" * 200, None)) <= 63


@pytest.mark.parametrize("city", ["", "   "])
def test_city_is_optional_but_cannot_be_blank(city):
    assert review().city is None
    with pytest.raises(ValidationError):
        review(city=city)


def test_old_import_is_an_alias_not_a_second_implementation():
    assert LegacyChromaStore is ChromaStore


def test_documents_survive_reopening_in_another_process(tmp_path):
    path = tmp_path / "process-persistence"
    store = ChromaStore(path, embedder=FixedEmbedder())
    store.upsert([review(city="São José dos Campos")])
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
from partner_copilot.ingestion.chroma_store import ChromaStore
store = ChromaStore(sys.argv[1], model="test/multilingual", collection=sys.argv[2])
assert store.count() == 1
metadata = store.col.get(ids=["rev_001"], include=["metadatas"])["metadatas"][0]
assert metadata["city"] == "São José dos Campos"
assert store.embedder._encoder is None
print("persistent-record-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(path), store.collection_name],
        env=os.environ | {"PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "persistent-record-ok" in result.stdout
