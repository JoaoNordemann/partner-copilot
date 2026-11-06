#!/usr/bin/env python
"""Run the frozen CPU-only MiniLM ablation in fresh, model-specific collections."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from partner_copilot.config import Settings
from partner_copilot.evaluation.ablations import (
    KS,
    MODES,
    cheap_methods,
    compare_methods,
    eligible_reviews,
    summarize_rankings,
)
from partner_copilot.evaluation.baselines import STOPWORDS
from partner_copilot.evaluation.dataset import load_eval_set, text_hash

MODELS = {
    "english": "sentence-transformers/all-MiniLM-L6-v2",
    "multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}
ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_model(name: str, folder: Path, database: Path, cache: Path, allow_download: bool) -> dict:
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    from partner_copilot.ingestion.chroma_store import ChromaStore
    from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder

    questions, corpus, _ = load_eval_set(folder)
    started = perf_counter()
    snapshot = Path(
        snapshot_download(
            name,
            cache_dir=str(cache),
            local_files_only=not allow_download,
            token=False,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
        )
    )
    config = Settings(
        _env_file=None,
        embedding_model=name,
        embedding_device="cpu",
        embedding_prefix_mode="auto",
        embedding_batch_size=32,
        hf_token=None,
    )
    loaded = {}

    def factory(model_name, device):
        model = SentenceTransformer(
            str(snapshot), device=device, local_files_only=True, trust_remote_code=False
        )
        prefix = "passage: " if "e5" in name else ""
        query_prefix = "query: " if "e5" in name else ""
        lengths = [len(model.tokenizer(prefix + r.text)["input_ids"]) for r in corpus]
        query_lengths = [
            len(model.tokenizer(query_prefix + q.pergunta)["input_ids"]) for q in questions
        ]
        if max(lengths + query_lengths) > model.max_seq_length:
            raise ValueError("Truncation would occur; define chunking before measuring")
        loaded.update(
            max_document_tokens=max(lengths),
            max_query_tokens=max(query_lengths),
            max_seq_length=model.max_seq_length,
        )
        return model

    embedder = SentenceTransformerEmbedder(config, model_factory=factory)
    store = ChromaStore(database, embedder=embedder, settings=config)
    if store.count():
        raise ValueError("Ablation requires a freshly created collection")
    store.upsert(corpus)
    assert store.count() == len(corpus)
    modes, full_rankings = {}, {}
    for mode in MODES:
        ranked, gated, details = {}, {}, []
        for q in questions:
            where = {"restaurant_id": q.filtros.restaurant_id} if mode == "restaurante" else None
            # Exhaust all eligible documents: HNSW candidate selection cannot drop a document.
            docs = store.query(q.pergunta, len(corpus), where=where)
            assert {d.review.id for d in docs} == {r.id for r in eligible_reviews(q, corpus, mode)}
            docs.sort(key=lambda d: (-d.score, d.review.id))
            ranked[q.id] = [d.review.id for d in docs]
            gated[q.id] = [d.review.id for d in docs if d.score >= 0.25]
            details.append(
                {
                    "id": q.id,
                    "eligible_count": len(docs),
                    "ranked_ids": ranked[q.id],
                    "scores": [d.score for d in docs],
                }
            )
        modes[mode] = {
            "ranking": summarize_rankings(questions, ranked),
            "operational": summarize_rankings(questions, gated),
        }
        full_rankings[mode] = details
    return {
        "model": name,
        "revision": snapshot.name,
        "device": "cpu",
        "collection": store.collection_name,
        "corpus_count": store.count(),
        "document_prefix": embedder.document_prefix,
        "query_prefix": embedder.query_prefix,
        "token_limits": loaded,
        "elapsed_seconds_including_load": perf_counter() - started,
        "modes": modes,
        "full_rankings": full_rankings,
    }


def render_report(report: dict) -> str:
    lines = [
        "# Retrieval CPU: complete ablation matrix",
        "",
        "Development benchmark: 30 exposed questions, 24 answerable; no generation measured.",
        "Restaurant-only filtering; item/date filters are intentionally absent.",
        "Metrics are macro over answerable questions. Empty precision slots count as zero.",
        "Random rows use the per-question mean over 200 seeds, not a single random draw.",
        "No tuning or automatic default changes. All attempted models are listed in results.json.",
        "",
        "| Policy | Method | Filter | k | Hit | Capped recall | Classic recall | MRR | Precision |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for policy in ("ranking", "operational"):
        for name, modes in report["methods"].items():
            for mode in MODES:
                for k in map(str, KS):
                    row = modes[mode][policy][k]["summary"]
                    values = [
                        row[key]
                        for key in (
                            "hit_at_k",
                            "recall_capped_at_k",
                            "recall_classic_at_k",
                            "mrr_at_k",
                            "precision_at_k",
                        )
                    ]
                    lines.append(
                        f"| {policy} | {name} | {mode} | {k} | "
                        + " | ".join(f"{v:.4f}" for v in values)
                        + " |"
                    )
    lines += [
        "",
        "## Primary comparison",
        "",
        "Multilingual versus English, capped recall@5 without filter, no score cutoff.",
    ]
    primary = next(
        (
            r
            for r in report["paired"]["methods"]
            if r["reference"] == "english"
            and r["variant"] == "multilingual"
            and r["policy"] == "ranking"
            and r["mode"] == "sem_filtro"
            and r["k"] == 5
            and r["metric"] == "recall_capped_at_k"
        ),
        None,
    )
    if primary:
        lines.append(
            f"Wins {primary['wins']}, ties {primary['ties']}, losses {primary['losses']} "
            f"/ {primary['questions']}; mean delta {primary['mean_delta']:.6f}."
        )
    else:
        lines.append("Not executed completely; no primary conclusion.")
    lines += [
        "",
        "## Interpretation limits",
        "",
        "This is not an independent test. Language suitability motivated the "
        "multilingual choice before this comparison.",
        "No model is declared best by selecting a favorable k or metric after the run.",
        "Capped recall changes denominator with k and need not increase. Classic "
        "recall and added relevant/irrelevant counts are in results.json.",
        "Negative questions, abstention, random dispersion and all paired "
        "question-level deltas are in results.json.",
        "Collections are rebuilt separately in a temporary isolated database; "
        "production Chroma is untouched.",
        "Full candidate retrieval measures ranking, not production ANN latency. "
        "Elapsed time includes model load/download.",
        "Question/corpus annotations retain their original provenance; no "
        "human-independent gold is claimed.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path, default=ROOT / "data/eval/human-v2")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--cache-dir", type=Path, default=ROOT / "work/hf-cache/sentence-transformers"
    )
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    folder, output = args.eval_dir.resolve(), args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "reports").resolve()):
        parser.error("Output must be a new directory under reports/")
    output.mkdir(parents=True, exist_ok=False)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    questions, corpus, manifest = load_eval_set(folder)
    report = {
        "protocol": "retrieval-cpu-ablation-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_measured": False,
        "evaluation_status": "exposed_development",
        "ks": list(KS),
        "filter_scope": "restaurant_id only",
        "snapshot": manifest["file_sha256_lf"],
        "annotation_status": manifest["annotation_status"],
        "corpus_count": len(corpus),
        "questions": len(questions),
        "primary": "multilingual minus english, ranking, sem_filtro, capped recall@5",
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "code_sha256": {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                Path(__file__).resolve(),
                ROOT / "src/partner_copilot/evaluation/ablations.py",
                ROOT / "src/partner_copilot/evaluation/baselines.py",
                ROOT / "src/partner_copilot/ingestion/embedder.py",
                ROOT / "src/partner_copilot/ingestion/chroma_store.py",
            ]
        },
        "protocol_sha256_lf": text_hash(ROOT / "docs/decisions.md"),
        "runtime": {
            "python": platform.python_version(),
            **{
                n: version(n)
                for n in ["torch", "transformers", "sentence-transformers", "chromadb", "pydantic"]
            },
        },
        "keyword_stopwords": sorted(STOPWORDS),
        "random_seeds": [42, 241],
        "attempts": [],
        "methods": {},
    }
    # Freeze metadata before any numeric evaluation. Output directories cannot be reused.
    (output / "protocol.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for label, name in MODELS.items():
        try:
            with TemporaryDirectory(
                prefix="partner-retrieval-ablation-", ignore_cleanup_errors=True
            ) as tmp:
                model = run_model(
                    name,
                    folder,
                    Path(tmp) / "chroma",
                    args.cache_dir.resolve(),
                    args.allow_download,
                )
            (output / f"{label}.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
            report["methods"][label] = model["modes"]
            report["attempts"].append(
                {"method": label, "model": name, "status": "ok", "revision": model["revision"]}
            )
            print(f"Completed {label}", flush=True)
        except Exception as exc:
            report["attempts"].append(
                {
                    "method": label,
                    "model": name,
                    "status": "error",
                    "error_type": type(exc).__name__,
                }
            )
            print(f"Failed {label}: {type(exc).__name__}", flush=True)
    report["methods"].update(cheap_methods(questions, corpus))
    report["paired"] = compare_methods(report["methods"])
    report["complete"] = all(a["status"] == "ok" for a in report["attempts"])
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "README.md").write_text(render_report(report), encoding="utf-8")
    print(f"Saved {output}; complete={report['complete']}")
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
