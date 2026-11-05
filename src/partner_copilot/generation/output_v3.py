"""V3: first JSON object, consistent abstention, exact source excerpts; no entailment claim."""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from partner_copilot.generation.contracts import (
    ABSTENTION_MESSAGE,
    GenerationContractError,
    InvalidCitationError,
)
from partner_copilot.generation.output_json_v1 import ReviewID, Text, _reject_constant, _unique_keys
from partner_copilot.generation.output_v1 import ParsedGeneration
from partner_copilot.schemas import RetrievedDoc


class SourceExcerpt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    review_id: ReviewID
    trecho: str = Field(min_length=1)

    @field_validator("trecho")
    @classmethod
    def nonblank_exact_quote(cls, value):
        if not value.strip():
            raise ValueError("Empty source excerpt")
        return value  # Preserve exact characters; never normalize the quote.


class GroundedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    texto: Text
    fontes: list[SourceExcerpt] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sources(self):
        ids = [source.review_id for source in self.fontes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate claim sources")
        return self


class GroundedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    abstem: bool
    afirmacoes: list[GroundedClaim]

    @model_validator(mode="after")
    def consistent_abstention(self):
        if self.abstem != (not self.afirmacoes):
            raise ValueError("Abstention and claims disagree")
        return self


@dataclass(frozen=True)
class DecodedOutput:
    value: GroundedOutput
    ignored_suffix: str


class QuoteMismatchError(GenerationContractError):
    code = "evidence_quote_not_found"


def decode_output(text: str) -> DecodedOutput:
    try:
        if not isinstance(text, str) or not text.lstrip().startswith("{"):
            raise ValueError("Output must begin with a JSON object")
        raw = text.lstrip()
        value, end = json.JSONDecoder(
            object_pairs_hook=_unique_keys, parse_constant=_reject_constant
        ).raw_decode(raw)
        return DecodedOutput(GroundedOutput.model_validate(value), raw[end:])
    except (ValueError, TypeError) as exc:
        raise GenerationContractError("V3 JSON schema validation failed") from exc


def _source_texts(docs):
    lookup = {}
    for doc in docs:
        lookup.setdefault(doc.review.id, []).append(doc.review.text)
    return lookup


def inspect_generation(text: str | None, docs: Sequence[RetrievedDoc]) -> dict:
    base = {
        "schema_valid": False,
        "abstained": None,
        "ids_in_context": None,
        "quotes_literal": None,
        "parser_accepted": False,
        "content_supported": None,
        "trailing_text_ignored": False,
        "ignored_suffix_chars": 0,
    }
    try:
        decoded = decode_output(text)
    except GenerationContractError:
        return base
    value = decoded.value
    base.update(
        schema_valid=True,
        abstained=value.abstem,
        trailing_text_ignored=bool(decoded.ignored_suffix.strip()),
        ignored_suffix_chars=len(decoded.ignored_suffix),
    )
    if value.abstem:
        base["parser_accepted"] = True
        return base
    lookup = _source_texts(docs)
    sources = [source for claim in value.afirmacoes for source in claim.fontes]
    base["ids_in_context"] = all(source.review_id in lookup for source in sources)
    if base["ids_in_context"]:
        base["quotes_literal"] = all(
            any(source.trecho in body for body in lookup[source.review_id]) for source in sources
        )
    base["parser_accepted"] = bool(base["ids_in_context"] and base["quotes_literal"])
    return base


def parse_generation(text: str, docs: Sequence[RetrievedDoc]) -> ParsedGeneration:
    value = decode_output(text).value
    if value.abstem:
        return ParsedGeneration(ABSTENTION_MESSAGE, [], True)
    lookup = _source_texts(docs)
    invalid = [
        source.review_id
        for claim in value.afirmacoes
        for source in claim.fontes
        if source.review_id not in lookup
    ]
    if invalid:
        raise InvalidCitationError(invalid, set(lookup))
    if any(
        not any(source.trecho in body for body in lookup[source.review_id])
        for claim in value.afirmacoes
        for source in claim.fontes
    ):
        raise QuoteMismatchError("Source excerpt does not occur literally in the cited context")
    lines, ids = [], []
    for claim in value.afirmacoes:
        for source in claim.fontes:
            if source.review_id not in ids:
                ids.append(source.review_id)
        prose = claim.texto.replace("[", r"\[").replace("]", r"\]")
        lines.append(
            prose + " " + " ".join("[" + source.review_id + "]" for source in claim.fontes)
        )
    return ParsedGeneration("\n".join(lines), ids, False)
