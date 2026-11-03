"""Opt-in semantic sanity check with a real, locally cached multilingual model."""

import os

import pytest

from partner_copilot.config import Settings
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.chunking import TokenTextSplitter
from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
from partner_copilot.ingestion.pipeline import IngestionPipeline
from partner_copilot.schemas import Review


@pytest.mark.semantic
@pytest.mark.skipif(os.environ.get("RUN_SEMANTIC_TESTS") != "1", reason="Set RUN_SEMANTIC_TESTS=1")
def test_portuguese_delivery_query_retrieves_related_reviews(tmp_path):
    from sentence_transformers import SentenceTransformer

    def load_cached_model(name, device):
        # Fail if unavailable locally; never download as a side effect of running tests.
        return SentenceTransformer(name, device=device, local_files_only=True)

    embedder = SentenceTransformerEmbedder(Settings(), model_factory=load_cached_model)
    reviews = [
        ("delay_1", "Esperei quase duas horas pelo pedido. O motoboy chegou muito atrasado."),
        ("delay_2", "O prazo era de quarenta minutos, mas a entrega levou uma hora e meia."),
        ("taste", "A pizza estava deliciosa, com bastante queijo e massa crocante."),
        ("packaging", "A embalagem veio rasgada e o refrigerante vazou na sacola."),
        ("price", "Os preços do cardápio estão caros e a promoção não vale a pena."),
    ]
    source = tmp_path / "reviews.jsonl"
    source.write_text(
        "\n".join(
            Review(
                id=identifier,
                restaurant_id="rest_test",
                text=text,
                rating=3,
                created_at="2026-11-01",
                category="pizza",
                bairro="Centro",
            ).model_dump_json()
            for identifier, text in reviews
        ),
        encoding="utf-8",
    )
    store = ChromaStore(tmp_path / "chroma", embedder=embedder)
    splitter = TokenTextSplitter(embedder, overlap_tokens=16)
    report = IngestionPipeline(store, splitter, batch_size=2).run(source)
    assert report.inserted == store.count() == len(reviews)
    results = store.query("entrega demorou muito", k=len(reviews))
    assert {doc.review.id for doc in results[:2]} == {"delay_1", "delay_2"}
    assert min(doc.score for doc in results[:2]) > max(doc.score for doc in results[2:])
