"""Persistent cosine vector store with explicit embedding ownership."""

import hashlib
import json
import re
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction, Metadata, Where

from partner_copilot.config import Settings, get_settings
from partner_copilot.ingestion.embedder import Embedder, SentenceTransformerEmbedder
from partner_copilot.schemas import RetrievedDoc, Review


def model_collection_name(base: str, model: str, contract: str | None) -> str:
    """Readable model tag plus digest; keep generated names within 63 ASCII characters."""
    base_slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:12].rstrip("-")
    model_slug = re.sub(r"[^a-z0-9]+", "-", model.rstrip("/").rsplit("/", 1)[-1].lower())
    model_slug = model_slug.strip("-")[:39].rstrip("-") or "model"
    identity = contract if contract is not None else model
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8]
    return f"{base_slug or 'reviews'}-{model_slug}-{digest}"


class ChromaStore:
    def __init__(
        self,
        path: str | Path | None = None,
        model: str | None = None,
        collection: str | None = None,
        *,
        embedding_function: EmbeddingFunction | None = None,
        embedder: Embedder | None = None,
        settings: Settings | None = None,
    ) -> None:
        if embedding_function is not None and embedder is not None:
            raise ValueError("Provide either embedder or embedding_function, not both")
        config = settings if settings is not None else get_settings()
        model = model or (embedder.model_name if embedder is not None else config.embedding_model)
        self.embedder = embedder
        contract: str | None = None
        if embedding_function is None:
            if self.embedder is None:
                self.embedder = SentenceTransformerEmbedder(config, model_name=model)
            if self.embedder.model_name != model:
                raise ValueError("Embedder model name does not match the collection model")
            contract = json.dumps(
                {
                    "model": model,
                    "normalize": True,
                    "document_prefix": self.embedder.document_prefix,
                    "query_prefix": self.embedder.query_prefix,
                },
                sort_keys=True,
            )
        self.path = Path(path) if path is not None else config.chroma_path
        self.collection_name = (
            collection
            if collection is not None
            else model_collection_name(config.chroma_collection, model, contract)
        )
        self.client = chromadb.PersistentClient(path=str(self.path))
        collection_metadata = {"hnsw:space": "cosine", "embedding_model": model}
        if contract is not None:
            collection_metadata["embedding_input_contract"] = contract
        # Production embeddings are explicit: Chroma must not choose its own model or prompts.
        # embedding_function is retained only as an explicit compatibility/injection path.
        self.col = self.client.get_or_create_collection(
            self.collection_name,
            embedding_function=embedding_function,
            metadata=collection_metadata,
        )
        metadata = self.col.metadata or {}
        if metadata.get("embedding_model") != model:
            raise ValueError(
                "Collection has a different or unknown embedding model. "
                "Use a new collection or rebuild the existing index."
            )
        if metadata.get("hnsw:space") != "cosine":
            raise ValueError("Collection must use cosine distance.")
        if contract is not None and metadata.get("embedding_input_contract") != contract:
            # The previous implementation used this exact model with normalization and no prefixes.
            compatible_legacy = (
                metadata.get("embedding_input_contract") is None
                and model.removeprefix("sentence-transformers/")
                == "paraphrase-multilingual-MiniLM-L12-v2"
                and self.embedder is not None
                and not self.embedder.document_prefix
                and not self.embedder.query_prefix
            )
            if not compatible_legacy:
                raise ValueError(
                    "Embedding preprocessing differs; use a new collection and reindex."
                )

    def count(self) -> int:
        """Return the number of documents in this collection."""
        return self.col.count()

    def reset(self) -> int:
        """Delete documents from this collection only; preserve its identity and configuration.

        Run during maintenance without concurrent writers. Other collections are untouched.
        Returns the number of deleted records. Does not load the embedding model.
        """
        removed = 0
        while True:
            ids = self.col.get(limit=1000, include=[])["ids"]
            if not ids:
                return removed
            self.col.delete(ids=ids)
            removed += len(ids)

    def upsert(self, reviews: list[Review]) -> None:
        if not reviews:
            return
        ids = [review.id for review in reviews]
        previous = self.col.get(ids=ids, include=["metadatas"])
        previous_metadata = dict(zip(previous["ids"], previous["metadatas"] or [], strict=True))
        metadatas: list[Metadata] = []
        for review in reviews:
            metadatas.append(
                {
                    # Chroma merges metadata; None deletes stale keys without storing a sentinel.
                    **{
                        key: None
                        for key in (previous_metadata.get(review.id) or {})
                        if key.startswith("aspect_")
                    },
                    "aspects_json": json.dumps(review.aspects, ensure_ascii=False),
                    "restaurant_id": review.restaurant_id,
                    "item": review.item or "",
                    "rating": review.rating,
                    "created_at": review.created_at.isoformat(),
                    "created_at_int": review.created_at_int,
                    "category": review.category,
                    "bairro": review.bairro,
                    **(
                        {"city": review.city}
                        if review.city is not None
                        else {"city": None}
                        if "city" in (previous_metadata.get(review.id) or {})
                        else {}
                    ),
                    **{f"aspect_{key}": value for key, value in review.aspects.items()},
                }
            )
        vectors = (
            self.embedder.embed_documents([review.text for review in reviews])
            if self.embedder is not None
            else None
        )
        self.col.upsert(
            ids=ids,
            documents=[review.text for review in reviews],
            metadatas=metadatas,
            embeddings=vectors,
        )

    def query(self, text: str, k: int, where: Where | None = None) -> list[RetrievedDoc]:
        if k < 1:
            raise ValueError("k must be positive")
        count = self.count()
        if count == 0:
            return []
        if where and len(where) > 1:
            where = {"$and": [{key: value} for key, value in where.items()]}
        result = self.col.query(
            query_texts=[text] if self.embedder is None else None,
            query_embeddings=[self.embedder.embed_query(text)]
            if self.embedder is not None
            else None,
            n_results=min(k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"]
        metadatas = result["metadatas"]
        distances = result["distances"]
        if documents is None or metadatas is None or distances is None:
            raise RuntimeError("Chroma did not return the requested documents and metadata")
        output: list[RetrievedDoc] = []
        for review_id, document, metadata, distance in zip(
            result["ids"][0], documents[0], metadatas[0], distances[0], strict=True
        ):
            if metadata is None or document is None:
                raise RuntimeError(f"Missing document or metadata for {review_id}")
            review = Review.model_validate(
                {
                    **metadata,
                    "id": review_id,
                    "text": document,
                    "item": metadata.get("item") or None,
                    "aspects": json.loads(str(metadata["aspects_json"])),
                }
            )
            output.append(RetrievedDoc(review=review, score=1.0 - distance))
        return output
