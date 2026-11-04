"""Application orchestration for querying only a registered production RAG collection."""

import logging
from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from partner_copilot.config import Settings
from partner_copilot.data_splits import validate_rag_collection_ids
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.retrieval.retriever import Retriever
from partner_copilot.schemas import Answer

if TYPE_CHECKING:
    from partner_copilot.ingestion.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class AskPreflightError(ValueError):
    """The requested existing collection or its registered RAG split cannot be used."""


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)
    restaurant_id: str = Field(min_length=1)
    aspect: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    item: str | None = None
    category: str | None = None
    city: str | None = None
    bairro: str | None = None

    @field_validator("question", "restaurant_id", "aspect", "item", "category", "city", "bairro")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Must not be blank when provided")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def ordered_dates(self) -> "AskRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        return self


def _open_store(settings: Settings, collection: str | None) -> "ChromaStore":
    if not (settings.chroma_path / "chroma.sqlite3").is_file():
        raise AskPreflightError("Persistent database not found; run scripts/ingest.py first")
    from chromadb.errors import NotFoundError

    from partner_copilot.ingestion.chroma_store import ChromaStore

    try:
        return ChromaStore(settings=settings, collection=collection, create_if_missing=False)
    except (NotFoundError, ValueError) as exc:
        raise AskPreflightError(f"Collection unavailable or incompatible: {exc}") from exc


def run_ask(settings: Settings, request: AskRequest, *, collection: str | None = None) -> Answer:
    load_prompt_template(settings.prompt_version)
    store = _open_store(settings, collection)
    try:
        validate_rag_collection_ids(store.review_ids(), settings.data_splits_dir)
    except (ValueError, OSError) as exc:
        raise AskPreflightError(f"RAG collection validation failed: {exc}") from exc
    logger.info(
        "ask_collection path=%s collection=%s embedding_model=%s",
        settings.chroma_path,
        store.collection_name,
        settings.embedding_model,
    )
    settings.export_hf_env()
    pipeline = RAGPipeline(Retriever(store, settings=settings), settings=settings)
    return pipeline.ask(**request.model_dump(exclude_none=True))
