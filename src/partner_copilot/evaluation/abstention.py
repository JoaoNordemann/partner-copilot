"""Versioned diagnostic metrics; tolerant detection never changes parser acceptance."""

import re

from partner_copilot.generation.contracts import ABSTENTION_MARKER


def detect_abstention(text: str | None, context_ids: list[str], *, normalize: bool = False) -> dict:
    value = text if isinstance(text, str) else ""
    if normalize:
        value = value.replace(r"\_", "_")
    allowed = set(context_ids)
    citations = re.findall(r"\[([^\[\]\r\n]+)\]", value)
    valid = sorted({identifier for identifier in citations if identifier in allowed})
    return {
        "strict": value.strip() == ABSTENTION_MARKER,
        "tolerant": ABSTENTION_MARKER in value and not valid,
        "valid_citation_ids": valid,
    }


def abstention_report(rows: list[dict]) -> dict:
    ids = [row["question_id"] for row in rows]
    if len(ids) != 30 or set(ids) != {f"q{i:02}" for i in range(1, 31)}:
        raise ValueError("Diagnostics require all 30 unique questions")
    reports = {}
    for normalize in (False, True):
        details = [
            {
                "question_id": row["question_id"],
                "llm_called": row["llm_called"],
                **detect_abstention(
                    row.get("raw_response"), row["context_ids"], normalize=normalize
                ),
            }
            for row in rows
        ]
        indexed = {row["question_id"]: row for row in details}
        groups = {
            "all_llm_calls": [r for r in rows if r["llm_called"]],
            "negative_llm_calls": [r for r in rows if r["llm_called"] and r["deve_abster"]],
            "positive_llm_calls": [r for r in rows if r["llm_called"] and not r["deve_abster"]],
            "hard_negative_llm_calls": [
                r
                for r in rows
                if r["llm_called"] and r["question_id"] in {"q25", "q26", "q27", "q28"}
            ],
        }
        metrics = {}
        for name, group in groups.items():
            metrics[name] = {}
            for mode in ("strict", "tolerant"):
                count = sum(indexed[r["question_id"]][mode] for r in group)
                metrics[name][mode] = {
                    "numerator": count,
                    "denominator": len(group),
                    "rate": count / len(group) if group else None,
                }
        for label, negative in (("negative_pipeline", True), ("positive_pipeline", False)):
            group = [r for r in rows if r["deve_abster"] == negative]
            metrics[label] = {}
            for mode in ("strict", "tolerant"):
                count = sum(
                    indexed[r["question_id"]][mode]
                    if r["llm_called"]
                    else bool(
                        r.get("answer")
                        and r["answer"].get("abstained")
                        and r["answer"].get("abstention_reason") == "retriever_empty"
                    )
                    for r in group
                )
                metrics[label][mode] = {
                    "numerator": count,
                    "denominator": len(group),
                    "rate": count / len(group) if group else None,
                }
        reports["normalized_underscores" if normalize else "raw"] = {
            "metrics": metrics,
            "questions": details,
        }
    return {
        "metric_version": "abstention-diagnostic-v1",
        "complete": True,
        "warning": (
            "Tolerant detection is diagnostic, not evidence validation or parser acceptance."
        ),
        "views": reports,
    }
