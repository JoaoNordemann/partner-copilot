import json
import logging
import re
from itertools import pairwise

import pytest

from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.chunking import TokenTextSplitter
from partner_copilot.ingestion.documents import WriteResult
from partner_copilot.ingestion.pipeline import IngestionPipeline, index_documents, parse_review


class WordTokenizer:
    def num_special_tokens_to_add(self, pair=False):
        return 2

    def __call__(self, text, add_special_tokens=True, return_offsets_mapping=False, **kwargs):
        offsets = [match.span() for match in re.finditer(r"\S+", text)]
        result = {"input_ids": list(range(len(offsets) + (2 if add_special_tokens else 0)))}
        if return_offsets_mapping:
            result["offset_mapping"] = offsets
        return result


class TokenProvider:
    def __init__(self, prefix="", limit=8):
        self.tokenizer, self.prefix, self.limit = WordTokenizer(), prefix, limit

    def document_tokenizer(self):
        return self.tokenizer, self.limit, self.prefix


class FixedEmbedder:
    model_name = "test/ingestion-pipeline"
    document_prefix = ""
    query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


class NoSplit:
    def split(self, text):
        return [text]


class MemoryStore:
    def __init__(self):
        self.docs = {}
        self.calls = 0

    def upsert_documents(self, documents, batch_size=128):
        inserted = sum(doc.id not in self.docs for doc in documents)
        self.docs.update({doc.id: doc for doc in documents})
        self.calls += 1
        return WriteResult(inserted=inserted, updated=len(documents) - inserted)


def payload(review_id="review_a", text="A entrega atrasou.", **changes):
    return {
        "id": review_id,
        "restaurant_id": "rest_001",
        "text": text,
        "rating": 2,
        "created_at": "2026-11-01",
        "category": "pizza",
        "bairro": "Centro",
        **changes,
    }


def write(path, records):
    path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")


def test_bad_records_are_skipped_duplicates_use_first_valid_row_and_counts_are_exact(
    tmp_path, caplog
):
    path = tmp_path / "mixed.jsonl"
    missing = payload(text="Outra avaliação sem identificador.")
    del missing["id"]
    alias = payload(text="Review identificada pelo campo alternativo.")
    del alias["id"]
    alias["review_id"] = "alternative_id"
    lines = [
        json.dumps(payload()),
        "{broken json",
        json.dumps(payload(rating=0, text="PRIVATE-SENTINEL")),
        "[]",
        "",
        json.dumps(missing),
        json.dumps(alias),
        json.dumps(payload()),
        json.dumps(payload(text="Conflicting duplicate.")),
        json.dumps(payload("last")),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    store = MemoryStore()
    caplog.set_level(logging.INFO)
    report = IngestionPipeline(store, NoSplit(), batch_size=2).run(path)
    assert report.lines_read == 10 and report.read == 9
    assert report.valid == 6 and report.invalid == 3
    assert report.duplicates == 2 and report.blank == 1 and report.ignored == 6
    assert report.reviews_upserted == report.documents_upserted == report.inserted == 4
    assert report.updated == 0
    assert store.docs["review_a"].text == "A entrega atrasou."
    assert "last" in store.docs and "alternative_id" in store.docs
    assert "PRIVATE-SENTINEL" not in caplog.text
    assert "invalid_record line=2" in caplog.text and "ingestion_completed" in caplog.text
    second = IngestionPipeline(store, NoSplit(), batch_size=2).run(path)
    assert second.inserted == 0 and second.updated == 4
    assert len(store.docs) == 4


def test_fallback_ids_are_deterministic_and_scoped_by_restaurant():
    row = payload()
    del row["id"]
    first = parse_review(json.dumps(row))
    assert first.id == parse_review(json.dumps(row | {"rating": 5})).id
    assert first.id != parse_review(json.dumps(row | {"restaurant_id": "rest_002"})).id
    assert first.id.startswith("review_")
    with pytest.raises(ValueError):
        parse_review(json.dumps(payload(review_id="")))


def test_token_chunking_preserves_short_text_and_bounds_long_documents_with_prefixes():
    provider = TokenProvider(prefix="passage: ", limit=8)
    splitter = TokenTextSplitter(provider, overlap_tokens=2)
    short = "  A entrega atrasou.  "
    assert splitter.split(short) == [short]
    text = " ".join(f"palavra{index}" for index in range(30))
    pieces = splitter.split(text)
    assert len(pieces) > 1 and pieces == splitter.split(text)
    assert all(len(provider.tokenizer("passage: " + piece)["input_ids"]) <= 8 for piece in pieces)
    assert set(text.split()) == {word for piece in pieces for word in piece.split()}
    assert all(set(left.split()) & set(right.split()) for left, right in pairwise(pieces))


def test_chunk_ids_and_citations_are_stable_and_obsolete_chunks_are_removed(tmp_path):
    path = tmp_path / "long.jsonl"
    row = payload(text=" ".join(f"palavra{index}" for index in range(25)))
    write(path, [row])
    splitter = TokenTextSplitter(TokenProvider(), overlap_tokens=2)
    store = ChromaStore(tmp_path / "chroma", embedder=FixedEmbedder())
    pipeline = IngestionPipeline(store, splitter, batch_size=2)
    first = pipeline.run(path)
    count = store.count()
    assert count > 2 and first.inserted == count
    second = pipeline.run(path)
    assert second.inserted == 0 and second.updated == count and store.count() == count
    assert store.review_ids() == ["review_a"]
    assert all(
        doc.review.id == "review_a" and doc.document_id.startswith("chunk_")
        for doc in store.query("Entrega", 10)
    )
    write(path, [payload(text="Texto curto.")])
    shortened = pipeline.run(path)
    assert shortened.stale_deleted == count and store.count() == 1
    assert store.query("Entrega", 1)[0].document_id == "review_a"
    write(path, [row])
    expanded = pipeline.run(path)
    assert expanded.stale_deleted == 1 and store.count() == count


def test_partial_chunk_sets_are_rejected_without_deleting_existing_documents(tmp_path):
    store = ChromaStore(tmp_path / "complete", embedder=FixedEmbedder())
    source = parse_review(json.dumps(payload()))
    docs = index_documents(source, ["Parte um.", "Parte dois."])
    store.upsert_documents(docs)
    with pytest.raises(ValueError, match="complete chunk set"):
        store.upsert_documents(docs[:1])
    assert store.count() == 2


def test_store_failure_is_fatal_and_not_reported_as_invalid_data(tmp_path, caplog):
    class FailingStore:
        def upsert_documents(self, documents, batch_size=128):
            raise OSError("disk full")

    path = tmp_path / "failure.jsonl"
    write(path, [payload()])
    with pytest.raises(OSError, match="disk full"):
        IngestionPipeline(FailingStore(), NoSplit(), batch_size=1).run(path)
    assert "ingestion_write_failed" in caplog.text
    assert "ingestion_completed" not in caplog.text


def test_character_limit_skips_oversized_record_and_continues(tmp_path):
    path = tmp_path / "limits.jsonl"
    write(path, [payload("long", text="x" * 101), payload("short", text="Bom.")])
    store = MemoryStore()
    report = IngestionPipeline(store, NoSplit(), max_review_chars=100).run(path)
    assert report.invalid == 1 and report.inserted == 1 and set(store.docs) == {"short"}


def test_invalid_chunk_configuration_and_runtime_model_failure_are_not_silently_skipped(tmp_path):
    with pytest.raises(ValueError, match="overlap"):
        TokenTextSplitter(TokenProvider(), max_tokens=4, overlap_tokens=4)
    with pytest.raises(RuntimeError, match="budget"):
        TokenTextSplitter(TokenProvider(limit=4), overlap_tokens=3).split("Texto.")

    class BrokenSplitter:
        def split(self, text):
            raise RuntimeError("model unavailable")

    path = tmp_path / "runtime.jsonl"
    write(path, [payload()])
    store = MemoryStore()
    with pytest.raises(RuntimeError, match="model unavailable"):
        IngestionPipeline(store, BrokenSplitter()).run(path)
    assert store.calls == 0


def test_model_value_error_is_not_misclassified_as_a_bad_record(tmp_path):
    class BadModelSplitter:
        def split(self, text):
            raise ValueError("invalid model configuration")

    path = tmp_path / "bad-model.jsonl"
    write(path, [payload()])
    store = MemoryStore()
    with pytest.raises(ValueError, match="model configuration"):
        IngestionPipeline(store, BadModelSplitter()).run(path)
    assert store.calls == 0


def test_persistent_pipeline_skips_invalid_records_and_preserves_metadata(tmp_path, caplog):
    source = tmp_path / "mixed.jsonl"
    rows = [
        payload("first", city="São José dos Campos", aspects={"tempo_entrega": "neg"}),
        payload("invalid", rating=0, text="PRIVATE-SENTINEL"),
        payload("last", rating=5, text="Pizza deliciosa.", aspects={"sabor": "pos"}),
    ]
    write(source, rows)
    database = tmp_path / "persistent"
    store = ChromaStore(database, embedder=FixedEmbedder())
    caplog.set_level(logging.INFO, logger="partner_copilot.ingestion.pipeline")
    first = IngestionPipeline(store, NoSplit(), batch_size=1).run(source)
    assert (first.read, first.valid, first.invalid, first.ignored) == (3, 2, 1, 1)
    assert first.inserted == store.count() == 2
    assert set(store.review_ids()) == {"first", "last"}
    assert "invalid_record line=2" in caplog.text
    assert "rating:greater_than_equal" in caplog.text
    assert "PRIVATE-SENTINEL" not in caplog.text
    assert "ingestion_completed" in caplog.text
    reopened = ChromaStore(database, embedder=FixedEmbedder())
    second = IngestionPipeline(reopened, NoSplit(), batch_size=1).run(source)
    assert second.inserted == 0 and second.updated == 2 and reopened.count() == 2
    metadata = reopened.col.get(ids=["first"], include=["metadatas"])["metadatas"][0]
    expected = {
        "restaurant_id": "rest_001",
        "review_id": "first",
        "city": "São José dos Campos",
        "category": "pizza",
        "bairro": "Centro",
        "rating": 2,
        "created_at": "2026-11-01",
        "created_at_int": 20261101,
        "aspect_tempo_entrega": "neg",
        "chunk_index": 0,
        "chunk_count": 1,
    }
    assert {key: metadata[key] for key in expected} == expected
    assert json.loads(metadata["aspects_json"]) == {"tempo_entrega": "neg"}
    assert "aspect_sabor" not in metadata
    assert all(type(value) in (str, int, float, bool) for value in metadata.values())
