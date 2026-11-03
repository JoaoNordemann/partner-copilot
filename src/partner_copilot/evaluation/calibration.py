"""Select a score threshold on a prespecified calibration partition only."""

import math
from fractions import Fraction

import numpy as np


def counts(rows: list[dict], threshold: float) -> dict:
    positive = [r for r in rows if not r["deve_abster"]]
    negative = [r for r in rows if r["deve_abster"]]

    def accepted(row: dict) -> bool:
        return row["best_score"] is not None and row["best_score"] >= threshold

    tp = sum(accepted(r) for r in positive)
    fp = sum(accepted(r) for r in negative)
    tn = len(negative) - fp
    return {
        "answerable": len(positive),
        "unanswerable": len(negative),
        "valid_questions_accepted": tp,
        "valid_questions_rejected": len(positive) - tp,
        "unanswerable_rejected": tn,
        "unanswerable_accepted": fp,
        "accepted_with_relevant_evidence": sum(
            any(
                score >= threshold and identifier in r["relevant_ids"]
                for identifier, score in zip(r["ranked_ids"], r["scores"], strict=True)
            )
            for r in positive
        ),
        "balanced_accuracy": float((Fraction(tp, len(positive)) + Fraction(tn, len(negative))) / 2)
        if positive and negative
        else None,
        "semantic_negatives_accepted": sum(
            accepted(r) for r in negative if r["negative_kind"] == "semantic"
        ),
        "semantic_negatives": sum(r["negative_kind"] == "semantic" for r in negative),
    }


def choose_threshold(calibration_rows: list[dict]) -> tuple[float, list[dict]]:
    if not any(r["deve_abster"] for r in calibration_rows) or not any(
        not r["deve_abster"] for r in calibration_rows
    ):
        raise ValueError("Calibration needs answerable and unanswerable questions")
    best_key = None
    selected = None
    curve = []
    last_signature = None
    for tick in range(1001):
        threshold = tick / 1000
        metric = counts(calibration_rows, threshold)
        objective = (
            Fraction(metric["valid_questions_accepted"], metric["answerable"])
            + Fraction(metric["unanswerable_rejected"], metric["unanswerable"])
        ) / 2
        key = (objective, -metric["unanswerable_accepted"], -tick)
        if best_key is None or key > best_key:
            best_key, selected = key, threshold
        signature = tuple(metric.items())
        if signature != last_signature:
            curve.append({"threshold": threshold, **metric})
            last_signature = signature
    return selected, curve


def distribution(rows: list[dict]) -> dict:
    result = {}
    for negative, group in [(False, "answerable"), (True, "unanswerable")]:
        subset = [r for r in rows if r["deve_abster"] == negative]
        values = [r["best_score"] for r in subset if r["best_score"] is not None]
        result[group] = {
            "count": len(subset),
            "no_candidate": len(subset) - len(values),
            "quantiles": dict(
                zip(
                    ["min", "q1", "median", "q3", "max"],
                    map(float, np.quantile(values, [0, 0.25, 0.5, 0.75, 1])),
                    strict=True,
                )
            )
            if values
            else None,
        }
    positive = result["answerable"]["quantiles"]
    negative = result["unanswerable"]["quantiles"]
    lower = max(positive["min"], negative["min"]) if positive and negative else None
    upper = min(positive["max"], negative["max"]) if positive and negative else None
    result["range_overlap"] = [lower, upper] if lower is not None and lower <= upper else None
    return result


def calibrate(questions: list, comparison: dict, protocol: dict) -> dict:
    calibration_ids, evaluation_ids = map(
        set, (protocol["calibration_ids"], protocol["evaluation_ids"])
    )
    if (
        len(calibration_ids) != 20
        or len(evaluation_ids) != 10
        or calibration_ids & evaluation_ids
        or calibration_ids | evaluation_ids != {q.id for q in questions}
    ):
        raise ValueError("Invalid 20/10 split")
    if comparison["snapshot_sha256_lf"] != protocol["snapshot_sha256_lf"]:
        raise ValueError("Protocol and scores refer to different snapshots")
    rows = []
    for mode in ("com_filtro", "sem_filtro"):
        ranked = {r["id"]: r for r in comparison["methods"]["semantic"][mode]["questions"]}
        for q in questions:
            record = ranked[q.id]
            scores = record["scores"]
            if (
                len(scores) != len(record["ranked_ids"])
                or any(not math.isfinite(s) for s in scores)
                or scores != sorted(scores, reverse=True)
            ):
                raise ValueError("Invalid or unsorted ranking scores")
            rows.append(
                {
                    "id": q.id,
                    "pergunta": q.pergunta,
                    "mode": mode,
                    "split": "calibration" if q.id in calibration_ids else "evaluation",
                    "deve_abster": q.deve_abster,
                    "negative_kind": (
                        "structural" if q.filtros.item or q.filtros.start_date else "semantic"
                    )
                    if q.deve_abster
                    else None,
                    "best_score": scores[0] if scores else None,
                    "best_id": record["ranked_ids"][0] if scores else None,
                    "top1_relevant": record["ranked_ids"][0] in q.relevantes if scores else False,
                    "ranked_ids": record["ranked_ids"],
                    "scores": scores,
                    "relevant_ids": q.relevantes,
                }
            )
    calibration = [r for r in rows if r["split"] == "calibration" and r["mode"] == "com_filtro"]
    selected, curve = choose_threshold(calibration)
    modes = {}
    for mode in ("com_filtro", "sem_filtro"):
        modes[mode] = {}
        for split in ("calibration", "evaluation"):
            subset = [r for r in rows if r["split"] == split and r["mode"] == mode]
            modes[mode][split] = {
                "distributions": distribution(subset),
                "previous": counts(subset, protocol["previous_threshold"]),
                "selected": counts(subset, selected),
            }
    return {
        "selected_threshold": selected,
        "previous_threshold": protocol["previous_threshold"],
        "k": 8,
        "objective": "balanced_accuracy_on_filtered_calibration_only",
        "candidate_grid_count": 1001,
        "calibration_curve_change_points": curve,
        "snapshot_sha256_lf": protocol["snapshot_sha256_lf"],
        "model": comparison["model"],
        "model_revision": comparison["model_revision"],
        "historically_exposed_evaluation_set": True,
        "promoted_global_default": False,
        "modes": modes,
        "per_question": rows,
    }
