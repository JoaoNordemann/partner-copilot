"""Paired CPU retrieval ablations, reusing the frozen metric definitions."""

import random
from itertools import combinations, pairwise
from statistics import mean, pstdev

from partner_copilot.evaluation.baselines import SEEDS, aggregate, question_metrics, tokens
from partner_copilot.evaluation.dataset import EvalQuestion
from partner_copilot.schemas import Review

KS = (1, 3, 5, 8, 12)
METRICS = ("hit_at_k", "recall_capped_at_k", "recall_classic_at_k", "mrr_at_k", "precision_at_k")
MODES = ("sem_filtro", "restaurante")


def eligible_reviews(question: EvalQuestion, corpus: list[Review], mode: str) -> list[Review]:
    """Only restaurant is an experimental filter; never item, date or labels."""
    if mode not in MODES:
        raise ValueError("Unknown filter mode")
    return [
        r
        for r in corpus
        if mode == "sem_filtro" or r.restaurant_id == question.filtros.restaurant_id
    ]


def measure_question(question: EvalQuestion, identifiers: list[str], k: int) -> dict:
    result = question_metrics(question, identifiers, k)
    result.update(
        id=question.id,
        returned_ids=identifiers[:k],
        retrieved_relevant=len(set(identifiers[:k]) & set(question.relevantes)),
        retrieved_irrelevant=len(set(identifiers[:k]) - set(question.relevantes)),
    )
    return result


def paired(reference: list[dict], variant: list[dict], metric: str) -> dict:
    """Pair every positive question; never silently intersect missing records."""
    if metric not in METRICS:
        raise ValueError("Unknown metric")
    if len({r["id"] for r in reference}) != len(reference) or len(
        {r["id"] for r in variant}
    ) != len(variant):
        raise ValueError("Duplicate question IDs")
    left = {r["id"]: r for r in reference}
    right = {r["id"]: r for r in variant}
    if left.keys() != right.keys():
        raise ValueError("Incomplete paired comparison")
    details = []
    for identifier in sorted(left):
        a, b = left[identifier], right[identifier]
        if a["deve_abster"] != b["deve_abster"]:
            raise ValueError("Different question groups")
        if a["deve_abster"]:
            continue
        delta = b[metric] - a[metric]
        details.append(
            {
                "id": identifier,
                "reference": a[metric],
                "variant": b[metric],
                "delta": delta,
                "outcome": "win" if delta > 1e-12 else "loss" if delta < -1e-12 else "tie",
            }
        )
    return {
        "wins": sum(r["outcome"] == "win" for r in details),
        "ties": sum(r["outcome"] == "tie" for r in details),
        "losses": sum(r["outcome"] == "loss" for r in details),
        "questions": len(details),
        "mean_delta": mean(r["delta"] for r in details) if details else None,
        "per_question": details,
    }


def summarize_rankings(questions: list[EvalQuestion], rankings: dict[str, list[str]]) -> dict:
    if set(rankings) != {q.id for q in questions}:
        raise ValueError("Rankings must cover exactly the evaluation questions")
    result = {}
    for k in KS:
        rows = [measure_question(q, rankings[q.id], k) for q in questions]
        result[str(k)] = {"summary": aggregate(rows), "questions": rows}
    return result


def cheap_methods(questions: list[EvalQuestion], corpus: list[Review]) -> dict:
    """Same tokenization and random seeds as the historical baselines."""
    output = {"keyword": {}, "random": {}}
    terms = {r.id: tokens(r.text) for r in corpus}
    for mode in MODES:
        eligible = {
            q.id: sorted(eligible_reviews(q, corpus, mode), key=lambda r: r.id) for q in questions
        }
        ranked, gated = {}, {}
        for q in questions:
            query_terms = tokens(q.pergunta)
            scores = {r.id: len(query_terms & terms[r.id]) for r in eligible[q.id]}
            ranked[q.id] = sorted(scores, key=lambda identifier: (-scores[identifier], identifier))
            gated[q.id] = [identifier for identifier in ranked[q.id] if scores[identifier] > 0]
        output["keyword"][mode] = {
            "ranking": summarize_rankings(questions, ranked),
            "operational": summarize_rankings(questions, gated),
        }
        runs = []
        example = None
        for seed in SEEDS:
            rankings = {}
            for q in questions:
                identifiers = [r.id for r in eligible[q.id]]
                random.Random(f"{seed}:{q.id}").shuffle(identifiers)
                rankings[q.id] = identifiers
            runs.append(summarize_rankings(questions, rankings))
            if example is None:
                example = {identifier: values[: max(KS)] for identifier, values in rankings.items()}
        averaged = {}
        for k in map(str, KS):
            rows = []
            for qi, q in enumerate(questions):
                samples = [run[k]["questions"][qi] for run in runs]
                row = {
                    "id": q.id,
                    "deve_abster": q.deve_abster,
                    "abstained": samples[0]["abstained"],
                    "returned_ids": None,
                }
                for key in (*METRICS, "retrieved_relevant", "retrieved_irrelevant"):
                    row[key] = (
                        mean(s[key] for s in samples) if samples[0][key] is not None else None
                    )
                rows.append(row)
            averaged[k] = {
                "summary": aggregate(rows),
                "questions": rows,
                "aggregate_std_across_seeds": {
                    key: pstdev(run[k]["summary"][key] for run in runs)
                    if runs[0][k]["summary"][key] is not None
                    else None
                    for key in runs[0][k]["summary"]
                },
            }
        output["random"][mode] = {
            "ranking": averaged,
            "operational": averaged,
            "seed_42_rankings": example,
            "repetitions": len(SEEDS),
        }
    return output


def compare_methods(methods: dict) -> dict:
    result = {"methods": [], "filters": [], "k_increments": []}
    for policy in ("ranking", "operational"):
        for mode in MODES:
            for k in map(str, KS):
                for reference, variant in combinations(methods, 2):
                    for metric in METRICS:
                        result["methods"].append(
                            {
                                "reference": reference,
                                "variant": variant,
                                "policy": policy,
                                "mode": mode,
                                "k": int(k),
                                "metric": metric,
                                **paired(
                                    methods[reference][mode][policy][k]["questions"],
                                    methods[variant][mode][policy][k]["questions"],
                                    metric,
                                ),
                            }
                        )
        for name, modes in methods.items():
            for k in map(str, KS):
                for metric in METRICS:
                    result["filters"].append(
                        {
                            "method": name,
                            "policy": policy,
                            "k": int(k),
                            "metric": metric,
                            "reference": "sem_filtro",
                            "variant": "restaurante",
                            **paired(
                                modes["sem_filtro"][policy][k]["questions"],
                                modes["restaurante"][policy][k]["questions"],
                                metric,
                            ),
                        }
                    )
            for mode in MODES:
                for a, b in pairwise(KS):
                    left = modes[mode][policy][str(a)]["questions"]
                    right = modes[mode][policy][str(b)]["questions"]
                    positives = [
                        (x, y) for x, y in zip(left, right, strict=True) if not x["deve_abster"]
                    ]
                    result["k_increments"].append(
                        {
                            "method": name,
                            "mode": mode,
                            "policy": policy,
                            "from_k": a,
                            "to_k": b,
                            "additional_relevant": sum(
                                y["retrieved_relevant"] - x["retrieved_relevant"]
                                for x, y in positives
                            ),
                            "additional_irrelevant": sum(
                                y["retrieved_irrelevant"] - x["retrieved_irrelevant"]
                                for x, y in positives
                            ),
                            "metrics": {metric: paired(left, right, metric) for metric in METRICS},
                        }
                    )
    return result
