"""Validate citation syntax and normalize the machine-readable refusal marker."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from partner_copilot.generation.contracts import (
    ABSTENTION_MARKER,
    ABSTENTION_MESSAGE,
    GenerationContractError,
    InvalidCitationError,
)
from partner_copilot.schemas import RetrievedDoc


@dataclass(frozen=True)
class ParsedGeneration:
    answer: str
    sources: list[str]
    abstained: bool


def parse_generation(text: str, docs: Sequence[RetrievedDoc]) -> ParsedGeneration:
    if not isinstance(text, str) or not text.strip():
        raise GenerationContractError("Empty or non-text model output")
    text = text.strip()
    if text == ABSTENTION_MARKER:
        return ParsedGeneration(ABSTENTION_MESSAGE, [], True)
    if ABSTENTION_MARKER in text:
        raise GenerationContractError("Abstention marker must be the complete output")
    valid_ids = {doc.review.id for doc in docs}
    invalid = [
        identifier
        for identifier in re.findall(r"\[([^\[\]\r\n]+)\]", text)
        if identifier not in valid_ids
    ]
    if invalid:
        raise InvalidCitationError(invalid, valid_ids)
    sources = []
    for line in text.splitlines():
        if not line.strip():
            continue
        content = re.sub(r"\[[^\[\]\r\n]+\]", "", line).strip(" .!?-")
        if not content:
            raise GenerationContractError("Citation-only output is not an answer")
        citations = re.findall(r"\[([^\[\]\r\n]+)\]", line)
        if not citations or not re.search(r"(?:\[[A-Za-z0-9_-]+\]\s*)+[.!?]?$", line):
            raise GenerationContractError("Every output line must end with a source citation")
        for identifier in citations:
            if identifier not in sources:
                sources.append(identifier)
    return ParsedGeneration(text, sources, False)
