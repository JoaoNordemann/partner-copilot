import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from partner_copilot.config import Settings
from partner_copilot.data_splits import (
    build_splits,
    file_key,
    load_absa_train_pool,
    read_jsonl,
    text_key,
    validate_rag_collection_ids,
    validate_rag_input,
    validate_splits,
    write_jsonl,
)

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data/splits"


def test_partitions_cover_source_and_have_disjoint_ids_and_normalized_texts():
    manifest = validate_splits(SPLITS)
    assert sum(manifest["counts"].values()) == 3000
    assert manifest["counts"]["gold"] == 100
    assert manifest["counts"]["quarantine"] == 1
    seen_ids, seen_texts = set(), set()
    for name in ("gold", "train_pool", "rag"):
        rows = read_jsonl(SPLITS / f"{name}.jsonl")
        ids = {row["id"] for row in rows}
        hashes = {text_key(row["text"]) for row in rows}
        assert not ids & seen_ids
        assert not hashes & seen_texts
        seen_ids |= ids
        seen_texts |= hashes
        assert len(manifest["distribution"][name]["restaurants"]) == 8
        assert len(manifest["distribution"][name]["ratings"]) == 5
    training = load_absa_train_pool(SPLITS)
    assert not {row.id for row in training} & set(manifest["gold_reserved_ids"])
    assert Settings().data_splits_dir == Path("data/splits")


def test_split_generation_is_reproducible(tmp_path):
    target = tmp_path / "splits"
    build_splits(ROOT / "data/raw/reviews.jsonl", ROOT / "data/gold", target)
    for name in ("gold", "train_pool", "rag", "quarantine"):
        assert (target / f"{name}.jsonl").read_bytes() == (SPLITS / f"{name}.jsonl").read_bytes()


def test_training_loader_rejects_gold_text_even_with_a_different_id(tmp_path):
    target = tmp_path / "splits"
    shutil.copytree(SPLITS, target)
    train_path = target / "train_pool.jsonl"
    training = read_jsonl(train_path)
    training[0]["text"] = read_jsonl(target / "gold.jsonl")[0]["text"]
    write_jsonl(train_path, training)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["file_sha256_lf"]["train_pool.jsonl"] = file_key(train_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Gold text leakage"):
        load_absa_train_pool(target)


def test_rag_preflight_rejects_full_corpus_and_legacy_collections():
    validate_rag_input(SPLITS / "rag.jsonl", SPLITS)
    with pytest.raises(ValueError, match="registered rag split"):
        validate_rag_input(ROOT / "data/raw/reviews.jsonl", SPLITS)
    manifest = validate_splits(SPLITS)
    validate_rag_collection_ids(manifest["ids"]["rag"][:2], SPLITS)
    with pytest.raises(ValueError, match="outside the RAG split"):
        validate_rag_collection_ids(manifest["ids"]["gold"][:1], SPLITS)


def test_ingestion_cli_rejects_full_corpus_before_model_loading():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ingest.py"),
            "--input",
            str(ROOT / "data/raw/reviews.jsonl"),
        ],
        env=os.environ | {"DATA_SPLITS_DIR": str(SPLITS), "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert "registered rag split" in result.stderr


def test_corrupted_split_is_rejected_before_training(tmp_path):
    target = tmp_path / "splits"
    shutil.copytree(SPLITS, target)
    path = target / "rag.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Split checksum mismatch"):
        load_absa_train_pool(target)
