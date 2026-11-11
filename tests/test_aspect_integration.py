import json
from datetime import date

import pytest

from partner_copilot.config import Settings
from partner_copilot.ingestion.aspects import FakeAspectExtractor, PrecomputedAspectExtractor
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.pipeline import IngestionPipeline
from partner_copilot.retrieval.retriever import Retriever


class FixedEmbedder:
    model_name = "tiny"
    document_prefix = query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


class OneDocument:
    def split(self, text):
        return [text]


def test_aspect_ingestion_and_filtered_retrieval(tmp_path):
    outputs = {
        "wanted": '{"aspects":{"tempo_entrega":"neg","sabor":"neg"}}',
        "different": '{"aspects":{"sabor":"neg"}}',
        "positive": '{"aspects":{"tempo_entrega":"pos"}}',
        "empty": '{"aspects":{}}',
        "invalid": '{"aspects":{"fora":"neg"}}',
        "bad-json": "{",
        "other-restaurant": "{",
        "other-item": "{",
        "other-date": "{",
    }
    source = tmp_path / "reviews.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": review_id,
                    "text": "O pedido chegou.",
                    "restaurant_id": "rest_b" if review_id == "other-restaurant" else "rest_a",
                    "item": "burger" if review_id == "other-item" else "pizza",
                    "created_at": "2026-10-31" if review_id == "other-date" else "2026-11-01",
                    "rating": 3,
                    "category": "pizza",
                    "bairro": "Centro",
                    "aspects": {"tempo_entrega": "neg"},
                }
            )
            for review_id in outputs
        ),
        encoding="utf-8",
    )
    legacy = Settings(_env_file=None, embedding_model="tiny")
    enabled = legacy.model_copy(
        update={"aspect_filter_enabled": True, "aspect_enrichment_enabled": True}
    )
    assert not legacy.aspect_enrichment_enabled and not legacy.aspect_filter_enabled
    old_store = ChromaStore(tmp_path / "db", embedder=FixedEmbedder(), settings=legacy)
    IngestionPipeline(old_store, OneDocument()).run(source)
    store = ChromaStore(tmp_path / "db", embedder=FixedEmbedder(), settings=enabled)
    assert store.collection_name != old_store.collection_name
    pipeline = IngestionPipeline(
        store, OneDocument(), aspect_extractor=FakeAspectExtractor(outputs)
    )
    first, second = pipeline.run(source), pipeline.run(source)
    assert first.inserted == len(outputs)
    assert second.inserted == 0 and second.updated == len(outputs)
    assert old_store.count() == store.count() == len(outputs)

    def ids(index, settings, aspect=None):
        retriever = Retriever(index, k=12, settings=settings)
        return {
            row.review.id
            for row in retriever.retrieve(
                "Atraso", "rest_a", aspect, item="pizza", start_date=date(2026, 11, 1)
            )
        }

    eligible = {"wanted", "different", "positive", "empty", "invalid", "bad-json"}
    assert ids(old_store, legacy, "tempo_entrega") == eligible
    assert ids(old_store, legacy) == ids(store, enabled) == eligible
    assert ids(store, enabled, "unsupported") == eligible
    assert ids(store, enabled, "tempo_entrega") == eligible - {"different"}
    metadata = store.col.get(ids=["invalid", "empty"], include=["metadatas"])
    by_id = dict(zip(metadata["ids"], metadata["metadatas"], strict=True))
    assert by_id["invalid"]["extractor_status"] == "inválido"
    assert by_id["invalid"]["extractor_version"] == "fake-v1"
    assert by_id["invalid"]["aspects_json"] == "{}"
    assert by_id["empty"]["extractor_status"] == "ok"
    assert "aspect_tempo_entrega" not in by_id["invalid"]


def test_precomputed_binds_prediction_to_corpus_text():
    from pathlib import Path

    from partner_copilot.schemas import Review

    root = Path(__file__).resolve().parents[1]
    corpus = root / "data/eval/human-v2/corpus.jsonl"
    predictions = root / "reports/absa-eval-checkpoint-253-v1/retrieval-predictions.jsonl"
    review = Review.model_validate_json(corpus.read_text(encoding="utf-8").splitlines()[0])
    extractor = PrecomputedAspectExtractor(predictions, corpus)
    assert extractor.extract(review).status == "ok"
    changed = review.model_copy(update={"text": "Texto alterado."})
    assert extractor.extract(changed).status == "inválido"


@pytest.mark.parametrize("raw", ['{"aspects":{"sabor":"neutro"}}', '{"aspects":{},"aspects":{}}'])
def test_fake_rejects_invalid_contract(raw):
    from types import SimpleNamespace

    result = FakeAspectExtractor({"review": raw}).extract(SimpleNamespace(id="review"))
    assert result.status == "inválido"
    assert result.aspects == {}
