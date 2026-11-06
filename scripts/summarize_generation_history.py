#!/usr/bin/env python
"""Consolidate frozen generation outputs with no inference or parser changes."""

import argparse
import hashlib
import json
from pathlib import Path

from partner_copilot.evaluation.retrospective import summarize_saved
from partner_copilot.schemas import Review

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "v1": "reports/generation-kaggle-v1/generation-kaggle-v1.jsonl",
    "B": "reports/generation-kaggle-v2/generation-kaggle-B-prompt-v2-parser-v1.jsonl",
    "C": "reports/generation-kaggle-v2/generation-kaggle-C-parser-v2.jsonl",
    "D": "reports/generation-kaggle-D/generation-kaggle-D.jsonl",
    "json-v1": "reports/generation-json-v1/generation-json-v1.jsonl",
    "v3-old": "reports/final-v3/generation-v3-contaminated.jsonl",
    "v3-new": "reports/final-v3/generation-v3-new.jsonl",
}
PARSERS = {
    "v1": "parser-v1",
    "C": "parser-v2",
    "D": "parser-v2",
    "json-v1": "parser-json-v1",
    "v3-old": "parser-v3",
    "v3-new": "parser-v3",
}


def load_sources(root: Path = ROOT) -> tuple[dict, dict]:
    rows, hashes = {}, {}
    for name, relative in SOURCES.items():
        data = (root / relative).read_bytes()
        hashes[relative] = hashlib.sha256(data).hexdigest()
        rows[name] = [
            json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()
        ]
    b = {r["question_id"]: r for r in rows["B"]}
    for row in rows["C"]:
        if row["source_sha256"] != hashes[SOURCES["B"]]:
            raise ValueError("C is not a replay of this B artifact")
    rows["C"] = [{**b[r["question_id"]], **r} for r in rows["C"]]
    return rows, hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources, hashes = load_sources()
    reviews = {
        r.id: r
        for r in (
            Review.model_validate_json(line)
            for line in (ROOT / "data/eval/human-v2/corpus.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    metrics = {
        name: summarize_saved(sources[name], reviews, version) for name, version in PARSERS.items()
    }
    payload = {
        "new_inference": False,
        "source_sha256": hashes,
        "parser_versions": PARSERS,
        "experiments": metrics,
        "notes": [
            "C and D are experiment names, not prompt versions.",
            "Text contracts do not have a JSON schema or excerpt field.",
            "Each diagnostic has its own denominator; abstentions have no IDs/excerpts.",
            "C creates no new LLM outputs; D reuses B plus 25 corrective calls.",
            "Only v3-new was clean relative to adjustment on those questions "
            "at its frozen execution.",
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for name, metric in metrics.items():
        print(
            name,
            json.dumps({k: v for k, v in metric.items() if k != "diagnostics"}, ensure_ascii=True),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
