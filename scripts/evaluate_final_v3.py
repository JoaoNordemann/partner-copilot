"""One frozen V3 run: new n11-n20 first, contaminated old questions separately."""

import argparse
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from partner_copilot.evaluation.final_v3 import (
    final_settings,
    load_final_set,
    run_final_v3,
    summarize_final,
)


def write_reports(output, rows, expected_ids, negatives):
    summary = summarize_final(rows, expected_ids, negatives)
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    target = output.with_suffix(".review.md")
    if not target.exists():
        lines = [
            "# Leitura V3 - pendente",
            "",
            "Revisor: ____ Origem: ____",
            "",
            "Grupo: " + str(summary["cohort"]),
            "Contaminado por iteracoes anteriores: " + str(summary["contaminated"]),
            "",
            "Trecho literal nao prova que a afirmacao decorre dele ou responde a pergunta.",
            "",
            (
                "| ID | Parser aceita | IDs no contexto | Trechos literais | "
                "Sustentada/pertinente por leitura |"
            ),
            "| --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            d = row["diagnostics"]
            lines.append(
                f"| {row['question_id']} | {d['parser_accepted']} | "
                f"{d['ids_in_context']} | {d['quotes_literal']} | pendente |"
            )
        for row in rows:
            lines += [
                "",
                "## " + row["question_id"],
                "",
                "Pergunta: " + row["pergunta"],
                "",
                "Suporte factual: ____",
                "Pertinencia: ____",
                "Abstencao adequada: ____",
                "",
                "Resposta apresentada ao usuario:",
                json.dumps(row["answer"], ensure_ascii=False),
                "",
                "Resposta bruta (inclui sufixo ignorado, se houver):",
                "```text",
                row["raw_response"] or "(LLM nao chamado)",
                "```",
                "",
                "Contexto:",
            ]
            for doc in row["context"]:
                lines.append(
                    "- " + doc["review_id"] + ": " + json.dumps(doc["text"], ensure_ascii=False)
                )
        with target.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-dir", type=Path, default=Path("data/eval/v3-final-check"))
    parser.add_argument("--old-dir", type=Path, default=Path("data/eval/human-v2"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--suite", choices=("new", "contaminated", "both"), default="both")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    settings = final_settings()
    if any(
        args.output_dir.resolve().is_relative_to(p.resolve())
        for p in (Path("data"), settings.chroma_path, args.new_dir, args.old_dir)
    ):
        parser.error("Write outside source datasets and production databases")
    cohorts = ("new", "contaminated") if args.suite == "both" else (args.suite,)
    loaded = {cohort: load_final_set(cohort, args.new_dir, args.old_dir) for cohort in cohorts}
    if args.check_only:
        print(
            json.dumps(
                {
                    "prompt": settings.prompt_version,
                    "parser": settings.parser_version,
                    "context_k": settings.context_k,
                    "max_new_tokens": settings.max_new_tokens,
                    "retry": False,
                    "cohorts": [
                        {
                            "cohort": key,
                            "questions": len(value[0]),
                            "negatives": sum(q.deve_abster for q in value[0]),
                            "contaminated": key == "contaminated",
                        }
                        for key, value in loaded.items()
                    ],
                },
                indent=2,
            )
        )
        return
    if not args.summarize_only:
        import torch

        if not torch.cuda.is_available():
            parser.error("CUDA required; no fake inference files written")
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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        for cohort, (questions, _, _, _) in loaded.items():
            output = args.output_dir / f"generation-v3-{cohort}.jsonl"
            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            print(
                json.dumps(
                    write_reports(
                        output,
                        rows,
                        [q.id for q in questions],
                        sum(q.deve_abster for q in questions),
                    ),
                    indent=2,
                )
            )
        return
    with TemporaryDirectory(prefix="partner-v3-", ignore_cleanup_errors=True) as temp:
        first_corpus = next(iter(loaded.values()))[1]
        if any(
            [r.model_dump() for r in value[1]] != [r.model_dump() for r in first_corpus]
            for value in loaded.values()
        ):
            raise ValueError("Cohorts must share the same frozen corpus")
        store = ChromaStore(
            Path(temp) / "chroma",
            collection="isolated_final_v3",
            embedder=SentenceTransformerEmbedder(settings),
            settings=settings,
        )
        store.upsert(first_corpus)
        retriever = Retriever(store, settings=settings)
        # get_llm is process-scoped; both cohorts share one loaded model.
        for cohort, (questions, _, _, _) in loaded.items():
            output = args.output_dir / f"generation-v3-{cohort}.jsonl"
            rows = run_final_v3(
                cohort,
                output,
                args.new_dir,
                args.old_dir,
                settings,
                retriever,
                lambda: get_llm(settings),
                environment=environment,
                backend="real_mistral_nf4",
                resume=args.resume,
            )
            print(
                json.dumps(
                    write_reports(
                        output,
                        rows,
                        [q.id for q in questions],
                        sum(q.deve_abster for q in questions),
                    ),
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
