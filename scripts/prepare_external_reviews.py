#!/usr/bin/env python
"""Prepare an isolated, non-commercial B2W sample for domain-shift evaluation.

No external code is executed and no Chroma collection is opened.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REVISION = "4639429ec698d7821fc99a0bc665fa213d9fcd5a"
SOURCE_ROOT = f"https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/{REVISION}"
SOURCE_URL = f"{SOURCE_ROOT}/B2W-Reviews01.csv"
SOURCE_SHA256 = "821fb0bf9f7230b0fba4e4f9fadd75a66d1a9ff0b1657810791d33007eb2ab38"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|\b\d{10,14}\b")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError("External data preparation timebox exceeded")


def fetch(url: str, destination: Path, deadline: float) -> None:
    """Bound network duration and publish a completed download atomically."""
    temporary = destination.with_suffix(destination.suffix + ".part")
    check_deadline(deadline)
    try:
        timeout = min(30.0, max(0.1, deadline - time.monotonic()))
        with urlopen(url, timeout=timeout) as response, temporary.open("wb") as target:
            total = 0
            while chunk := response.read(1024 * 1024):
                check_deadline(deadline)
                total += len(chunk)
                if total > 100 * 1024 * 1024:
                    raise ValueError("Unexpected source size: exceeds 100 MiB")
                target.write(chunk)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def select_sample(
    source: Path, per_rating: int = 40, seed: int = 42, *, deadline: float | None = None
) -> tuple[list[dict], dict]:
    """Select unique texts by stable hash rank, with equal quotas for each star rating."""
    if per_rating < 1:
        raise ValueError("per_rating must be positive")
    buckets: dict[int, list] = {rating: [] for rating in range(1, 6)}
    seen: set[bytes] = set()
    stats: Counter = Counter()
    original_ratings: Counter = Counter()
    eligible_ratings: Counter = Counter()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        # The pinned CSV is comma-delimited, despite the upstream README's spreadsheet advice.
        reader = csv.DictReader(stream)
        if not {"review_text", "overall_rating"}.issubset(reader.fieldnames or []):
            raise ValueError("Missing review_text or overall_rating CSV columns")
        for index, row in enumerate(reader, start=1):
            if deadline is not None:
                check_deadline(deadline)
            stats["source_rows"] += 1
            try:
                rating = int(row["overall_rating"])
            except (ValueError, TypeError):
                stats["invalid_rating"] += 1
                continue
            if rating not in buckets:
                stats["invalid_rating"] += 1
                continue
            original_ratings[rating] += 1
            text = (row["review_text"] or "").strip()
            if not 20 <= len(text) <= 2000:
                stats["excluded_length"] += 1
                continue
            if CONTACT.search(text):
                stats["excluded_obvious_contact"] += 1
                continue
            normalized = " ".join(text.casefold().split())
            identity = hashlib.sha256(normalized.encode("utf-8")).digest()
            if identity in seen:
                stats["excluded_duplicate_text"] += 1
                continue
            seen.add(identity)
            eligible_ratings[rating] += 1
            record = {
                "external_id": f"b2w_row_{index:06d}",
                "source_row": index,
                "domain": "ecommerce",
                "text": text,
                "overall_rating": rating,
                "annotation_status": "unannotated",
            }
            rank = int.from_bytes(hashlib.sha256(f"{seed}\0{normalized}".encode()).digest(), "big")
            heapq.heappush(buckets[rating], (-rank, -index, record))
            if len(buckets[rating]) > per_rating:
                heapq.heappop(buckets[rating])
    if any(len(bucket) < per_rating for bucket in buckets.values()):
        raise ValueError("Not enough unique eligible texts for every rating quota")
    records = sorted(
        (entry[2] for bucket in buckets.values() for entry in bucket),
        key=lambda record: record["source_row"],
    )
    return records, {
        **stats,
        "source_rating_counts": dict(sorted(original_ratings.items())),
        "eligible_unique_rating_counts": dict(sorted(eligible_ratings.items())),
        "selected_rating_counts": dict(
            sorted(Counter(r["overall_rating"] for r in records).items())
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--per-rating", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-budget-minutes", type=float, default=10)
    args = parser.parse_args()
    from partner_copilot.config import get_settings

    settings = get_settings()
    args.out_dir = args.out_dir if args.out_dir is not None else settings.external_reviews_dir
    if args.per_rating < 1 or not 0 < args.time_budget_minutes <= 90:
        parser.error("per-rating must be positive and time budget must be in (0, 90] minutes")
    started = time.monotonic()
    deadline = started + args.time_budget_minutes * 60
    args.out_dir.mkdir(parents=True, exist_ok=True)
    readme = args.out_dir / "SOURCE_README.md"
    if not readme.exists():
        fetch(f"{SOURCE_ROOT}/README.md", readme, deadline)
    license_evidence = readme.read_text(encoding="utf-8")
    if "by-nc-sa/4.0" not in license_evidence or "NonCommercial" not in license_evidence:
        raise ValueError("Expected source license was not confirmed; refusing to use the CSV")
    csv_path = args.out_dir / "B2W-Reviews01.csv"
    if not csv_path.exists():
        fetch(SOURCE_URL, csv_path, deadline)
    source_hash = file_sha256(csv_path)
    if source_hash != SOURCE_SHA256:
        raise ValueError("Source CSV checksum mismatch; remove it and download the pinned revision")
    records, stats = select_sample(csv_path, args.per_rating, args.seed, deadline=deadline)
    output = args.out_dir / "reviews_sample.jsonl"
    payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    output.write_bytes(payload.encode("utf-8"))
    manifest = {
        "dataset": "B2W-Reviews01",
        "credit": "B2W Digital; Livy Real, Marcio Oshiro and Alexandre Mafra (STIL 2019)",
        "hf_catalog": "https://huggingface.co/datasets/ruanchaves/b2w-reviews01",
        "original_repository": "https://github.com/americanas-tech/b2w-reviews01",
        "revision": REVISION,
        "source_url": SOURCE_URL,
        "source_sha256": source_hash,
        "license": "CC-BY-NC-SA-4.0",
        "license_url": LICENSE_URL,
        "license_evidence_url": f"{SOURCE_ROOT}/README.md",
        "license_evidence_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
        "license_conflict": "HF metadata says CC-BY-4.0; original NC-SA terms are retained here.",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "sampling": "Lowest SHA256(seed + NUL + normalized text) ranks within each star rating",
        "per_rating": args.per_rating,
        "sample_count": len(records),
        "sample_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "transformations": [
            "Keep only text, overall_rating and source row with local evaluation metadata",
            "Trim outer whitespace; preserve spelling, punctuation and internal whitespace",
            "Keep texts with 20-2000 characters; exclude obvious email, URL or long digit runs",
            "Deduplicate casefolded text with collapsed whitespace; keep first eligible occurrence",
            "Balance rating quotas; do not infer aspect annotations from overall rating",
        ],
        "usage": "Local non-commercial evaluation and language inspection; no RAG ingestion",
        "statistics": stats,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "LICENSE.txt").write_text(
        "B2W-Reviews01 - B2W Digital\n"
        "Original dataset and this selected sample: CC BY-NC-SA 4.0.\n"
        f"License: {LICENSE_URL}\n"
        f"Source: {SOURCE_URL}\n"
        "Changes: field selection, filtering, deduplication and stratified sampling.\n"
        "No endorsement by the source authors is implied.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "sample_count": len(records),
                "sample_sha256": manifest["sample_sha256"],
                **stats,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
