"""Persistent cosine vector store with explicit embedding ownership."""

import json
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction, Metadata, Where
from chromadb.utils import embedding_functions

from partner_copilot.schemas import RetrievedDoc, Review


class ChromaStore:
    def __init__(
        self,
        path: str | Path,
        model: str,
        collection: str = "reviews",
        *,
        embedding_function: EmbeddingFunction | None = None,
    ) -> None:
        self.client = chromadb.PersistentClient(path=str(path))
        emb = embedding_function
        if emb is None:
            emb = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model, normalize_embeddings=True
            )
        self.col = self.client.get_or_create_collection(
            collection,
            embedding_function=emb,
            metadata={"hnsw:space": "cosine", "embedding_model": model},
        )
        metadata = self.col.metadata or {}
        if metadata.get("embedding_model") != model:
            raise ValueError(
                "Collection has a different or unknown embedding model. "
                "Use a new collection or rebuild the existing index."
            )
        if metadata.get("hnsw:space") != "cosine":
            raise ValueError("Collection must use cosine distance.")

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
                    **{f"aspect_{key}": value for key, value in review.aspects.items()},
                }
            )
        self.col.upsert(
            ids=ids,
            documents=[review.text for review in reviews],
            metadatas=metadatas,
        )

    def query(self, text: str, k: int, where: Where | None = None) -> list[RetrievedDoc]:
        if k < 1:
            raise ValueError("k must be positive")
        count = self.col.count()
        if count == 0:
            return []
        if where and len(where) > 1:
            where = {"$and": [{key: value} for key, value in where.items()]}
        result = self.col.query(
            query_texts=[text],
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
