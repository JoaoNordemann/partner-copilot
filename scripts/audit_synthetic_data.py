"""Audit exact repetition, ratings, weak aspects and delivery trends in synthetic data."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


def repetition_metrics(rows: list[dict]) -> dict:
    # Literal, case-sensitive sentences: retain punctuation; trim separator whitespace only.
    sentences = Counter(
        sentence.strip()
        for row in rows
        for sentence in re.split(r"(?<=[.!?])\s+", row["text"])
        if sentence.strip()
    )
    texts = Counter(row["text"] for row in rows)
    repeated = {text: count for text, count in sentences.items() if count > 1}
    return {
        "sentence_occurrences": sum(sentences.values()),
        "distinct_sentences": len(sentences),
        "distinct_repeated_sentences": len(repeated),
        "excess_sentence_occurrences": sum(count - 1 for count in repeated.values()),
        "repeated_sentence_occurrences": sum(repeated.values()),
        "top_repeated": sentences.most_common(10),
        "distinct_duplicate_review_texts": sum(count > 1 for count in texts.values()),
        "excess_duplicate_review_texts": sum(count - 1 for count in texts.values()),
    }


def negative_rate(rows: list[dict], aspect: str) -> dict:
    labels = [row["aspects"][aspect] for row in rows if aspect in row["aspects"]]
    negatives = labels.count("neg")
    return {
        "negative": negatives,
        "mentioned": len(labels),
        "rate": negatives / len(labels) if labels else None,
    }


def audit(rows: list[dict], restaurants: tuple, end: date) -> dict:
    cutoff = end - timedelta(days=13)
    weaknesses = []
    for restaurant in restaurants:
        for aspect in restaurant.weak_aspects:
            eligible = [
                row
                for row in rows
                if aspect != "tempo_entrega" or date.fromisoformat(row["created_at"]) < cutoff
            ]
            target = [row for row in eligible if row["restaurant_id"] == restaurant.restaurant_id]
            baseline_ids = {
                rest.restaurant_id for rest in restaurants if aspect not in rest.weak_aspects
            }
            baseline = [row for row in eligible if row["restaurant_id"] in baseline_ids]
            weaknesses.append(
                {
                    "restaurant_id": restaurant.restaurant_id,
                    "aspect": aspect,
                    "restaurant": negative_rate(target, aspect),
                    "baseline": negative_rate(baseline, aspect),
                }
            )
    weeks = []
    for offset in range(5, -1, -1):
        week_end = end - timedelta(days=7 * offset)
        week_start = week_end - timedelta(days=6)
        for restaurant_id in ("rest_002", "rest_004"):
            window = [
                row
                for row in rows
                if row["restaurant_id"] == restaurant_id
                and week_start <= date.fromisoformat(row["created_at"]) <= week_end
            ]
            weeks.append(
                {
                    "restaurant_id": restaurant_id,
                    "start": week_start.isoformat(),
                    "end": week_end.isoformat(),
                    "reviews": len(window),
                    **negative_rate(window, "tempo_entrega"),
                }
            )
    trend = {}
    for restaurant_id in ("rest_002", "rest_004"):
        subset = [row for row in rows if row["restaurant_id"] == restaurant_id]
        trend[restaurant_id] = {
            "historical": negative_rate(
                [row for row in subset if date.fromisoformat(row["created_at"]) < cutoff],
                "tempo_entrega",
            ),
            "recent": negative_rate(
                [row for row in subset if cutoff <= date.fromisoformat(row["created_at"]) <= end],
                "tempo_entrega",
            ),
        }
    return {
        "reviews": len(rows),
        "repetition": repetition_metrics(rows),
        "ratings": dict(sorted(Counter(row["rating"] for row in rows).items())),
        "mean_rating": sum(row["rating"] for row in rows) / len(rows),
        "five_star_with_negative_aspect": sum(
            row["rating"] == 5 and "neg" in row["aspects"].values() for row in rows
        ),
        "weaknesses": weaknesses,
        "weeks": weeks,
        "trend": trend,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/reviews.jsonl"))
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generator_path = Path(__file__).with_name("generate_synthetic_data.py")
    spec = importlib.util.spec_from_file_location("audited_generator", generator_path)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)
    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        parser.error("Input must contain at least one review")
    result = audit(rows, generator.RESTAURANTS, args.end_date)
    payload = json.dumps(result, ensure_ascii=True, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
