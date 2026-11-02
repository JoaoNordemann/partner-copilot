import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from partner_copilot.config import Settings
from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
from partner_copilot.retrieval.store import ChromaStore
from partner_copilot.schemas import Review


class RecordingEncoder:
    def __init__(self):
        self.calls = []

    def encode(self, sentences, **kwargs):
        self.calls.append((list(sentences), kwargs))
        return np.array(
            [[3.0, 4.0, float(index + 1)] for index, _ in enumerate(sentences)], dtype=np.float32
        )


def make_embedder(model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", **changes):
    encoder = RecordingEncoder()
    loads = []

    def factory(model_name, device):
        loads.append((model_name, device))
        return encoder

    settings = Settings(embedding_model=model, embedding_batch_size=2, **changes)
    return SentenceTransformerEmbedder(settings, model_factory=factory), encoder, loads


def test_module_import_does_not_import_sentence_transformers():
    root = Path(__file__).resolve().parents[1]
    code = """
import builtins
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "sentence_transformers" or name.startswith("sentence_transformers."):
        raise AssertionError("Model library imported eagerly")
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
instance = SentenceTransformerEmbedder()
assert instance.embed_documents([]) == []
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONPATH": str(root / "src")},
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_lazy_loading_empty_inputs_and_batching():
    embedder, encoder, loads = make_embedder()
    assert loads == []
    assert embedder.embed_documents([]) == []
    assert loads == []
    documents = [f"Avaliação {index}" for index in range(5)]
    vectors = embedder.embed_documents(documents)
    assert len(loads) == 1
    assert [sentences for sentences, _ in encoder.calls] == [
        documents[:2],
        documents[2:4],
        documents[4:],
    ]
    assert len(vectors) == 5
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert all(call[1]["batch_size"] == 2 for call in encoder.calls)
    assert all(call[1]["normalize_embeddings"] is True for call in encoder.calls)
    assert all(call[1]["prompt"] == "" for call in encoder.calls)
    assert len(embedder.embed_query("Por que atrasou?")) == 3
    assert len(loads) == 1
    assert encoder.calls[-1][0] == ["Por que atrasou?"]


@pytest.mark.parametrize(
    "mode,document,query",
    [
        ("auto", "passage: Chegou frio.", "query: O que aconteceu?"),
        ("e5", "passage: Chegou frio.", "query: O que aconteceu?"),
        ("none", "Chegou frio.", "O que aconteceu?"),
    ],
)
def test_e5_uses_different_document_and_query_prefixes(mode, document, query):
    embedder, encoder, _ = make_embedder(
        "intfloat/multilingual-e5-small", embedding_prefix_mode=mode
    )
    embedder.embed_documents(["Chegou frio."])
    embedder.embed_query("O que aconteceu?")
    assert encoder.calls[0][0] == [document]
    assert encoder.calls[1][0] == [query]


@pytest.mark.parametrize("value", ["", "  ", None])
def test_invalid_queries_fail_before_loading(value):
    embedder, _, loads = make_embedder()
    with pytest.raises(ValueError, match="non-empty strings"):
        embedder.embed_query(value)
    assert loads == []


def test_a_single_string_is_not_a_document_batch():
    embedder, _, loads = make_embedder()
    with pytest.raises(TypeError, match="sequence"):
        embedder.embed_documents("Avaliação")
    assert loads == []


@pytest.mark.parametrize(
    "vectors",
    [
        np.array([[0.0, 0.0]]),
        np.array([[float("nan"), 1.0]]),
        np.array([1.0, 2.0]),
        np.empty((1, 0)),
    ],
)
def test_invalid_encoder_results_are_rejected(vectors):
    class BadEncoder:
        def encode(self, sentences, **kwargs):
            return vectors

    embedder = SentenceTransformerEmbedder(Settings(), model_factory=lambda *_: BadEncoder())
    with pytest.raises(ValueError, match=r"invalid|zero"):
        embedder.embed_query("Pergunta")


@pytest.mark.parametrize(
    "changes",
    [
        {"embedding_batch_size": 0},
        {"embedding_batch_size": 4097},
        {"embedding_model": "  "},
        {"embedding_device": ""},
        {"embedding_prefix_mode": "invalid"},
    ],
)
def test_embedding_config_validation(changes):
    with pytest.raises(ValidationError):
        Settings(**changes)


def test_chroma_uses_explicit_document_and_query_embeddings_and_reopens_lazily(tmp_path):
    embedder, encoder, loads = make_embedder("intfloat/multilingual-e5-small")
    store = ChromaStore(tmp_path / "chroma", embedder=embedder)
    assert loads == []
    assert store.query("Pergunta", 3) == []
    assert loads == []
    review = Review(
        id="rev_test",
        restaurant_id="rest_001",
        text="Chegou frio.",
        rating=2,
        created_at="2026-11-01",
        category="pizza",
        bairro="Centro",
    )
    store.upsert([review])
    assert encoder.calls[0][0] == ["passage: Chegou frio."]
    docs = store.query("Por que frio?", 3, {"restaurant_id": "rest_001"})
    assert docs[0].review == review
    assert encoder.calls[-1][0] == ["query: Por que frio?"]
    reopened_embedder, reopened_encoder, reopened_loads = make_embedder(
        "intfloat/multilingual-e5-small"
    )
    reopened = ChromaStore(tmp_path / "chroma", embedder=reopened_embedder)
    assert reopened_loads == []
    assert reopened.query("Frio?", 1)[0].review.id == "rev_test"
    assert reopened_encoder.calls[0][0] == ["query: Frio?"]


def test_chroma_rejects_changed_model_or_prefixes_before_loading(tmp_path):
    embedder, _, _ = make_embedder("intfloat/multilingual-e5-small")
    original = ChromaStore(tmp_path / "contract", embedder=embedder)
    changed, _, loads = make_embedder(
        "intfloat/multilingual-e5-small", embedding_prefix_mode="none"
    )
    with pytest.raises(ValueError, match="preprocessing"):
        ChromaStore(tmp_path / "contract", collection=original.collection_name, embedder=changed)
    assert loads == []
    changed, _, loads = make_embedder("some-other-model")
    with pytest.raises(ValueError, match="embedding model"):
        ChromaStore(tmp_path / "contract", collection=original.collection_name, embedder=changed)
    assert loads == []
