"""Streaming JSONL reader with actionable validation errors."""

from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from partner_copilot.schemas import Review


def load_reviews(path: Path) -> Iterator[Review]:
    with path.open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                yield Review.model_validate_json(line)
            except ValidationError as exc:
                raise ValueError(f"{path}: line {line_number}: invalid review: {exc}") from exc
