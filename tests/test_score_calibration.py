import copy
import json
from pathlib import Path

import pytest

from partner_copilot.evaluation.calibration import calibrate, choose_threshold, counts, distribution
from partner_copilot.evaluation.dataset import load_eval_set

ROOT = Path(__file__).resolve().parents[1]


def row(score, negative=False):
    return {
        "best_score": score,
        "deve_abster": negative,
        "ranked_ids": ["doc"] if score is not None else [],
        "scores": [score] if score is not None else [],
        "relevant_ids": [] if negative else ["doc"],
        "negative_kind": "semantic" if negative else None,
    }


def test_threshold_objective_and_ties_prefer_fewer_false_acceptances():
    selected, _ = choose_threshold([row(0.8), row(0.3), row(0.4, True), row(None, True)])
    assert selected == 0.401
    metric = counts([row(0.401), row(0.401, True), row(None, True)], 0.401)
    assert metric["valid_questions_accepted"] == 1
    assert metric["unanswerable_accepted"] == 1
    assert metric["unanswerable_rejected"] == 1


def test_missing_scores_are_not_converted_to_zero_and_overlap_is_explicit():
    result = distribution([row(0.2), row(0.8), row(0.4, True), row(None, True)])
    assert result["unanswerable"]["no_candidate"] == 1
    assert result["unanswerable"]["quantiles"]["min"] == 0.4
    assert result["range_overlap"] == [0.4, 0.4]
    with pytest.raises(ValueError):
        choose_threshold([row(0.4)])


def test_acceptance_does_not_mean_evidence_survives_threshold():
    record = row(0.8)
    record.update(ranked_ids=["wrong", "right"], scores=[0.8, 0.2], relevant_ids=["right"])
    result = counts([record, row(0.5, True)], 0.3)
    assert result["valid_questions_accepted"] == 1
    assert result["accepted_with_relevant_evidence"] == 0


def test_evaluation_scores_cannot_change_selected_threshold():
    questions, _, _ = load_eval_set(ROOT / "data/eval")
    protocol = json.loads((ROOT / "reports/min-score-protocol.json").read_text(encoding="utf-8"))
    comparison = json.loads(
        (ROOT / "reports/retrieval-comparison.json").read_text(encoding="utf-8")
    )
    first = calibrate(questions, comparison, protocol)
    modified = copy.deepcopy(comparison)
    for mode in ("com_filtro", "sem_filtro"):
        for record in modified["methods"]["semantic"][mode]["questions"]:
            if record["id"] in protocol["evaluation_ids"]:
                record["scores"] = [1.0] * len(record["scores"])
    second = calibrate(questions, modified, protocol)
    assert first["selected_threshold"] == second["selected_threshold"]
    assert first["calibration_curve_change_points"] == second["calibration_curve_change_points"]
    saved = json.loads((ROOT / "reports/min-score-calibration.json").read_text(encoding="utf-8"))
    assert first == saved
    assert len(first["per_question"]) == 60
    invalid = copy.deepcopy(protocol)
    invalid["evaluation_ids"][0] = invalid["calibration_ids"][0]
    with pytest.raises(ValueError, match="split"):
        calibrate(questions, comparison, invalid)
