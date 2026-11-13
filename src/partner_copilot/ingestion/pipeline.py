"""Tolerant JSONL ingestion with deterministic IDs, bounded chunks and progress accounting."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from partner_copilot.ingestion.aspects import AspectExtractor
from partner_copilot.ingestion.chunking import InvalidChunkInput, TextSplitter
from partner_copilot.ingestion.documents import IndexedDocument, WriteResult
from partner_copilot.schemas import Review

logger = logging.getLogger(__name__)


class DocumentStore(Protocol):
    def upsert_documents(
        self, documents: list[IndexedDocument], batch_size: int = 128
    ) -> WriteResult: ...


@dataclass
class IngestionReport:
    lines_read: int = 0
    read: int = 0
    valid: int = 0
    invalid: int = 0
    duplicates: int = 0
    blank: int = 0
    ignored: int = 0
    reviews_upserted: int = 0
    documents_upserted: int = 0
    inserted: int = 0
    updated: int = 0
    stale_deleted: int = 0
    batches: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def parse_review(line: str) -> Review:
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError("A review must be a JSON object")
    missing_id = "id" not in payload and "review_id" not in payload
    if "id" not in payload:
        payload["id"] = "pending-content-id" if missing_id else payload["review_id"]
    review = Review.model_validate(payload)
    if not review.id.strip() or not review.restaurant_id.strip():
        raise ValueError("Review and restaurant IDs must not be blank")
    if not review.text.strip():
        raise ValueError("Review text must not be blank")
    if missing_id:
        identity = json.dumps(
            [review.restaurant_id, review.created_at.isoformat(), review.text],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        review = review.model_copy(
            update={"id": "review_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()}
        )
    return review


def index_documents(review: Review, pieces: list[str]) -> list[IndexedDocument]:
    if not pieces or any(not isinstance(piece, str) or not piece.strip() for piece in pieces):
        raise InvalidChunkInput("Splitter must produce non-empty text chunks")
    fields = review.model_dump(exclude={"created_at_int", "id", "text"})
    documents = []
    for index, piece in enumerate(pieces):
        document_id = (
            review.id
            if len(pieces) == 1
            else "chunk_"
            + hashlib.sha256(
                json.dumps([review.id, index], separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        )
        documents.append(
            IndexedDocument(
                **fields,
                id=document_id,
                text=piece,
                review_id=review.id,
                chunk_index=index,
                chunk_count=len(pieces),
            )
        )
    return documents


def rejection_reason(exc: ValueError) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, error['loc']))}:{error['type']}"
            for error in exc.errors(include_input=False, include_context=False, include_url=False)[
                :5
            ]
        )
    if isinstance(exc, json.JSONDecodeError):
        return f"json:{exc.msg}"
    return str(exc)


class IngestionPipeline:
    def __init__(
        self,
        store: DocumentStore,
        splitter: TextSplitter,
        *,
        batch_size: int = 128,
        max_review_chars: int = 50000,
        aspect_extractor: AspectExtractor | None = None,
    ) -> None:
        if batch_size < 1 or max_review_chars < 1:
            raise ValueError("batch_size and max_review_chars must be positive")
        self.store, self.splitter = store, splitter
        self.aspect_extractor = aspect_extractor
        self.batch_size, self.max_review_chars = batch_size, max_review_chars

    def run(self, path: Path) -> IngestionReport:
        report = IngestionReport()
        pending: list[IndexedDocument] = []
        seen: dict[str, Review] = {}

        def flush() -> None:
            if not pending:
                return
            try:
                result = self.store.upsert_documents(pending, batch_size=self.batch_size)
            except Exception as exc:
                logger.error(
                    "ingestion_write_failed error_type=%s completed=%s; retry is safe",
                    type(exc).__name__,
                    report.to_dict(),
                )
                raise
            report.reviews_upserted += len({doc.review_id for doc in pending})
            report.documents_upserted += len(pending)
            report.inserted += result.inserted
            report.updated += result.updated
            report.stale_deleted += result.stale_deleted
            report.batches += 1
            logger.info("ingestion_progress %s", report.to_dict())
            pending.clear()

        logger.info("ingestion_started batch_size=%d", self.batch_size)
        with path.open(encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                report.lines_read += 1
                if not line.strip():
                    report.blank += 1
                    report.ignored += 1
                    continue
                report.read += 1
                try:
                    review = parse_review(line)
                    if len(review.text) > self.max_review_chars:
                        raise ValueError("Review exceeds the configured character safety limit")
                except (ValidationError, ValueError) as exc:
                    report.invalid += 1
                    report.ignored += 1
                    logger.warning(
                        "invalid_record line=%d reason=%s", line_number, rejection_reason(exc)
                    )
                    continue
                if review.id in seen:
                    report.valid += 1
                    report.duplicates += 1
                    report.ignored += 1
                    logger.warning(
                        "duplicate_review line=%d conflict=%s; first valid row wins",
                        line_number,
                        seen[review.id] != review,
                    )
                    continue
                try:
                    documents = index_documents(review, self.splitter.split(review.text))
                except InvalidChunkInput as exc:
                    report.invalid += 1
                    report.ignored += 1
                    logger.warning(
                        "invalid_chunk_input line=%d reason=%s", line_number, rejection_reason(exc)
                    )
                    continue
                report.valid += 1
                seen[review.id] = review
                if pending and len(pending) + len(documents) > self.batch_size:
                    flush()
                if self.aspect_extractor is not None:
                    extraction = self.aspect_extractor.extract(review)
                    if extraction.status == "inválido":
                        logger.warning(
                            "invalid_aspect_extraction review_id=%s extractor_version=%s",
                            review.id,
                            self.aspect_extractor.version,
                        )
                    for document in documents:
                        document.aspects = extraction.aspects
                        document.extractor_version = self.aspect_extractor.version
                        document.extractor_status = extraction.status
                pending.extend(documents)
                if len(pending) >= self.batch_size:
                    flush()
        flush()
        logger.info("ingestion_completed %s", report.to_dict())
        return report
