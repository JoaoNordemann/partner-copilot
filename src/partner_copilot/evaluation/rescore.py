"""Recompute judgments-dependent metrics while preserving recorded retrieval rankings."""

from copy import deepcopy
from pathlib import Path

from partner_copilot.evaluation.baselines import random_baseline, score_rankings
from partner_copilot.evaluation.calibration import calibrate
from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.evaluation.retrieval import summarize


def rescore_review(
    original_folder: Path,
    reviewed_folder: Path,
    operational: dict,
    comparison: dict,
    protocol: dict,
) -> dict:
    previous, original_corpus, parent = load_eval_set(original_folder)
    questions, corpus, manifest = load_eval_set(reviewed_folder)
    if manifest.get("parent_snapshot_sha256_lf") != parent["file_sha256_lf"]:
        raise ValueError("Reviewed snapshot does not descend from the original snapshot")
    for source in (operational, comparison, protocol):
        if source["snapshot_sha256_lf"] != parent["file_sha256_lf"]:
            raise ValueError("Source scores and original snapshot differ")
    if original_corpus != corpus:
        raise ValueError("Rank reuse requires exactly the same corpus")
    previous_by_id = {q.id: q for q in previous}
    for question in questions:
        old = previous_by_id[question.id]
        if (question.pergunta, question.filtros, question.tipo, question.deve_abster) != (
            old.pergunta,
            old.filtros,
            old.tipo,
            old.deve_abster,
        ):
            raise ValueError("Rank reuse requires unchanged questions, filters and answerability")
    by_id = {q.id: q for q in questions}
    changed_ids = sorted(q.id for q in questions if q.relevantes != previous_by_id[q.id].relevantes)
    operational, comparison, protocol = map(deepcopy, (operational, comparison, protocol))
    for mode in ("sem_filtro", "com_filtro"):
        rows = operational["modes"][mode]["questions"]
        for row in rows:
            relevant = set(by_id[row["id"]].relevantes)
            row["relevant_ids"] = by_id[row["id"]].relevantes
            row["recall_at_k"] = (
                len(set(row["returned_ids"]) & relevant) / len(relevant) if relevant else None
            )
            row["reciprocal_rank"] = (
                next(
                    (
                        1 / rank
                        for rank, identifier in enumerate(row["returned_ids"], 1)
                        if identifier in relevant
                    ),
                    0.0,
                )
                if relevant
                else None
            )
        operational["modes"][mode]["summary"] = summarize(rows)
        operational["modes"][mode]["per_type"] = {
            kind: summarize([r for r in rows if r["tipo"] == kind])
            for kind in sorted({r["tipo"] for r in rows})
        }
        for method in ("semantic", "keyword"):
            entry = comparison["methods"][method][mode]
            for section, field in (("ranking", "ranked_ids"), ("operational", "operational_ids")):
                entry[section] = score_rankings(
                    questions, {r["id"]: r[field] for r in entry["questions"]}
                )
        eligible = {
            q.id: [
                i
                for i, review in enumerate(corpus)
                if mode == "sem_filtro" or q.filtros.matches(review)
            ]
            for q in questions
        }
        comparison["methods"]["random"][mode] = random_baseline(questions, corpus, eligible)
    provenance = {
        "method": "Reuse frozen rankings and scores; recompute relevance-dependent metrics",
        "parent_snapshot_sha256_lf": parent["file_sha256_lf"],
        "changed_question_ids": changed_ids,
        "assisted_human_reviewed_questions": manifest["assisted_human_question_review_count"],
        "independent_blind_human_review": False,
        "embeddings_recomputed": False,
    }
    for output in (operational, comparison, protocol):
        output["snapshot_sha256_lf"] = manifest["file_sha256_lf"]
        output["rescore_provenance"] = provenance
    for output in (operational, comparison):
        output["annotation_status"] = manifest["annotation_status"]
    calibration = calibrate(questions, comparison, protocol)
    calibration["rescore_provenance"] = provenance
    return {
        "retrieval-baseline.json": operational,
        "retrieval-comparison.json": comparison,
        "min-score-protocol.json": protocol,
        "min-score-calibration.json": calibration,
    }
