# retrieval/retriever.py
from typing import Protocol

from ..schemas import RetrievedDoc


class VectorStore(Protocol):
    def query(self, text: str, k: int, where: dict | None) -> list[RetrievedDoc]: ...


class Retriever:
    def __init__(self, store: VectorStore, k: int = 8, min_score: float = 0.25):
        self.store, self.k, self.min_score = store, k, min_score

    def retrieve(
        self, query: str, restaurant_id: str, aspect: str | None = None
    ) -> list[RetrievedDoc]:
        where = {"restaurant_id": restaurant_id}
        if aspect:
            where[f"aspect_{aspect}"] = "neg"
        docs = self.store.query(query, self.k * 2, where)
        return [d for d in docs if d.score >= self.min_score][: self.k]
