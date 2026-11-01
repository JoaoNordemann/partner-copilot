import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from partner_copilot.ingestion.indexer import ingest_reviews

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_external_reviews.py"
spec = importlib.util.spec_from_file_location("prepare_external", SCRIPT)
assert spec is not None and spec.loader is not None
_external = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_external)


@pytest.fixture
def source_csv(tmp_path):
    path = tmp_path / "reviews.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["review_text", "overall_rating", "reviewer_id"])
        writer.writeheader()
        for rating in range(1, 6):
            for index in range(10):
                writer.writerow(
                    {
                        "review_text": f"Minha opinião {rating}-{index}: entrega e produto.",
                        "overall_rating": rating,
                        "reviewer_id": "not-exported",
                    }
                )
        writer.writerow(
            {"review_text": "MINHA OPINIÃO 1-0: entrega e produto.", "overall_rating": 1}
        )
        writer.writerow(
            {
                "review_text": "Pode falar comigo pelo teste@example.com por favor.",
                "overall_rating": 1,
            }
        )
        writer.writerow({"review_text": "bom", "overall_rating": 1})
    return path


def test_sampling_is_balanced_unique_and_reproducible(source_csv):
    rows, stats = _external.select_sample(source_csv, per_rating=2, seed=42)
    assert rows == _external.select_sample(source_csv, per_rating=2, seed=42)[0]
    assert rows != _external.select_sample(source_csv, per_rating=2, seed=99)[0]
    assert Counter(row["overall_rating"] for row in rows) == dict.fromkeys(range(1, 6), 2)
    assert len({" ".join(row["text"].casefold().split()) for row in rows}) == 10
    assert stats["excluded_duplicate_text"] == 1
    assert stats["excluded_obvious_contact"] == 1
    assert stats["excluded_length"] == 1
    assert all("reviewer_id" not in row and "aspects" not in row for row in rows)
    assert all(row["annotation_status"] == "unannotated" for row in rows)


def test_insufficient_eligible_rows_fails_instead_of_duplicating(source_csv):
    with pytest.raises(ValueError, match="Not enough"):
        _external.select_sample(source_csv, per_rating=11)


def test_invalid_quota_and_deadline_are_enforced(source_csv):
    with pytest.raises(ValueError, match="positive"):
        _external.select_sample(source_csv, per_rating=0)
    with pytest.raises(TimeoutError, match="timebox"):
        _external.select_sample(source_csv, per_rating=2, deadline=0)


def test_external_records_do_not_enter_the_restaurant_index(source_csv, tmp_path):
    class RefusingStore:
        def upsert(self, reviews):
            pytest.fail("External reviews must not be sent to the RAG store")

    rows, _ = _external.select_sample(source_csv, per_rating=2)
    sample = tmp_path / "external.jsonl"
    sample.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid review"):
        ingest_reviews(sample, RefusingStore())
