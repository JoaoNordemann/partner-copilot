"""Application orchestration for validated RAG ingestion and explicit collection resets."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from partner_copilot.config import Settings
from partner_copilot.data_splits import validate_rag_collection_ids, validate_rag_input
from partner_copilot.ingestion.aspects import build_aspect_extractor
from partner_copilot.ingestion.chunking import TokenTextSplitter
from partner_copilot.ingestion.pipeline import IngestionPipeline, IngestionReport

if TYPE_CHECKING:
    from partner_copilot.ingestion.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class IngestionPreflightError(ValueError):
    """Input or collection validation failed before ingestion or reset."""


@dataclass(frozen=True)
class IngestionOutcome:
    report: IngestionReport
    collection: str
    database_path: Path
    total_documents: int
    reset_removed: int = 0


def _create_store(settings: Settings) -> ChromaStore:
    # Keep CLI --help and rejected inputs independent from Chroma/model initialization.
    from partner_copilot.ingestion.chroma_store import ChromaStore

    return ChromaStore(path=settings.chroma_path, model=settings.embedding_model, settings=settings)


def run_ingestion(
    settings: Settings,
    *,
    input_path: Path | None = None,
    batch_size: int = 128,
    reset: bool = False,
) -> IngestionOutcome:
    if batch_size < 1:
        raise IngestionPreflightError("batch_size must be positive")
    path = input_path if input_path is not None else settings.data_splits_dir / "rag.jsonl"
    if not path.is_file():
        raise IngestionPreflightError(f"Input file does not exist: {path}")
    try:
        validate_rag_input(path, settings.data_splits_dir)
    except (ValueError, OSError) as exc:
        raise IngestionPreflightError(
            f"Split validation failed: {exc}. Run scripts/prepare_data_splits.py first."
        ) from exc
    try:
        extractor = build_aspect_extractor(settings)
    except (ValueError, OSError, KeyError) as exc:
        raise IngestionPreflightError(f"Aspect extractor configuration failed: {exc}") from exc
    settings.export_hf_env()
    store = _create_store(settings)
    if not reset:
        try:
            validate_rag_collection_ids(store.review_ids(), settings.data_splits_dir)
        except ValueError as exc:
            raise IngestionPreflightError(str(exc)) from exc
    try:
        splitter = TokenTextSplitter(
            store.embedder,
            max_tokens=settings.ingestion_chunk_max_tokens,
            overlap_tokens=settings.ingestion_chunk_overlap_tokens,
        )
    except ValueError as exc:
        raise IngestionPreflightError(str(exc)) from exc
    removed = 0
    if reset:
        # Verify tokenizer/model availability and the effective budget before deleting anything.
        splitter.prepare()
        removed = store.reset()
        logger.info("ingestion_reset collection=%s removed=%d", store.collection_name, removed)
    report = IngestionPipeline(
        store,
        splitter,
        batch_size=batch_size,
        max_review_chars=settings.ingestion_max_review_chars,
        aspect_extractor=extractor,
    ).run(path)
    return IngestionOutcome(
        report, store.collection_name, settings.chroma_path, store.count(), removed
    )
