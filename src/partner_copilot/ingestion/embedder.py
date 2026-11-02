"""Lazy multilingual sentence embeddings, independent from vector storage."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from threading import Lock
from typing import Any, Protocol

import numpy as np

from partner_copilot.config import Settings, get_settings


class Encoder(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
        prompt: str,
    ) -> np.ndarray: ...


class Embedder(Protocol):
    model_name: str
    document_prefix: str
    query_prefix: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


ModelFactory = Callable[[str, str], Encoder]


def _load_sentence_transformer(model_name: str, device: str) -> Encoder:
    # Import and model construction are delayed until the first non-empty embedding request.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device, trust_remote_code=False)


class SentenceTransformerEmbedder:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        model_name: str | None = None,
        model_factory: ModelFactory | None = None,
    ) -> None:
        config = settings if settings is not None else get_settings()
        self.model_name = model_name if model_name is not None else config.embedding_model
        if not self.model_name.strip():
            raise ValueError("Embedding model name must not be blank")
        self.batch_size = config.embedding_batch_size
        self.device = config.embedding_device
        mode = config.embedding_prefix_mode
        name = self.model_name.rstrip("/").rsplit("/", 1)[-1]
        e5 = mode == "e5" or (mode == "auto" and name.startswith(("multilingual-e5-", "e5-")))
        self.document_prefix = "passage: " if e5 else ""
        self.query_prefix = "query: " if e5 else ""
        self._factory = model_factory if model_factory is not None else _load_sentence_transformer
        self._encoder: Encoder | None = None
        self._load_lock = Lock()
        self._dimension: int | None = None

    def _get_encoder(self) -> Encoder:
        if self._encoder is None:
            with self._load_lock:
                if self._encoder is None:
                    self._encoder = self._factory(self.model_name, self.device)
        return self._encoder

    def _embed(self, texts: Sequence[str], prefix: str) -> list[list[float]]:
        if isinstance(texts, (str, bytes)):
            raise TypeError("Pass a sequence of texts, not a single string")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty strings")
        if not texts:
            return []
        encoder = self._get_encoder()
        output: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [prefix + text for text in texts[start : start + self.batch_size]]
            # Suppress model-saved prompts: prefixes are applied exactly once by this module.
            vectors = np.asarray(
                encoder.encode(
                    batch,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    prompt="",
                ),
                dtype=np.float32,
            )
            if (
                vectors.ndim != 2
                or vectors.shape[0] != len(batch)
                or vectors.shape[1] < 1
                or not np.isfinite(vectors).all()
            ):
                raise ValueError("Encoder returned invalid embedding shape or non-finite values")
            dimension = vectors.shape[1]
            if self._dimension is not None and dimension != self._dimension:
                raise ValueError("Encoder dimension changed between embedding requests")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if not np.isfinite(norms).all() or np.any(norms == 0):
                raise ValueError("Encoder returned a zero or invalid embedding norm")
            self._dimension = dimension
            output.extend((vectors / norms).tolist())
        return output

    def document_tokenizer(self) -> tuple[Any, int, str]:
        """Lazily expose tokenizer and context size for lossless document chunking."""
        encoder = self._get_encoder()
        tokenizer = getattr(encoder, "tokenizer", None)
        limit = getattr(encoder, "max_seq_length", None)
        if tokenizer is None or not isinstance(limit, int) or limit < 1:
            raise RuntimeError("Encoder does not expose its tokenizer and context size")
        return tokenizer, limit, self.document_prefix

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one normalized vector per document, in input order."""
        return self._embed(texts, self.document_prefix)

    def embed_query(self, text: str) -> list[float]:
        """Return a normalized query vector, using a query prefix for E5."""
        return self._embed([text], self.query_prefix)[0]
