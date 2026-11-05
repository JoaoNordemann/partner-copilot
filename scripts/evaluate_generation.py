"""Run all 30 questions with real Mistral, durable JSONL and explicit resumability."""

import argparse
import hashlib
import json
import logging
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import TemporaryDirectory

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.evaluation.generation import run_generation, summarize_generation
from partner_copilot.generation.output import parser_identity
from partner_copilot.generation.prompts import load_prompt_template

logger = logging.getLogger(__name__)


def read_results(path: Path) -> list[dict]:
    rows = []
    lines = path.read_bytes().splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line.decode("utf-8")))
        except (ValueError, UnicodeDecodeError):
            if index == len(lines) - 1 and not line.endswith(b"\n") and len(rows) < 30:
                logger.warning("Ignoring final interrupted line for summary only")
                break
            raise ValueError("Corrupt results; do not edit the checkpoint") from None
    if rows and any(row["experiment_id"] != rows[0]["experiment_id"] for row in rows):
        raise ValueError("Mixed experiments in results")
    if [row["question_id"] for row in rows] != [f"q{i:02}" for i in range(1, len(rows) + 1)]:
        raise ValueError("Question order differs from the protocol")
    if len({r["question_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate question IDs in results")
    return rows


def write_summary(output: Path, rows: list[dict]) -> dict:
    summary = summarize_generation(rows)
    target = output.with_suffix(".summary.json")
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    by_id = {row["question_id"]: row for row in rows}
    lines = [
        "# Leitura de respostas reais — pendente",
        "",
        "Gerar este arquivo não significa que as respostas foram revisadas.",
        "Revisor: ______  Origem da revisão (humana/IA): ______",
        "",
    ]
    for identifier in summary["manual_review_ids"]:
        lines += [
            "## " + identifier,
            "",
            "Revisada: [ ]",
            "Suporte factual: ______",
            "Abstenção adequada: ______",
            "Citações sustentam afirmações: ______",
            "Observações: ______",
            "",
        ]
        row = by_id.get(identifier)
        if row is None:
            lines += ["Pergunta ainda não executada.", ""]
            continue
        lines += [
            "Pergunta: " + row["pergunta"],
            "",
            "Resposta bruta:",
            json.dumps(row["raw_response"], ensure_ascii=False),
            "",
            "Erro: " + json.dumps(row["error"], ensure_ascii=False),
            "",
            "Contexto enviado:",
        ]
        for doc in row["context"]:
            lines += ["- " + doc["review_id"] + ": " + json.dumps(doc["text"], ensure_ascii=False)]
        lines += [""]
    output.with_suffix(".review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt-version")
    parser.add_argument("--parser-version", choices=("parser-v1", "parser-v2", "parser-json-v1"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        settings = Settings(
            **{
                key: value
                for key, value in {
                    "prompt_version": args.prompt_version,
                    "parser_version": args.parser_version,
                }.items()
                if value is not None
            }
        )
        load_prompt_template(settings.prompt_version)
        parser_identity(settings.parser_version)
        folder = args.eval_dir if args.eval_dir is not None else settings.data_eval_dir
        if any(
            args.output.resolve().is_relative_to(path.resolve())
            for path in (
                settings.data_raw_dir,
                settings.data_gold_dir,
                settings.data_splits_dir,
                settings.data_external_dir,
                settings.chroma_path,
                folder,
            )
        ):
            parser.error("Write results outside source datasets and production databases")
        if args.summarize_only:
            summary = write_summary(args.output, read_results(args.output))
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        questions, corpus, _ = load_eval_set(folder)
        import torch

        if args.check_only:
            print(
                json.dumps(
                    {
                        "prompt_version": settings.prompt_version,
                        "parser_version": settings.parser_version,
                        "questions": len(questions),
                        "corpus": len(corpus),
                        "eval_dir": str(folder),
                        "output": str(args.output),
                        "cuda_available": torch.cuda.is_available(),
                        "token_configured": settings.hf_token is not None,
                    }
                )
            )
            return 0
        if not torch.cuda.is_available():
            parser.error("CUDA unavailable; run in the GPU notebook. No fake results were written.")
        from partner_copilot.generation.provider import get_llm
        from partner_copilot.ingestion.chroma_store import ChromaStore
        from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
        from partner_copilot.retrieval.retriever import Retriever

        packages = {}
        for name in [
            "torch",
            "transformers",
            "bitsandbytes",
            "accelerate",
            "chromadb",
            "sentence-transformers",
        ]:
            try:
                packages[name] = version(name)
            except PackageNotFoundError:
                packages[name] = None
        root = Path(__file__).resolve().parents[1]
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
        )
        source_digest = hashlib.sha256()
        for source in sorted((root / "src/partner_copilot").rglob("*.py")):
            source_digest.update(str(source.relative_to(root)).replace("\\", "/").encode())
            source_digest.update(source.read_text(encoding="utf-8").encode())
        source_digest.update(Path(__file__).read_text(encoding="utf-8").encode())
        environment = {
            "python": sys.version.split()[0],
            "packages": packages,
            "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "torch_cuda_version": torch.version.cuda,
            "source_commit": commit.stdout.strip(),
            "source_code_sha256": source_digest.hexdigest(),
        }
        settings.export_hf_env()
        # Rebuild the tiny isolated gold index locally after a session restart.
        # The durable JSONL may be on Drive; it is never stored in this temporary directory.
        with TemporaryDirectory(
            prefix="partner-copilot-generation-", ignore_cleanup_errors=True
        ) as temp:
            store = ChromaStore(
                Path(temp) / "chroma",
                collection="isolated_generation_eval",
                embedder=SentenceTransformerEmbedder(settings),
                settings=settings,
            )
            store.upsert(corpus)
            rows = run_generation(
                folder,
                args.output,
                settings,
                Retriever(store, settings=settings),
                lambda: get_llm(settings),
                environment=environment,
                backend="real_mistral_nf4",
                resume=args.resume,
            )
        summary = write_summary(args.output, rows)
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary["complete"] and not any(summary["errors"].values()) else 1
    except Exception as exc:
        # Avoid reflecting credentials from backend error messages into logs.
        logger.error(
            "generation_run_failed type=%s; existing checkpoint preserved", type(exc).__name__
        )
        print(
            "Execution failed. Check checkpoint, configuration and GPU; then use --resume.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
