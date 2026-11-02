#!/usr/bin/env python
"""Validate frozen annotation artifacts without consulting synthetic aspect labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Aspect = Literal["sabor", "tempo_entrega", "temperatura", "embalagem", "preco", "atendimento"]


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    aspects: dict[Aspect, Literal["pos", "neg"]]
    notas: str | None = None


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(folder: Path, source: Path, guide: Path) -> dict:
    selection = json.loads((folder / "sample_manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((folder / "annotation_manifest.json").read_text(encoding="utf-8"))
    blind_path = folder / "reviews_100.blind.jsonl"
    labels_path = folder / "aspects_100.ai.jsonl"
    blind = [json.loads(line) for line in blind_path.read_text(encoding="utf-8").splitlines()]
    annotations = [
        Annotation.model_validate_json(line)
        for line in labels_path.read_text(encoding="utf-8").splitlines()
    ]
    if len(annotations) != 100 or len(blind) != 100:
        raise ValueError("Expected exactly 100 blind records and annotations")
    ids = [row.id for row in annotations]
    if len(set(ids)) != 100 or ids != [row["id"] for row in blind]:
        raise ValueError("Annotation IDs must be unique and match the frozen blind order")
    if any(set(row) != {"id", "text"} for row in blind):
        raise ValueError("Blind input must expose only id and text")
    expected = {
        "source_sha256": hashlib.sha256(
            source.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest(),
        "blind_sample_sha256": checksum(blind_path),
        "guide_sha256": checksum(guide),
    }
    if any(selection[key] != value for key, value in expected.items()):
        raise ValueError("Source, blind sample or guide checksum mismatch")
    for key in ("blind_sample_sha256", "guide_sha256"):
        if provenance[key] != expected[key]:
            raise ValueError("Annotation provenance does not match the frozen inputs")
    if provenance["annotations_sha256"] != checksum(labels_path):
        raise ValueError("Annotation checksum mismatch: record revisions separately")
    if provenance["generated_labels_consulted"] or selection["selection_uses_generated_aspects"]:
        raise ValueError("The recorded protocol is not blind to generated labels")
    # Load only text and selection metadata; never read or compare source aspects.
    source_rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    by_id = {row["id"]: row for row in source_rows}
    for row in blind:
        if row["id"] not in by_id or row["text"] != by_id[row["id"]]["text"]:
            raise ValueError("Blind review differs from the source snapshot")

    def normalized_text_hash(text: str) -> str:
        normalized = " ".join(text.casefold().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    blind_hashes = {normalized_text_hash(row["text"]) for row in blind}
    if len(blind_hashes) != 100:
        raise ValueError("Blind sample contains normalized text duplicates")
    exposure = json.loads((folder / "prior_exposure.json").read_text(encoding="utf-8"))
    if set(ids) & set(exposure["ids"]) or blind_hashes & set(exposure["normalized_text_sha256"]):
        raise ValueError("Blind sample contains previously exposed IDs or texts")
    reserved_ids = sorted(
        row["id"] for row in source_rows if normalized_text_hash(row["text"]) in blind_hashes
    )
    if reserved_ids != selection["reserved_from_training_ids"]:
        raise ValueError("Training reservation must include all normalized text duplicates")
    restaurants = Counter(by_id[review_id]["restaurant_id"] for review_id in ids)
    ratings = Counter(by_id[review_id]["rating"] for review_id in ids)
    if dict(restaurants) != selection["restaurant_counts"]:
        raise ValueError("Restaurant stratification does not match the manifest")
    if {str(key): value for key, value in ratings.items()} != selection["rating_counts"]:
        raise ValueError("Rating stratification does not match the manifest")
    mixed = sum(set(row.aspects.values()) == {"pos", "neg"} for row in annotations)
    notes = sum(bool(row.notas) for row in annotations)
    if mixed != provenance["mixed_polarity_reviews"] or notes != provenance["reviews_with_notes"]:
        raise ValueError("Annotation summary mismatch")
    return {
        "valid_annotations": len(annotations),
        "restaurants": dict(sorted(restaurants.items())),
        "ratings": dict(sorted(ratings.items())),
        "mixed_polarity_reviews": mixed,
        "reviews_with_notes": notes,
        "human_reviewed_count": provenance["human_reviewed_count"],
        "status": provenance["status"],
        "reserved_from_training_ids": len(selection["reserved_from_training_ids"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--guide", type=Path)
    args = parser.parse_args()
    from partner_copilot.config import get_settings

    settings = get_settings()
    args.folder = args.folder if args.folder is not None else settings.data_gold_dir
    args.source = args.source if args.source is not None else settings.raw_reviews_path
    args.guide = args.guide if args.guide is not None else settings.annotation_guide_path
    print(json.dumps(validate(args.folder, args.source, args.guide), ensure_ascii=True))


if __name__ == "__main__":
    main()
