"""Compare aspect metadata sources in isolated CPU Chroma collections."""

import argparse
import itertools
import json
import subprocess
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from partner_copilot.config import Settings
from partner_copilot.evaluation.ablations import paired, summarize_rankings
from partner_copilot.evaluation.dataset import load_eval_set, text_hash
from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
from partner_copilot.retrieval.retriever import date_key

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data/eval/human-v2"
PREDICTIONS = ROOT / "reports/absa-eval-checkpoint-253-v1/retrieval-predictions.jsonl"
GENERATOR = ROOT / "data/raw/reviews.jsonl"
HUMAN = ROOT / "data/gold/aspects_100.human.jsonl"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MIN_SCORE = 0.25
GROUPS = {
    "embalagem": (1, 5, 21),
    "atendimento": (2, 23),
    "temperatura": (3, 6, 19),
    "sabor": (4, 7, 14, 15, 16, 17, 18, 22, 29),
    "preco": (8, 24),
    "tempo_entrega": (9, 10, 11, 12, 13, 20, 30),
}
ASPECTS = {f"q{number:02}": aspect for aspect, numbers in GROUPS.items() for number in numbers}


def load_rows(path, key="id"):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    index = {row[key]: row for row in rows}
    if len(rows) != len(index):
        raise ValueError(f"Duplicate IDs in {path}")
    return index


def filters(question, arm):
    scope = question.filtros
    conditions = [{"restaurant_id": scope.restaurant_id}]
    if scope.item is not None:
        conditions.append({"item": scope.item})
    if scope.start_date is not None:
        conditions.append({"created_at_int": {"$gte": date_key(scope.start_date)}})
    if scope.end_date is not None:
        conditions.append({"created_at_int": {"$lte": date_key(scope.end_date)}})
    aspect = ASPECTS.get(question.id)
    if arm != "A" and aspect:
        negative = {f"aspect_{aspect}": "neg"}
        conditions.append(
            {"$or": [negative, {"absa_status": "inválido"}]} if arm == "B" else negative
        )
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def collect(database, snapshot, questions, corpus, sources, predictions):
    import chromadb
    from sentence_transformers import SentenceTransformer

    config = Settings(
        _env_file=None,
        embedding_model=MODEL,
        embedding_device="cpu",
        embedding_prefix_mode="auto",
        embedding_batch_size=32,
    )
    model = SentenceTransformer(str(snapshot), device="cpu", local_files_only=True)
    embedder = SentenceTransformerEmbedder(config, model_factory=lambda *_: model)
    texts = [review.text for review in corpus]
    prompts = [question.pergunta for question in questions]
    max_tokens = max(len(model.tokenizer(text)["input_ids"]) for text in texts + prompts)
    if max_tokens > model.max_seq_length:
        raise ValueError("Corpus or query requires chunking")
    vectors = embedder.embed_documents(texts)
    query_vectors = [embedder.embed_query(prompt) for prompt in prompts]
    base_metadata = [
        {"restaurant_id": r.restaurant_id, "item": r.item or "", "created_at_int": r.created_at_int}
        for r in corpus
    ]
    client = chromadb.PersistentClient(path=database)
    rankings = {str(k): {} for k in (5, 8)}
    for arm, labels in sources.items():
        collection = client.create_collection(
            f"absa-retrieval-{arm.lower()}",
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        metadata = []
        for review, base in zip(corpus, base_metadata, strict=True):
            aspects = {f"aspect_{key}": value for key, value in labels.get(review.id, {}).items()}
            row = {**base, **aspects}
            if arm == "B":
                row["absa_status"] = predictions[review.id]["status"]
            metadata.append(row)
        collection.add(
            ids=[r.id for r in corpus], documents=texts, embeddings=vectors, metadatas=metadata
        )
        for k, by_arm in rankings.items():
            by_arm[arm] = {}
            for question, query in zip(questions, query_vectors, strict=True):
                result = collection.query(
                    query_embeddings=[query],
                    where=filters(question, arm),
                    n_results=2 * int(k),
                    include=["distances"],
                )
                ranked = zip(result["distances"][0], result["ids"][0], strict=True)
                by_arm[arm][question.id] = [
                    review_id for distance, review_id in ranked if 1 - distance >= MIN_SCORE
                ][: int(k)]
    return rankings, max_tokens


def audit_losses(questions, rankings, sources, predictions):
    audit = {}
    for q in questions:
        if q.deve_abster:
            continue
        relevant = set(q.relevantes)
        aspect = ASPECTS[q.id]
        before = relevant.intersection(rankings["A"][q.id])
        changes = {}
        for arm in ("B", "C", "D"):
            after = relevant.intersection(rankings[arm][q.id])
            labels = sources[arm]
            lost = {
                review_id: labels[review_id].get(aspect, "ausente")
                for review_id in sorted(before - after)
            }
            excluded = {
                review_id: labels[review_id].get(aspect, "ausente")
                for review_id in sorted(relevant)
                if labels[review_id].get(aspect) != "neg"
                and (arm != "B" or predictions[review_id]["status"] == "ok")
            }
            changes[arm] = {
                "lost": lost,
                "gained": sorted(after - before),
                "excluded_by_aspect": excluded,
                "lost_all_top_5": bool(before and not after),
            }
        audit[q.id] = changes
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / "work/hf-cache/sentence-transformers")
    args = parser.parse_args()
    from huggingface_hub import snapshot_download

    questions, corpus, _ = load_eval_set(EVAL)
    if set(ASPECTS) != {q.id for q in questions if not q.deve_abster} | {"q29", "q30"}:
        raise ValueError("Question mapping differs from the protocol")
    source = load_rows(GENERATOR)
    human = load_rows(HUMAN)
    predictions = load_rows(PREDICTIONS, "review_id")
    manifest = json.loads(PREDICTIONS.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    if (
        text_hash(PREDICTIONS) != manifest["predictions_sha256_lf"]
        or text_hash(EVAL / "corpus.jsonl") != manifest["corpus_sha256_lf"]
        or {r.id for r in corpus} != human.keys()
        or human.keys() != predictions.keys()
        or any(source[r.id]["text"] != r.text for r in corpus)
    ):
        raise ValueError("Corpus, annotations or predictions differ from frozen inputs")
    sources = {
        "A": {},
        "B": {key: row["aspects"] for key, row in predictions.items()},
        "C": {r.id: source[r.id]["aspects"] for r in corpus},
        "D": {key: row["aspects"] for key, row in human.items()},
    }
    snapshot = Path(
        snapshot_download(
            MODEL,
            revision=REVISION,
            cache_dir=args.cache,
            token=False,
            local_files_only=True,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
        )
    )
    # Chroma keeps Windows file handles open until process exit.
    # A dedicated directory within a fresh run directory isolates the production database.
    with TemporaryDirectory(prefix="absa-retrieval-", ignore_cleanup_errors=True) as database:
        rankings, max_tokens = collect(database, snapshot, questions, corpus, sources, predictions)
    metrics = {
        k: {arm: summarize_rankings(questions, by_question)[k] for arm, by_question in arms.items()}
        for k, arms in rankings.items()
    }
    comparisons = {}
    for k, arms in metrics.items():
        comparisons[k] = [
            {
                "reference": a,
                "variant": b,
                "metric": metric,
                **paired(arms[a]["questions"], arms[b]["questions"], metric),
            }
            for a, b in itertools.combinations(arms, 2)
            for metric in ("precision_at_k", "recall_capped_at_k")
        ]
    loss_audit = audit_losses(questions, rankings["5"], sources, predictions)
    summary = metrics["5"]
    a, b = (summary[arm]["summary"] for arm in ("A", "B"))
    precision_gain = b["precision_at_k"] - a["precision_at_k"]
    recall_change = b["recall_capped_at_k"] - a["recall_capped_at_k"]
    lost_all = sum(row["B"]["lost_all_top_5"] for row in loss_audit.values())
    report = {
        "analysis": "exploratory, synthetic corpus, previously seen questions",
        "protocol_commit": "8505f09247bd4daf6579af54fc7ef1d0aaf7394c",
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "inputs_sha256_lf": {
            path.relative_to(ROOT).as_posix(): text_hash(path)
            for path in (
                EVAL / "corpus.jsonl",
                EVAL / "questions.jsonl",
                PREDICTIONS,
                GENERATOR,
                HUMAN,
            )
        },
        "embedding": {
            "model": MODEL,
            "revision": REVISION,
            "device": "cpu",
            "max_tokens": max_tokens,
        },
        "packages": {
            package: version(package) for package in ("chromadb", "sentence-transformers", "torch")
        },
        "min_score": MIN_SCORE,
        "aspect_mapping": ASPECTS,
        "predictions_invalid": manifest["invalid"],
        "rankings": rankings,
        "metrics": metrics,
        "comparisons": comparisons,
        "loss_audit_at_5": loss_audit,
        "criterion": {
            "precision_gain": precision_gain,
            "recall_change": recall_change,
            "lost_all": lost_all,
            "passed": precision_gain >= 0.02 and recall_change >= -0.02 and lost_all <= 1,
        },
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(json.dumps(report["criterion"]))


if __name__ == "__main__":
    main()
