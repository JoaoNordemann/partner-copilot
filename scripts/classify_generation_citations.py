"""Classify D citation rejections without changing parser behavior or source artifacts."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from partner_copilot.generation.contracts import InvalidCitationError
from partner_copilot.generation.output import parse_generation
from partner_copilot.schemas import RetrievedDoc, Review


def classify(row, reviews, known_ids=None):
    universe = set(reviews) if known_ids is None else set(known_ids)
    allowed = set(row["context_ids"])
    normalized = row["raw_response"].replace(r"\_", "_")
    docs = [RetrievedDoc(review=reviews[d["review_id"]], score=d["score"]) for d in row["context"]]
    try:
        parse_generation(row["raw_response"], docs, parser_version="parser-v2")
    except InvalidCitationError as exc:
        rejected = list(exc.invalid_ids)
    else:
        raise ValueError("Expected InvalidCitationError")
    assert rejected == list(
        dict.fromkeys(t for t in re.findall(r"\[([^\[\]\r\n]+)\]", normalized) if t not in allowed)
    )
    mentioned = sorted(set(re.findall(r"\b(?:rev|review)_\d+\b", " ".join(rejected))))
    real_outside = [
        identifier
        for identifier in mentioned
        if identifier in universe and identifier not in allowed
    ]
    altered = [identifier for identifier in mentioned if identifier not in universe]
    grouped = any("," in token and re.search(r"(?:rev|review)_\d+", token) for token in rejected)
    marker = "SEM_EVIDENCIA" in rejected
    boundaries = any(t in {"PERGUNTA_JSON", "AVALIACOES_JSONL"} for t in rejected)
    primary = (
        "real_id_outside_context"
        if real_outside
        else "altered_or_unknown_id"
        if altered
        else "grouped_context_ids"
        if grouped
        else "marker_as_citation"
        if marker
        else "boundary_as_citation"
        if boundaries
        else "prose_as_citation"
    )
    return {
        "question_id": row["question_id"],
        "primary_category": primary,
        "rejected_tokens_after_parser_v2_normalization": rejected,
        "context_ids": row["context_ids"],
        "mentioned_review_ids": mentioned,
        "real_ids_outside_context": real_outside,
        "altered_or_unknown_ids": altered,
        "grouped_ids": grouped,
        "marker_as_citation": marker,
        "boundary_as_citation": boundaries,
        "escaped_underscores_present_but_already_normalized": r"\_" in row["raw_response"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/eval/human-v2/corpus.jsonl"))
    parser.add_argument("--raw-corpus", type=Path, default=Path("data/raw/reviews.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error("Choose a new output")
    data = args.source.read_bytes()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    reviews = {
        r.id: r
        for r in (
            Review.model_validate_json(line)
            for line in args.corpus.read_text(encoding="utf-8").splitlines()
        )
    }
    known_ids = set(reviews) | {
        json.loads(line)["id"]
        for line in args.raw_corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    rejected = [
        classify(row, reviews, known_ids)
        for row in rows
        if (row.get("error") or {}).get("type") == "InvalidCitationError"
    ]
    report = {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "classification_version": "citation-diagnostic-v1",
        "reviewer": "Codex",
        "origin": "AI/code",
        "known_corpus_id_count": len(known_ids),
        "raw_corpus_sha256": hashlib.sha256(args.raw_corpus.read_bytes()).hexdigest(),
        "primary_category_counts": dict(Counter(r["primary_category"] for r in rejected)),
        "all_error_messages": dict(Counter(r["error"]["message"] for r in rows if r["error"])),
        "real_outside_context_cases": sum(bool(r["real_ids_outside_context"]) for r in rejected),
        "cases": rejected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
