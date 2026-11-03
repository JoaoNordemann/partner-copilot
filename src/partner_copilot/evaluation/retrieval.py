"""Score a fixed development set in semantic-only and production-filtered modes."""

from pathlib import Path
from statistics import mean

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.embedder import Embedder
from partner_copilot.retrieval.retriever import Retriever


def summarize(rows: list[dict]) -> dict:
    answerable = [row for row in rows if not row["deve_abster"]]
    unanswerable = [row for row in rows if row["deve_abster"]]
    return {
        "questions": len(rows),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "recall_at_k": mean(row["recall_at_k"] for row in answerable) if answerable else None,
        "mrr_at_k": mean(row["reciprocal_rank"] for row in answerable) if answerable else None,
        "answerable_abstention_rate": mean(not row["returned_ids"] for row in answerable)
        if answerable
        else None,
        "correct_abstention_rate": mean(not row["returned_ids"] for row in unanswerable)
        if unanswerable
        else None,
        "false_answer_rate": mean(bool(row["returned_ids"]) for row in unanswerable)
        if unanswerable
        else None,
    }


def evaluate(
    folder: Path,
    database_path: Path,
    embedder: Embedder,
    settings: Settings,
) -> dict:
    """Use an empty, dedicated evaluation database; never reset an existing collection."""
    questions, corpus, manifest = load_eval_set(folder)
    if database_path.exists() and any(database_path.iterdir()):
        raise ValueError("Evaluation requires an empty database directory")
    store = ChromaStore(
        database_path, collection="isolated_gold_eval", embedder=embedder, settings=settings
    )
    store.upsert(corpus)
    retriever = Retriever(store, settings=settings)
    modes = {}
    for mode in ("sem_filtro", "com_filtro"):
        rows = []
        for question in questions:
            if mode == "com_filtro":
                docs = retriever.retrieve(
                    question.pergunta, **question.filtros.model_dump(exclude_none=True)
                )
            else:
                candidates = store.query(question.pergunta, settings.retrieval_k * 2)
                docs = [doc for doc in candidates if doc.score >= settings.retrieval_min_score][
                    : settings.retrieval_k
                ]
            identifiers = [doc.review.id for doc in docs]
            relevant = set(question.relevantes)
            hits = len(set(identifiers) & relevant)
            reciprocal_rank = next(
                (
                    1 / rank
                    for rank, identifier in enumerate(identifiers, 1)
                    if identifier in relevant
                ),
                0.0,
            )
            rows.append(
                {
                    "id": question.id,
                    "tipo": question.tipo,
                    "deve_abster": question.deve_abster,
                    "returned_ids": identifiers,
                    "scores": [doc.score for doc in docs],
                    "relevant_ids": question.relevantes,
                    "recall_at_k": hits / len(relevant) if relevant else None,
                    "reciprocal_rank": reciprocal_rank if relevant else None,
                }
            )
        modes[mode] = {
            "summary": summarize(rows),
            "per_type": {
                kind: summarize([row for row in rows if row["tipo"] == kind])
                for kind in sorted({row["tipo"] for row in rows})
            },
            "questions": rows,
        }
    return {
        "model": embedder.model_name,
        "k": settings.retrieval_k,
        "min_score": settings.retrieval_min_score,
        "corpus_count": len(corpus),
        "snapshot_sha256_lf": manifest["file_sha256_lf"],
        "annotation_status": manifest["annotation_status"],
        "purpose": manifest["purpose"],
        "modes": modes,
    }
