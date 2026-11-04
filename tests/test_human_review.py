import copy
import json
from pathlib import Path

import pytest

from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.evaluation.rescore import rescore_review

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "data/eval"
REVIEWED = PARENT / "human-v2"


def read_report(name, directory=ROOT / "reports"):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def test_review_changes_only_query_judgment_without_relabeling_absa_gold():
    previous, old_corpus, old_manifest = load_eval_set(PARENT)
    questions, corpus, manifest = load_eval_set(REVIEWED)
    assert corpus == old_corpus
    assert manifest["parent_snapshot_sha256_lf"] == old_manifest["file_sha256_lf"]
    assert [
        q.id for q, old in zip(questions, previous, strict=True) if q.relevantes != old.relevantes
    ] == ["q22"]
    q22 = next(q for q in questions if q.id == "q22")
    assert "rev_002800" in q22.relevantes
    assert "sabor" not in next(r for r in corpus if r.id == "rev_002800").aspects
    assert manifest["assisted_human_question_review_count"] == 15
    assert manifest["independent_human_reviewed_count"] == 0


def test_review_provenance_preserves_pool_scope_disagreement_and_assistance():
    rows = [
        json.loads(line)
        for line in (REVIEWED / "human_review.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 15
    assert sum(len(row["presented_reviews"]) for row in rows) == 56
    assert all(
        not row["complete_corpus_review"] and not row["independent_blind_review"] for row in rows
    )
    by_id = {row["question_id"]: row for row in rows}
    assert by_id["q09"]["answer_and_assistance_history"]["correction"]["user_confirmation"]
    assert (
        by_id["q22"]["answer_and_assistance_history"]["disagreement"]["review_id"] == "rev_002800"
    )
    for row in rows:
        assert set(row["human_selected_ids"]) | set(row["human_rejected_ids"]) == {
            review["id"] for review in row["presented_reviews"]
        }


def test_rescoring_preserves_scores_and_reproduces_reviewed_reports():
    names = ("retrieval-baseline.json", "retrieval-comparison.json", "min-score-protocol.json")
    inputs = [read_report(name) for name in names]
    untouched = copy.deepcopy(inputs)
    results = rescore_review(PARENT, REVIEWED, *inputs)
    assert inputs == untouched
    for name, result in results.items():
        assert result == read_report(name, ROOT / "reports/human-v2")
    for mode in ("sem_filtro", "com_filtro"):
        old = inputs[0]["modes"][mode]["questions"]
        new = results[names[0]]["modes"][mode]["questions"]
        assert [(r["id"], r["returned_ids"], r["scores"]) for r in old] == [
            (r["id"], r["returned_ids"], r["scores"]) for r in new
        ]
    old_precision = inputs[1]["methods"]["semantic"]["com_filtro"]["ranking"]["8"]["precision_at_k"]
    new_precision = results[names[1]]["methods"]["semantic"]["com_filtro"]["ranking"]["8"][
        "precision_at_k"
    ]
    assert new_precision - old_precision == pytest.approx(1 / (24 * 8))
    assert results["min-score-calibration.json"]["selected_threshold"] == 0.287


def test_rescore_refuses_scores_from_a_different_snapshot():
    inputs = [
        read_report(name)
        for name in (
            "retrieval-baseline.json",
            "retrieval-comparison.json",
            "min-score-protocol.json",
        )
    ]
    inputs[1]["snapshot_sha256_lf"] = {}
    with pytest.raises(ValueError, match="snapshot"):
        rescore_review(PARENT, REVIEWED, *inputs)
