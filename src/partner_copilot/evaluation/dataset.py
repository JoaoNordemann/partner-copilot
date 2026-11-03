"""Validated, frozen development set for retrieval and abstention calibration."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from partner_copilot.schemas import Review

EXPECTED_COUNTS = {
    "restaurante_aspecto": 8,
    "temporal": 5,
    "item": 5,
    "parafrase": 6,
    "sem_resposta": 6,
}


def text_hash(path: Path) -> str:
    """Stable on Git checkouts with LF or CRLF."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


class QueryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    restaurant_id: str = Field(min_length=1)
    item: str | None = Field(default=None, min_length=1)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def valid_window(self) -> "QueryFilters":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Inverted date window")
        return self

    def matches(self, review: Review) -> bool:
        return (
            review.restaurant_id == self.restaurant_id
            and (self.item is None or review.item == self.item)
            and (self.start_date is None or review.created_at >= self.start_date)
            and (self.end_date is None or review.created_at <= self.end_date)
        )


class EvalQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^q[0-9]{2}$")
    pergunta: str = Field(min_length=1)
    tipo: Literal["restaurante_aspecto", "temporal", "item", "parafrase", "sem_resposta"]
    filtros: QueryFilters
    relevantes: list[str]
    deve_abster: bool
    criterio: str = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_relevance(self) -> "EvalQuestion":
        if len(self.relevantes) != len(set(self.relevantes)):
            raise ValueError("Duplicate relevant IDs")
        if self.deve_abster != (not self.relevantes) or self.deve_abster != (
            self.tipo == "sem_resposta"
        ):
            raise ValueError("Abstention, question type and relevance disagree")
        return self


def load_eval_set(folder: Path) -> tuple[list[EvalQuestion], list[Review], dict]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for filename, digest in manifest["file_sha256_lf"].items():
        if text_hash(folder / filename) != digest:
            raise ValueError(f"Eval snapshot checksum mismatch: {filename}")
    questions = [
        EvalQuestion.model_validate_json(line)
        for line in (folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    corpus = [
        Review.model_validate_json(line)
        for line in (folder / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    by_id = {review.id: review for review in corpus}
    if len(by_id) != len(corpus) or len(corpus) != manifest["corpus_count"]:
        raise ValueError("Duplicate IDs or incorrect corpus count")
    if sorted(by_id) != manifest["corpus_ids"]:
        raise ValueError("Corpus IDs differ from manifest")
    if Counter(q.tipo for q in questions) != EXPECTED_COUNTS:
        raise ValueError("Question composition differs from the 30-question protocol")
    if len({q.id for q in questions}) != 30:
        raise ValueError("Duplicate question IDs")
    for question in questions:
        for identifier in question.relevantes:
            if identifier not in by_id or not question.filtros.matches(by_id[identifier]):
                raise ValueError(
                    f"Relevant ID outside corpus or filters: {question.id}/{identifier}"
                )
    return questions, corpus, manifest
