"""Retrospective diagnostics over saved model outputs; never calls an LLM."""

import re
from collections import Counter

from partner_copilot.generation.contracts import ABSTENTION_MARKER, GenerationContractError
from partner_copilot.generation.output import parse_generation
from partner_copilot.generation.output_json_v1 import inspect_generation as inspect_json
from partner_copilot.generation.output_v3 import inspect_generation as inspect_v3
from partner_copilot.schemas import RetrievedDoc, Review


def context_docs(row: dict, reviews: dict[str, Review]) -> list[RetrievedDoc]:
    return [
        RetrievedDoc(
            review=reviews[d["review_id"]].model_copy(update={"text": d["text"]}), score=d["score"]
        )
        for d in row["context"]
    ]


def inspect_saved(row: dict, reviews: dict[str, Review], parser: str) -> dict:
    if not row["llm_called"]:
        return {
            "llm_called": False,
            "schema_valid": None,
            "parser_accepted": None,
            "ids_in_context": None,
            "quotes_literal": None,
        }
    docs = context_docs(row, reviews)
    text = row["raw_response"]
    if parser in ("parser-v1", "parser-v2"):
        normalized = text.replace(r"\_", "_") if parser == "parser-v2" else text
        tokens = re.findall(r"\[([^\[\]\r\n]+)\]", normalized)
        allowed = {d.review.id for d in docs}
        ids_ok = (
            None
            if normalized.strip() == ABSTENTION_MARKER
            else bool(tokens) and all(t in allowed for t in tokens)
        )
        try:
            parse_generation(text, docs, parser_version=parser)
            accepted = True
        except GenerationContractError:
            accepted = False
        return {
            "llm_called": True,
            "schema_valid": None,
            "parser_accepted": accepted,
            "ids_in_context": ids_ok,
            "quotes_literal": None,
        }
    diagnostic = (inspect_v3 if parser == "parser-v3" else inspect_json)(text, docs)
    return {"llm_called": True, **diagnostic}


def fraction(values: list[bool | None]) -> dict:
    applicable = [v for v in values if v is not None]
    return {"passed": sum(bool(v) for v in applicable), "applicable": len(applicable)}


def summarize_saved(rows: list[dict], reviews: dict[str, Review], parser: str) -> dict:
    ids = [r["question_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate experiment/question IDs")
    diagnostics = {r["question_id"]: inspect_saved(r, reviews, parser) for r in rows}
    called = [r for r in rows if r["llm_called"]]
    ds = [diagnostics[r["question_id"]] for r in called]
    for r in called:
        recorded = r.get("accepted")
        if recorded is None:
            recorded = r.get("error") is None and r.get("answer") is not None
        if recorded != diagnostics[r["question_id"]]["parser_accepted"]:
            raise ValueError("Saved acceptance differs from frozen parser")
    positives = [r for r in rows if not r["deve_abster"]]
    evidence = sum(bool(set(r["relevant_ids"]) & set(r["context_ids"])) for r in positives)
    return {
        "questions": len(rows),
        "llm_outputs": len(called),
        "no_llm": len(rows) - len(called),
        "schema": fraction([d["schema_valid"] for d in ds]),
        "accepted": fraction([d["parser_accepted"] for d in ds]),
        "ids": fraction([d["ids_in_context"] for d in ds]),
        "quotes": fraction([d.get("quotes_literal") for d in ds]),
        "positive_context_evidence": {"passed": evidence, "applicable": len(positives)},
        "ignored_suffix": sum(bool(d.get("trailing_text_ignored")) for d in ds),
        "error_types": dict(Counter(r["error"]["type"] for r in called if r.get("error"))),
        "diagnostics": diagnostics,
    }
