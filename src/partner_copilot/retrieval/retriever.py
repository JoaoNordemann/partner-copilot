"""Restaurant-scoped retrieval with inclusive date filters and explicit abstention."""

from datetime import date
from typing import Any, Protocol

from partner_copilot.config import Settings, get_settings
from partner_copilot.ingestion.aspects import aspect_filter
from partner_copilot.schemas import RetrievedDoc

# Structural contract; importing the retriever must not require the Chroma adapter.
Where = dict[str, Any]


class VectorStore(Protocol):
    def query(self, text: str, k: int, where: Where | None) -> list[RetrievedDoc]: ...


def date_key(value: date) -> int:
    return value.year * 10000 + value.month * 100 + value.day


class Retriever:
    """Rank reviews within a restaurant using metadata and similarity."""

    def __init__(
        self,
        store: VectorStore,
        k: int | None = None,
        min_score: float | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        config = settings if settings is not None else get_settings()
        self.k = config.retrieval_k if k is None else k
        self.min_score = config.retrieval_min_score if min_score is None else min_score
        if not 1 <= self.k <= 50 or not 0 <= self.min_score <= 1:
            raise ValueError("k must be between 1 and 50; min_score between 0 and 1")
        self.store = store
        self.aspect_filter_enabled = config.aspect_filter_enabled

    def retrieve(
        self,
        query: str,
        restaurant_id: str,
        aspect: str | None = None,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        item: str | None = None,
        category: str | None = None,
        city: str | None = None,
        bairro: str | None = None,
    ) -> list[RetrievedDoc]:
        """Return up to k qualifying documents; never relax filters or the score threshold."""
        if not query.strip() or not restaurant_id.strip():
            raise ValueError("query and restaurant_id must not be blank")
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        filters: list[Where] = [{"restaurant_id": restaurant_id}]
        if aspect is not None:
            if not aspect.strip():
                raise ValueError("aspect must not be blank")
            predicate = aspect_filter(aspect, self.aspect_filter_enabled)
            if predicate is not None:
                filters.append(predicate)
        for name, value in (
            ("item", item),
            ("category", category),
            ("city", city),
            ("bairro", bairro),
        ):
            if value is not None:
                if not value.strip():
                    raise ValueError(f"{name} must not be blank")
                filters.append({name: value})
        if start_date is not None:
            filters.append({"created_at_int": {"$gte": date_key(start_date)}})
        if end_date is not None:
            filters.append({"created_at_int": {"$lte": date_key(end_date)}})
        where = filters[0] if len(filters) == 1 else {"$and": filters}
        docs = self.store.query(query, self.k * 2, where)
        return [doc for doc in docs if doc.score >= self.min_score][: self.k]
