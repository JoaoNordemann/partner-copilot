"""Validated domain models shared by ingestion, retrieval and generation."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from partner_copilot.generation.contracts import (
    ABSTENTION_MESSAGE,
    DEFAULT_PARSER_VERSION,
    GenerationMetrics,
)


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


class AnswerMetadata(BaseModel):
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    retrieved_documents: int = Field(ge=0)
    context_documents: int = Field(ge=0)
    prompt_version: str = Field(min_length=1)
    parser_version: str = Field(default=DEFAULT_PARSER_VERSION, min_length=1)
    llm_called: bool
    generation: GenerationMetrics | None = None

    @model_validator(mode="after")
    def consistent_counts(self) -> "AnswerMetadata":
        if not self.llm_called and self.generation is not None:
            raise ValueError("Generation metrics require a model call")
        if self.context_documents > self.retrieved_documents:
            raise ValueError("Context count cannot exceed retrieved count")
        if not self.llm_called and self.context_documents != 0:
            raise ValueError("Context must be empty if generation was not called")
        if self.llm_called and self.context_documents == 0:
            raise ValueError("Generation requires at least one context document")
        return self


class Answer(BaseModel):
    answer: str = Field(min_length=1)
    sources: list[str]
    abstained: bool
    abstention_reason: Literal["retriever_empty", "llm_insufficient_evidence"] | None
    metadata: AnswerMetadata

    @model_validator(mode="after")
    def consistent_abstention(self) -> "Answer":
        if len(self.sources) != len(set(self.sources)):
            raise ValueError("Sources must be unique")
        if self.abstained:
            if self.sources or self.abstention_reason is None or self.answer != ABSTENTION_MESSAGE:
                raise ValueError("Abstention requires fixed text, reason and no sources")
        elif self.abstention_reason is not None or not self.sources or not self.metadata.llm_called:
            raise ValueError("Normal answers require sources and no abstention reason")
        if self.abstention_reason == "retriever_empty" and (
            self.metadata.retrieved_documents or self.metadata.llm_called
        ):
            raise ValueError("Empty retrieval cannot call the LLM")
        if self.abstention_reason == "llm_insufficient_evidence" and not self.metadata.llm_called:
            raise ValueError("LLM refusal requires a generation call")
        return self
