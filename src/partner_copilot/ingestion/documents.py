"""Indexed chunks and write accounting, separate from the source review schema."""

from dataclasses import dataclass

from pydantic import Field

from partner_copilot.schemas import Review


class IndexedDocument(Review):
    review_id: str = Field(min_length=1)
    chunk_index: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=1, ge=1)


@dataclass
class WriteResult:
    inserted: int = 0
    updated: int = 0
    stale_deleted: int = 0
