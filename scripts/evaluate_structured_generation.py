"""Run the frozen JSON prompt only on the ten new verification questions."""

import argparse
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from partner_copilot.config import Settings
from partner_copilot.evaluation.structured import (
    load_verification,
    run_structured_verification,
    summarize_structured,
)
from partner_copilot.generation.output import parser_identity


def write_reports(output: Path, rows):
    summary = summarize_structured(rows)
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    review = output.with_suffix(".review.md")
    if not review.exists():
        lines = [
            "# Revisao do JSON: pendente",
            "",
            "Revisor: ____ Origem: ____",
            "",
            "Aceitacao pelo parser nao comprova resposta pertinente ou factual.",
            "",
            "| Pergunta | Aceita pelo parser | Sustentada para a pergunta (leitura) |",
            "| --- | --- | --- |",
        ]
        for r in rows:
            lines.append(
                f"| {r['question_id']} | {r['diagnostics']['parser_accepted']} | pendente |"
            )
        for r in rows:
            lines += [
                "",
                "## " + r["question_id"],
                "",
                "Pergunta: " + r["pergunta"],
                "",
                "Sustentacao factual: ____",
                "Abstencao adequada: ____",
                "Observacoes: ____",
                "",
                "Resposta bruta:",
                "```json",
                r["raw_response"] or "null",
                "```",
                "",
                "Contexto:",
            ]
            for doc in r["context"]:
                lines.append(
                    "- " + doc["review_id"] + ": " + json.dumps(doc["text"], ensure_ascii=False)
                )
        with review.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path, default=Path("data/eval/json-verification-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    settings = Settings(prompt_version="partner-copilot-json-v1", parser_version="parser-json-v1")
    questions, corpus, _manifest = load_verification(args.eval_dir)
    parser_identity(settings.parser_version)
    if any(
        args.output.resolve().is_relative_to(p.resolve())
        for p in (Path("data"), args.eval_dir, settings.chroma_path)
    ):
        parser.error("Write outside source data and databases")
    if args.summarize_only:
        rows = [
            json.loads(line)
            for line in args.output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len({r["experiment_id"] for r in rows}) != 1:
            parser.error("Mixed experiments")
    elif args.check_only:
        print(
            json.dumps(
                {
                    "questions": len(questions),
                    "negatives": sum(q.deve_abster for q in questions),
                    "corpus": len(corpus),
                    "prompt": settings.prompt_version,
                    "parser": settings.parser_version,
                    "retry": False,
                }
            )
        )
        return
    else:
        import torch

        if not torch.cuda.is_available():
            parser.error("CUDA required; no fake model results written")
        from partner_copilot.generation.provider import get_llm
        from partner_copilot.ingestion.chroma_store import ChromaStore
        from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder
        from partner_copilot.retrieval.retriever import Retriever

        settings.export_hf_env()
        root = Path(__file__).resolve().parents[1]
        digest = hashlib.sha256()
        for path in sorted((root / "src/partner_copilot").rglob("*.py")):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_text(encoding="utf-8").encode())
        digest.update(Path(__file__).read_bytes())
        environment = {
            "python": platform.python_version(),
            "packages": {
                name: version(name)
                for name in (
                    "torch",
                    "transformers",
                    "bitsandbytes",
                    "accelerate",
                    "chromadb",
                    "sentence-transformers",
                    "pydantic",
                )
            },
            "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "torch_cuda_version": torch.version.cuda,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            "source_code_sha256": digest.hexdigest(),
        }
        with TemporaryDirectory(prefix="partner-json-eval-", ignore_cleanup_errors=True) as temp:
            store = ChromaStore(
                Path(temp) / "chroma",
                collection="isolated_json_verification",
                embedder=SentenceTransformerEmbedder(settings),
                settings=settings,
            )
            store.upsert(corpus)
            rows = run_structured_verification(
                args.eval_dir,
                args.output,
                settings,
                Retriever(store, settings=settings),
                lambda: get_llm(settings),
                environment=environment,
                backend="real_mistral_nf4",
                resume=args.resume,
            )
    print(json.dumps(write_reports(args.output, rows), indent=2))


if __name__ == "__main__":
    main()
