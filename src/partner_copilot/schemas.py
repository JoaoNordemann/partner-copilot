"""Validated domain models shared by ingestion, retrieval and generation."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator


class Review(BaseModel):
    id: str = Field(min_length=1)
    restaurant_id: str = Field(min_length=1)
    item: str | None = None
    text: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    created_at: date
    category: str = Field(min_length=1)
    bairro: str = Field(min_length=1)
    city: str | None = Field(default=None, min_length=1)
    aspects: dict[str, Literal["pos", "neg"]] = Field(default_factory=dict)

    @field_validator("city")
    @classmethod
    def _valid_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("city must not be blank when provided")
        return value.strip()

    @computed_field
    @property
    def created_at_int(self) -> int:
        """Numeric date for Chroma range filters; always derived from created_at."""
        return self.created_at.year * 10000 + self.created_at.month * 100 + self.created_at.day


class RetrievedDoc(BaseModel):
    review: Review
    score: float
    document_id: str | None = None
    chunk_index: int = 0
    chunk_count: int = 1


class Answer(BaseModel):
    answer: str
    sources: list[str]
