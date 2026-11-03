#!/usr/bin/env python
"""Validate the frozen retrieval eval set, or measure it with a locally cached model."""

import argparse
import json
import os
import re
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import load_eval_set


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--k", type=int)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--compare-baselines", action="store_true")
    args = parser.parse_args()
    if args.compare_baselines and (args.k is not None or args.min_score is not None):
        parser.error("Baseline comparison fixes k=1,3,5,8 and the operational threshold at 0.25")
    overrides = {
        key: value
        for key, value in {
            "embedding_model": args.model,
            "retrieval_k": args.k,
            "retrieval_min_score": args.min_score,
        }.items()
        if value is not None
    }
    try:
        settings = Settings(**overrides)
        folder = args.eval_dir if args.eval_dir is not None else settings.data_eval_dir
        questions, corpus, _ = load_eval_set(folder)
        if args.check_only:
            print(json.dumps({"questions": len(questions), "corpus": len(corpus), "valid": True}))
            return 0
        if args.output is None:
            parser.error("--output is required unless --check-only is used")
        # An evaluation report must never overwrite frozen inputs or production data.
        output = args.output.resolve()
        if output.is_relative_to(settings.data_raw_dir.resolve()) or any(
            output.is_relative_to(path.resolve())
            for path in (
                settings.data_gold_dir,
                settings.data_splits_dir,
                folder,
                settings.data_external_dir,
                settings.chroma_path,
            )
        ):
            parser.error("Write reports outside source datasets and database directories")
        from huggingface_hub import try_to_load_from_cache
        from sentence_transformers import SentenceTransformer

        from partner_copilot.evaluation.retrieval import evaluate
        from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder

        model_details = {}

        def load_cached_model(name, device):
            model = SentenceTransformer(name, device=device, local_files_only=True)
            revision = getattr(model[0].auto_model.config, "_commit_hash", None)
            repo_id = name if "/" in name else f"sentence-transformers/{name}"
            cached = try_to_load_from_cache(
                repo_id, "config.json", cache_dir=os.environ.get("SENTENCE_TRANSFORMERS_HOME")
            )
            if revision is None and isinstance(cached, str):
                snapshot = Path(cached).parent.name
                revision = snapshot if re.fullmatch(r"[a-f0-9]{40}", snapshot) else None
            model_details["revision"] = revision
            for review in corpus:
                length = len(model.tokenizer(embedder.document_prefix + review.text)["input_ids"])
                if length > model.max_seq_length:
                    raise ValueError(
                        "Eval review exceeds model context; explicit chunking is needed"
                    )
            return model

        embedder = SentenceTransformerEmbedder(settings, model_factory=load_cached_model)
        # No production database path is accepted. On Windows the client may retain handles
        # until process exit; cleanup errors must not discard a successful evaluation report.
        with TemporaryDirectory(prefix="partner-copilot-eval-", ignore_cleanup_errors=True) as tmp:
            if args.compare_baselines:
                from partner_copilot.evaluation.baselines import compare_baselines

                report = compare_baselines(folder, embedder)
            else:
                report = evaluate(folder, Path(tmp) / "chroma", embedder, settings)
            report["model_revision"] = model_details["revision"]
            report["runtime_versions"] = {
                name: version(name)
                for name in (
                    "chromadb",
                    "sentence-transformers",
                    "transformers",
                    "torch",
                    "pydantic",
                )
            }
            report["embedding_prefixes"] = {
                "document": embedder.document_prefix,
                "query": embedder.query_prefix,
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        if args.compare_baselines:
            print(json.dumps({"report": str(output), "ks": report["ks"]}))
        else:
            print(json.dumps({mode: value["summary"] for mode, value in report["modes"].items()}))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Evaluation failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
