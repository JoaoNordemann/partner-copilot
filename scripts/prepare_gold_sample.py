#!/usr/bin/env python
"""Prepare a reproducible, label-blind annotation sample without consulting generated aspects."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

POSITIVE = re.compile(
    r"gostei|bom|boa|ótim|otim|delícia|delicia|no prazo|dentro do prazo|rápid|rapid|"
    r"antes do previsto|bem fechada|lacrada|lacre estava inteiro|bem resistente|prestativ|educad"
)
NEGATIVE = re.compile(
    r"atras|demor|esperei|esperando|ruim|estranh|sem graça|sem graca|deixou a desejar|"
    r"não gostei|nao gostei|não vale|nao vale|caro|frio|morno|rompido|rasg|danific|"
    r"tampa veio solta|sem lacre|aberta|ninguém|ninguem|ignorou|grossos|requenta|esquentar"
)


def text_hash(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def mixed_candidate(text: str) -> bool:
    """Lexical selection aid only, not an annotation or a generated-label lookup."""
    return bool(POSITIVE.search(text.casefold()) and NEGATIVE.search(text.casefold()))


def select_reviews(rows: list[dict], exposure: dict, seed: int) -> tuple[list[dict], dict]:
    excluded_ids = set(exposure["ids"])
    excluded_texts = set(exposure["normalized_text_sha256"])
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    seen: set[str] = set()
    for row in sorted(rows, key=lambda row: row["id"]):
        identity = text_hash(row["text"])
        if row["id"] in excluded_ids or identity in excluded_texts or identity in seen:
            continue
        seen.add(identity)
        # Intentionally never access the source field "aspects".
        groups[row["restaurant_id"], row["rating"]].append(
            {
                "id": row["id"],
                "text": row["text"],
                "restaurant_id": row["restaurant_id"],
                "rating": row["rating"],
                "mixed_candidate": mixed_candidate(row["text"]),
            }
        )
    restaurants = sorted({row["restaurant_id"] for row in rows})
    if len(restaurants) != 8:
        raise ValueError("This reference sample expects eight restaurants")
    selected = []
    quotas = []
    for index, restaurant in enumerate(restaurants):
        for rating, base_quota in {1: 2, 2: 2, 3: 3, 4: 3, 5: 2}.items():
            quota = base_quota + int(index < 4 and rating == index + 1)
            pool = sorted(
                groups[restaurant, rating],
                key=lambda row: hashlib.sha256(f"{seed}:{row['id']}".encode()).hexdigest(),
            )
            if len(pool) < quota:
                raise ValueError(f"Insufficient unexposed rows in {restaurant}, rating {rating}")
            hard = [row for row in pool if row["mixed_candidate"]][: quota // 2]
            hard_ids = {row["id"] for row in hard}
            chosen = hard + [row for row in pool if row["id"] not in hard_ids][: quota - len(hard)]
            selected.extend(chosen)
            quotas.append({"restaurant_id": restaurant, "rating": rating, "count": quota})
    # Blind order does not reveal restaurant or rating strata.
    selected.sort(key=lambda row: hashlib.sha256(f"{seed}:blind:{row['id']}".encode()).hexdigest())
    return selected, {"quotas": quotas, "excluded_exposed_ids": len(excluded_ids)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/reviews.jsonl"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/gold"))
    parser.add_argument("--exposure", type=Path, default=Path("data/gold/prior_exposure.json"))
    parser.add_argument("--guide", type=Path, default=Path("docs/annotation-guide.md"))
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    guide = args.guide.read_bytes()
    if len(guide.decode("utf-8-sig").splitlines()) != 10:
        parser.error("The annotation guide must be written with exactly ten rules first")
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    exposure = json.loads(args.exposure.read_text(encoding="utf-8"))
    selected, details = select_reviews(rows, exposure, args.seed)
    blind_rows = [{"id": row["id"], "text": row["text"]} for row in selected]
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in blind_rows).encode(
        "utf-8"
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    blind_path = args.out_dir / "reviews_100.blind.jsonl"
    if blind_path.exists() and blind_path.read_bytes() != payload:
        raise ValueError("The existing blind sample is frozen; use another output directory")
    blind_path.write_bytes(payload)
    chosen_hashes = {text_hash(row["text"]) for row in selected}
    manifest = {
        "seed": args.seed,
        "count": len(selected),
        "source_sha256": hashlib.sha256(
            args.input.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest(),
        "source_hash_algorithm": "SHA256 of UTF-8 text normalized to LF line endings",
        "guide_sha256": hashlib.sha256(guide).hexdigest(),
        "blind_sample_sha256": hashlib.sha256(payload).hexdigest(),
        "selection_uses_generated_aspects": False,
        "mixed_candidate_method": "Lexical cues only; candidates may be false positives",
        "mixed_candidates": sum(row["mixed_candidate"] for row in selected),
        "restaurant_counts": dict(
            sorted(Counter(row["restaurant_id"] for row in selected).items())
        ),
        "rating_counts": dict(sorted(Counter(row["rating"] for row in selected).items())),
        "reserved_from_training_ids": sorted(
            row["id"] for row in rows if text_hash(row["text"]) in chosen_hashes
        ),
        "strata_by_id": [
            {key: row[key] for key in ("id", "restaurant_id", "rating")} for row in selected
        ],
        **details,
    }
    (args.out_dir / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "count",
                    "restaurant_counts",
                    "rating_counts",
                    "mixed_candidates",
                    "excluded_exposed_ids",
                    "blind_sample_sha256",
                )
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
