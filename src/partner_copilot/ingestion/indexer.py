"""Batch ingestion, independent from the concrete vector store."""

from pathlib import Path
from typing import Protocol

from partner_copilot.ingestion.loaders import load_reviews
from partner_copilot.schemas import Review


class ReviewStore(Protocol):
    def upsert(self, reviews: list[Review]) -> None: ...


def ingest_reviews(path: Path, store: ReviewStore, batch_size: int = 128) -> int:
    """Upsert stable review IDs. Failures can leave completed batches; reruns are safe."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    batch: list[Review] = []
    seen: set[str] = set()
    processed = 0
    for review in load_reviews(path):
        if review.id in seen:
            raise ValueError(f"{path}: duplicate review id: {review.id}")
        seen.add(review.id)
        batch.append(review)
        if len(batch) == batch_size:
            store.upsert(batch)
            processed += len(batch)
            batch = []
    if batch:
        store.upsert(batch)
        processed += len(batch)
    return processed
