import importlib.util
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_prepare = load_script("prepare_gold_sample")
_validate = load_script("validate_gold_set")


class HiddenLabels(dict):
    def __getitem__(self, key):
        if key == "aspects":
            raise AssertionError("Selection must not consult generated labels")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key == "aspects":
            raise AssertionError("Selection must not consult generated labels")
        return super().get(key, default)


def make_population():
    return [
        HiddenLabels(
            {
                "id": f"r{restaurant}-{rating}-{index}",
                "restaurant_id": f"rest_{restaurant:03d}",
                "rating": rating,
                "text": f"Review {restaurant}-{rating}-{index}. Gostei do sabor mas atrasou.",
                "aspects": object(),
            }
        )
        for restaurant in range(1, 9)
        for rating in range(1, 6)
        for index in range(5)
    ]


def test_stratified_selection_never_consults_labels_and_respects_prior_exposure():
    rows = make_population()
    exposure = {
        "ids": [rows[0]["id"]],
        "normalized_text_sha256": [_prepare.text_hash(rows[1]["text"])],
    }
    selected, _ = _prepare.select_reviews(rows, exposure, seed=1729)
    assert len(selected) == 100
    assert selected == _prepare.select_reviews(rows, exposure, seed=1729)[0]
    assert len({_prepare.text_hash(row["text"]) for row in selected}) == 100
    assert rows[0]["id"] not in {row["id"] for row in selected}
    assert rows[1]["id"] not in {row["id"] for row in selected}
    assert set(Counter(row["restaurant_id"] for row in selected).values()) == {12, 13}
    assert {row["rating"] for row in selected} == {1, 2, 3, 4, 5}
    assert all("aspects" not in row for row in selected)


def test_insufficient_stratum_fails_instead_of_duplicating():
    with pytest.raises(ValueError, match="Insufficient"):
        _prepare.select_reviews(
            make_population()[4:], {"ids": [], "normalized_text_sha256": []}, 1729
        )


def test_frozen_annotation_artifacts_are_consistent_and_identified_as_ai():
    summary = _validate.validate(
        ROOT / "data/gold", ROOT / "data/raw/reviews.jsonl", ROOT / "docs/annotation-guide.md"
    )
    assert summary["valid_annotations"] == 100
    assert summary["mixed_polarity_reviews"] >= 30
    assert len(summary["restaurants"]) == 8
    assert summary["human_reviewed_count"] == 0
    assert summary["status"] == "ai_annotated_pending_independent_human_review"
    assert summary["reserved_from_training_ids"] >= 100


def test_changed_annotations_are_detected_by_checksum(tmp_path):
    target = tmp_path / "gold"
    shutil.copytree(ROOT / "data/gold", target)
    path = target / "aspects_100.ai.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["aspects"] = {}
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="Annotation checksum mismatch"):
        _validate.validate(
            target, ROOT / "data/raw/reviews.jsonl", ROOT / "docs/annotation-guide.md"
        )


def test_annotated_edge_cases_follow_the_written_guide_without_inferred_aspects():
    path = ROOT / "data/gold/aspects_100.ai.jsonl"
    annotations = {
        row["id"]: row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    }
    assert annotations["rev_001895"]["aspects"] == {}  # Generic approval, no specific aspect.
    assert annotations["rev_001916"]["aspects"] == {"temperatura": "neg"}  # Cold is not delay.
    assert "tempo_entrega" not in annotations["rev_001685"]["aspects"]  # Neutral duration.
    assert annotations["rev_002257"]["aspects"]["atendimento"] == "neg"  # Slow chat response.
    assert "tempo_entrega" not in annotations["rev_002257"]["aspects"]
