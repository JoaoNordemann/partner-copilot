"""Strict structured output: schema first, context membership second, rendering in code."""

import json
from collections.abc import Sequence
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from partner_copilot.generation.contracts import (
    ABSTENTION_MESSAGE,
    GenerationContractError,
    InvalidCitationError,
)
from partner_copilot.generation.output_v1 import ParsedGeneration
from partner_copilot.schemas import RetrievedDoc

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ReviewID = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$", min_length=1)]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    texto: Text
    review_ids: list[ReviewID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sources(self):
        if len(set(self.review_ids)) != len(self.review_ids):
            raise ValueError("Duplicate claim sources")
        return self


class StructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    abstem: bool
    afirmacoes: list[Claim]

    @model_validator(mode="after")
    def consistent_abstention(self):
        if self.abstem != (not self.afirmacoes):
            raise ValueError("Abstention requires empty claims; answers require claims")
        return self


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON constant")


def validate_schema(text: str) -> StructuredOutput:
    try:
        if not isinstance(text, str):
            raise ValueError("Non-text output")
        value = json.loads(text, object_pairs_hook=_unique_keys, parse_constant=_reject_constant)
        return StructuredOutput.model_validate(value)
    except (ValueError, TypeError, ValidationError) as exc:
        raise GenerationContractError("Structured JSON schema validation failed") from exc


def parse_generation(text: str, docs: Sequence[RetrievedDoc]) -> ParsedGeneration:
    value = validate_schema(text)
    if value.abstem:
        return ParsedGeneration(ABSTENTION_MESSAGE, [], True)
    allowed = {doc.review.id for doc in docs}
    invalid = [
        identifier
        for claim in value.afirmacoes
        for identifier in claim.review_ids
        if identifier not in allowed
    ]
    if invalid:
        raise InvalidCitationError(invalid, allowed)
    sources, lines = [], []
    for claim in value.afirmacoes:
        for identifier in claim.review_ids:
            if identifier not in sources:
                sources.append(identifier)
        # Literal brackets in prose are not citations; all citations come from review_ids.
        prose = claim.texto.replace("[", r"\[").replace("]", r"\]")
        lines.append(
            prose + " " + " ".join("[" + identifier + "]" for identifier in claim.review_ids)
        )
    return ParsedGeneration("\n".join(lines), sources, False)


def inspect_generation(text: str | None, docs: Sequence[RetrievedDoc]) -> dict:
    try:
        value = validate_schema(text)
    except GenerationContractError:
        return {
            "schema_valid": False,
            "abstained": None,
            "ids_in_context": None,
            "parser_accepted": False,
            "content_supported": None,
        }
    result = {
        "schema_valid": True,
        "abstained": value.abstem,
        "ids_in_context": None
        if value.abstem
        else all(
            identifier in {doc.review.id for doc in docs}
            for claim in value.afirmacoes
            for identifier in claim.review_ids
        ),
        "parser_accepted": False,
        "content_supported": None,
    }
    result["parser_accepted"] = value.abstem or result["ids_in_context"]
    return result
