import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from chromadb.errors import NotFoundError

from partner_copilot import asking
from partner_copilot.asking import AskPreflightError, AskRequest, run_ask
from partner_copilot.config import Settings
from partner_copilot.generation.contracts import InvalidCitationError
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.schemas import Review

ROOT = Path(__file__).resolve().parents[1]


class Embedder:
    model_name = "test/ask"
    document_prefix = query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def setup_store(tmp_path, monkeypatch):
    settings = Settings(
        chroma_path=tmp_path / "db",
        data_splits_dir=ROOT / "data/splits",
        embedding_model=Embedder.model_name,
    )
    source = json.loads(
        (ROOT / "data/splits/rag.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    review = Review.model_validate(source)
    store = ChromaStore(settings=settings, embedder=Embedder())
    store.upsert([review])
    monkeypatch.setattr(
        asking,
        "_open_store",
        lambda settings, collection: ChromaStore(
            settings=settings, collection=collection, embedder=Embedder(), create_if_missing=False
        ),
    )
    return settings, store, review


def test_real_retrieval_empty_does_not_call_llm_and_valid_answer_cites_only_used_source(
    tmp_path, monkeypatch
):
    settings, store, review = setup_store(tmp_path, monkeypatch)
    llm = Mock()
    loader = Mock(return_value=llm)
    monkeypatch.setattr("partner_copilot.pipeline.get_llm", loader)
    answer = run_ask(settings, AskRequest(question="Espera?", restaurant_id="absent"))
    assert answer.abstained and answer.abstention_reason == "retriever_empty"
    loader.assert_not_called()
    llm.generate.return_value = f"Há um relato de espera [{review.id}]."
    answer = run_ask(settings, AskRequest(question="Espera?", restaurant_id=review.restaurant_id))
    assert answer.sources == [review.id] and not answer.abstained
    assert answer.metadata.context_documents == 1 and store.count() == 1
    llm.generate.return_value = "Há um relato [inventada] e outro [inventada]."
    with pytest.raises(InvalidCitationError) as exc:
        run_ask(settings, AskRequest(question="Espera?", restaurant_id=review.restaurant_id))
    assert exc.value.invalid_citation_count == 2
    assert exc.value.invalid_ids == ("inventada",)


def test_query_mode_never_creates_unknown_database_or_collection(tmp_path):
    path = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        ChromaStore(path, embedder=Embedder(), create_if_missing=False)
    assert not path.exists()
    existing = ChromaStore(tmp_path / "existing", embedder=Embedder())
    names = [c.name for c in existing.client.list_collections()]
    with pytest.raises(NotFoundError):
        ChromaStore(
            tmp_path / "existing",
            collection="unknown_collection",
            embedder=Embedder(),
            create_if_missing=False,
        )
    assert [c.name for c in existing.client.list_collections()] == names


def test_collection_with_gold_or_training_ids_is_rejected_before_generation(tmp_path, monkeypatch):
    settings, store, review = setup_store(tmp_path, monkeypatch)
    store.upsert([review.model_copy(update={"id": "outside_rag"})])
    loader = Mock()
    monkeypatch.setattr("partner_copilot.pipeline.get_llm", loader)
    with pytest.raises(AskPreflightError, match="outside the RAG"):
        run_ask(settings, AskRequest(question="Pergunta", restaurant_id=review.restaurant_id))
    loader.assert_not_called()
