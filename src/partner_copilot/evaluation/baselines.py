"""Fixed multi-k metrics and cheap baselines, independent from relevance judgments."""

import random
import re
import unicodedata
from pathlib import Path
from statistics import mean, pstdev

import numpy as np

from partner_copilot.evaluation.dataset import EvalQuestion, load_eval_set
from partner_copilot.ingestion.embedder import Embedder

KS = (1, 3, 5, 8)
SEEDS = range(42, 242)
# Fixed before calculating results; no corpus-frequency or relevance-based selection.
STOPWORDS = frozenset(
    [
        "a",
        "ao",
        "aos",
        "as",
        "ate",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "entre",
        "essa",
        "esse",
        "esta",
        "este",
        "foi",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "ou",
        "para",
        "pela",
        "pelas",
        "pelo",
        "pelos",
        "por",
        "qual",
        "quais",
        "que",
        "quem",
        "se",
        "seu",
        "sua",
        "suas",
        "seus",
        "um",
        "uma",
        "uns",
        "umas",
        "nos",
        "nas",
        "sao",
        "foi",
        "ser",
        "ha",
        "the",
    ]
)


def tokens(text: str) -> set[str]:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(char) != "Mn"
    )
    return set(re.findall(r"[a-z0-9]+", normalized)) - STOPWORDS


def question_metrics(question: EvalQuestion, identifiers: list[str], k: int) -> dict:
    if k < 1 or len(identifiers) != len(set(identifiers)):
        raise ValueError("k must be positive and returned IDs unique")
    selected = identifiers[:k]
    relevant = set(question.relevantes)
    hits = len(set(selected) & relevant)
    rank = next(
        (rank for rank, identifier in enumerate(selected, 1) if identifier in relevant), None
    )
    return {
        "deve_abster": question.deve_abster,
        "abstained": not selected,
        "hit_at_k": float(hits > 0) if relevant else None,
        "recall_capped_at_k": hits / min(k, len(relevant)) if relevant else None,
        "recall_classic_at_k": hits / len(relevant) if relevant else None,
        "mrr_at_k": 1 / rank if rank is not None else 0.0 if relevant else None,
        "precision_at_k": hits / k if relevant else None,
    }


def aggregate(rows: list[dict]) -> dict:
    positives = [row for row in rows if not row["deve_abster"]]
    negatives = [row for row in rows if row["deve_abster"]]
    result = {
        name: mean(row[name] for row in positives) if positives else None
        for name in (
            "hit_at_k",
            "recall_capped_at_k",
            "recall_classic_at_k",
            "mrr_at_k",
            "precision_at_k",
        )
    }
    result.update(
        {
            "answerable_abstention_rate": mean(row["abstained"] for row in positives)
            if positives
            else None,
            "correct_abstention_rate": mean(row["abstained"] for row in negatives)
            if negatives
            else None,
            "false_evidence_rate": mean(not row["abstained"] for row in negatives)
            if negatives
            else None,
        }
    )
    return result


def score_rankings(questions: list[EvalQuestion], rankings: dict[str, list[str]]) -> dict:
    return {
        str(k): aggregate([question_metrics(q, rankings[q.id], k) for q in questions]) for k in KS
    }


def compare_baselines(folder: Path, embedder: Embedder) -> dict:
    questions, corpus, manifest = load_eval_set(folder)
    # Full exact cosine ranking isolates embedding quality from ANN approximation on 100 texts.
    vectors = np.asarray(embedder.embed_documents([r.text for r in corpus]), dtype=np.float64)
    queries = np.asarray([embedder.embed_query(q.pergunta) for q in questions], dtype=np.float64)
    if (
        not np.isfinite(vectors).all()
        or not np.isfinite(queries).all()
        or np.any(np.linalg.norm(vectors, axis=1) == 0)
        or np.any(np.linalg.norm(queries, axis=1) == 0)
    ):
        raise ValueError("Embeddings must be finite and nonzero")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    similarities = queries @ vectors.T
    lexical_documents = [tokens(review.text) for review in corpus]
    methods = {name: {} for name in ("semantic", "keyword", "random")}
    for mode in ("sem_filtro", "com_filtro"):
        eligible = {
            q.id: [
                i
                for i, review in enumerate(corpus)
                if mode == "sem_filtro" or q.filtros.matches(review)
            ]
            for q in questions
        }
        for method in ("semantic", "keyword"):
            ranked, gated, details = {}, {}, []
            for qi, q in enumerate(questions):
                query_terms = tokens(q.pergunta)
                scores = {
                    i: float(similarities[qi, i])
                    if method == "semantic"
                    else len(query_terms & lexical_documents[i])
                    for i in eligible[q.id]
                }
                ordered = sorted(scores, key=lambda i: (-scores[i], corpus[i].id))
                ranked[q.id] = [corpus[i].id for i in ordered]
                gated[q.id] = [
                    corpus[i].id
                    for i in ordered
                    if (scores[i] >= 0.25 if method == "semantic" else scores[i] > 0)
                ]
                details.append(
                    {
                        "id": q.id,
                        "eligible_count": len(ordered),
                        "ranked_ids": ranked[q.id][: max(KS)],
                        "scores": [scores[i] for i in ordered[: max(KS)]],
                        "operational_ids": gated[q.id][: max(KS)],
                    }
                )
            methods[method][mode] = {
                "ranking": score_rankings(questions, ranked),
                "operational": score_rankings(questions, gated),
                "questions": details,
            }
        repetitions = []
        seed_example = None
        for seed in SEEDS:
            ranked = {}
            for q in questions:
                indices = sorted(eligible[q.id], key=lambda i: corpus[i].id)
                random.Random(f"{seed}:{q.id}").shuffle(indices)
                ranked[q.id] = [corpus[i].id for i in indices]
            repetitions.append(score_rankings(questions, ranked))
            if seed == SEEDS.start:
                seed_example = {key: value[: max(KS)] for key, value in ranked.items()}
        random_summary = {}
        for k in map(str, KS):
            random_summary[k] = {
                stat: {
                    metric: (
                        operation(run[k][metric] for run in repetitions)
                        if repetitions[0][k][metric] is not None
                        else None
                    )
                    for metric in repetitions[0][k]
                }
                for stat, operation in (("mean", mean), ("std", pstdev))
            }
        methods["random"][mode] = {
            "ranking": random_summary,
            "operational_same_as_ranking": True,
            "seed_42_rankings": seed_example,
        }
    return {
        "protocol": "multi_k_v1",
        "ks": list(KS),
        "corpus_count": len(corpus),
        "answerable_questions": 24,
        "unanswerable_questions": 6,
        "model": embedder.model_name,
        "semantic_ranking": "exact cosine over identical corpus",
        "semantic_operational_min_score": 0.25,
        "keyword_score": "distinct token intersection",
        "keyword_stopwords": sorted(STOPWORDS),
        "keyword_operational_min_score_exclusive": 0,
        "random": {
            "repetitions": len(SEEDS),
            "seeds": [SEEDS.start, SEEDS.stop - 1],
            "rng": "Random(f'{seed}:{question_id}').shuffle on ID-sorted eligible corpus",
        },
        "snapshot_sha256_lf": manifest["file_sha256_lf"],
        "annotation_status": manifest["annotation_status"],
        "purpose": manifest["purpose"],
        "english_ablation": {
            "executed": False,
            "reason": (
                "English model not supplied to this run; see documented local collection inventory"
            ),
        },
        "methods": methods,
    }
