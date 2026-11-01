"""Reproducible, disjoint review partitions with gold leakage checks."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from partner_copilot.schemas import Review


def text_key(text: str) -> str:
    return hashlib.sha256(" ".join(text.casefold().split()).encode("utf-8")).hexdigest()


def file_key(path: Path) -> str:
    """Ignore platform newline conversion, preserving all other content."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    )


def build_splits(
    source: Path, gold_dir: Path, output: Path, *, train_fraction: float = 0.7, seed: int = 2718
) -> dict:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between zero and one")
    source_rows = read_jsonl(source)
    rows = {row["id"]: row for row in source_rows}
    if len(rows) != len(source_rows):
        raise ValueError("Source review IDs must be unique")
    for row in source_rows:
        Review.model_validate(row)
    selection = json.loads((gold_dir / "sample_manifest.json").read_text(encoding="utf-8"))
    annotations_meta = json.loads(
        (gold_dir / "annotation_manifest.json").read_text(encoding="utf-8")
    )
    labels_path = gold_dir / "aspects_100.ai.jsonl"
    blind_path = gold_dir / "reviews_100.blind.jsonl"
    if selection["source_sha256"] != file_key(source):
        raise ValueError("Source does not match the frozen gold snapshot")
    if hashlib.sha256(blind_path.read_bytes()).hexdigest() != selection["blind_sample_sha256"]:
        raise ValueError("Frozen blind sample checksum mismatch")
    if (
        hashlib.sha256(labels_path.read_bytes()).hexdigest()
        != annotations_meta["annotations_sha256"]
    ):
        raise ValueError("Frozen annotations checksum mismatch")
    blind = read_jsonl(blind_path)
    labels = {row["id"]: row for row in read_jsonl(labels_path)}
    gold_ids = {row["id"] for row in blind}
    if len(gold_ids) != 100 or gold_ids != set(labels):
        raise ValueError("Expected 100 unique gold IDs with matching annotations")
    if any(row["id"] not in rows or row["text"] != rows[row["id"]]["text"] for row in blind):
        raise ValueError("Gold review text does not match the source")
    gold_texts = {text_key(row["text"]) for row in blind}
    reserved = {row["id"] for row in source_rows if text_key(row["text"]) in gold_texts}
    if reserved != set(selection["reserved_from_training_ids"]):
        raise ValueError("Gold reservation does not include every exact normalized duplicate")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in source_rows:
        if row["id"] not in reserved:
            groups[text_key(row["text"])].append(row)
    group_keys = sorted(
        groups, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()
    )
    train_group_count = round(train_fraction * len(group_keys))
    train_keys = set(group_keys[:train_group_count])
    train = sorted((row for key in train_keys for row in groups[key]), key=lambda row: row["id"])
    rag = sorted(
        (row for key in group_keys if key not in train_keys for row in groups[key]),
        key=lambda row: row["id"],
    )
    gold = [
        {
            "id": row["id"],
            "text": row["text"],
            **labels[row["id"]],
            "annotation_status": annotations_meta["status"],
        }
        for row in blind
    ]
    quarantine = [
        {"id": row["id"], "text": row["text"], "reason": "normalized_duplicate_of_gold"}
        for row in source_rows
        if row["id"] in reserved - gold_ids
    ]
    partitions = {"gold": gold, "train_pool": train, "rag": rag, "quarantine": quarantine}
    output.mkdir(parents=True, exist_ok=True)
    for name, records in partitions.items():
        write_jsonl(output / f"{name}.jsonl", records)
    manifest = {
        "seed": seed,
        "train_fraction_of_non_gold_text_groups": train_fraction,
        "source_sha256_lf": file_key(source),
        "gold_status": annotations_meta["status"],
        "source_count": len(source_rows),
        "gold_reserved_ids": sorted(reserved),
        "gold_reserved_text_hashes": sorted(gold_texts),
        "counts": {name: len(records) for name, records in partitions.items()},
        "ids": {name: sorted(row["id"] for row in records) for name, records in partitions.items()},
        "file_sha256_lf": {
            f"{name}.jsonl": file_key(output / f"{name}.jsonl") for name in partitions
        },
        "distribution": {
            name: {
                "restaurants": dict(
                    sorted(Counter(rows[row["id"]]["restaurant_id"] for row in records).items())
                ),
                "ratings": dict(
                    sorted(Counter(rows[row["id"]]["rating"] for row in records).items())
                ),
            }
            for name, records in partitions.items()
        },
        "training_labels": "Synthetic generator labels; not independently annotated gold",
        "leakage_scope": "Disjoint IDs and normalized texts; template families can overlap",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validate_splits(output)
    return manifest


def validate_splits(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    all_ids: set[str] = set()
    all_texts: set[str] = set()
    for name in ("gold", "train_pool", "rag", "quarantine"):
        path = folder / f"{name}.jsonl"
        if file_key(path) != manifest["file_sha256_lf"][path.name]:
            raise ValueError(f"Split checksum mismatch: {name}")
        rows = read_jsonl(path)
        ids = [row["id"] for row in rows]
        if len(ids) != len(set(ids)) or sorted(ids) != manifest["ids"][name]:
            raise ValueError(f"Split IDs mismatch: {name}")
        if len(rows) != manifest["counts"][name] or all_ids & set(ids):
            raise ValueError(f"Duplicate or overlapping IDs: {name}")
        hashes = {text_key(row["text"]) for row in rows}
        if name in {"train_pool", "rag"}:
            if hashes & set(manifest["gold_reserved_text_hashes"]):
                raise ValueError(f"Gold text leakage: {name}")
            if set(ids) & set(manifest["gold_reserved_ids"]):
                raise ValueError(f"Gold ID leakage: {name}")
            if hashes & all_texts:
                raise ValueError(f"Text leakage across partitions: {name}")
            for row in rows:
                Review.model_validate(row)
        all_ids.update(ids)
        all_texts.update(hashes)
    gold_rows = read_jsonl(folder / "gold.jsonl")
    quarantine_rows = read_jsonl(folder / "quarantine.jsonl")
    gold_ids = {row["id"] for row in gold_rows}
    quarantine_ids = {row["id"] for row in quarantine_rows}
    gold_hashes = {text_key(row["text"]) for row in gold_rows}
    if gold_ids | quarantine_ids != set(manifest["gold_reserved_ids"]):
        raise ValueError("Gold and quarantine IDs must match the evaluation reservation")
    if gold_hashes != set(manifest["gold_reserved_text_hashes"]) or any(
        text_key(row["text"]) not in gold_hashes for row in quarantine_rows
    ):
        raise ValueError("Quarantine must contain only normalized duplicates of gold")
    if len(all_ids) != manifest["source_count"]:
        raise ValueError("Splits do not cover the source corpus")
    return manifest


def load_absa_train_pool(folder: Path = Path("data/splits")) -> list[Review]:
    """Validate every partition before returning any training example."""
    validate_splits(folder)
    return [Review.model_validate(row) for row in read_jsonl(folder / "train_pool.jsonl")]


def validate_rag_input(path: Path, folder: Path = Path("data/splits")) -> None:
    """Reject the full corpus, training pool or gold before loading embeddings."""
    manifest = validate_splits(folder)
    if file_key(path) != manifest["file_sha256_lf"]["rag.jsonl"]:
        raise ValueError("RAG input must match the registered rag split, not the full corpus")


def validate_rag_collection_ids(ids: list[str], folder: Path = Path("data/splits")) -> None:
    """Do not mix a previously indexed full corpus into the new RAG-only collection."""
    manifest = validate_splits(folder)
    if set(ids) - set(manifest["ids"]["rag"]):
        raise ValueError(
            "Collection contains IDs outside the RAG split. Choose a new CHROMA_COLLECTION; "
            "existing documents were not deleted."
        )
