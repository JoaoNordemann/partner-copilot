"""Validated domain models shared by ingestion, retrieval and generation."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class Review(BaseModel):
    id: str = Field(min_length=1)
    restaurant_id: str = Field(min_length=1)
    item: str | None = None
    text: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    created_at: date
    category: str = Field(min_length=1)
    bairro: str = Field(min_length=1)
    aspects: dict[str, Literal["pos", "neg"]] = Field(default_factory=dict)

    @computed_field
    @property
    def created_at_int(self) -> int:
        """Numeric date for Chroma range filters; always derived from created_at."""
        return self.created_at.year * 10000 + self.created_at.month * 100 + self.created_at.day


class RetrievedDoc(BaseModel):
    review: Review
    score: float


class Answer(BaseModel):
    answer: str
    sources: list[str]
