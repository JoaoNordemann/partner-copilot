"""Run experiment D from a complete saved B JSONL; never overwrite B or C."""

import argparse
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path

from partner_copilot.config import Settings
from partner_copilot.evaluation.abstention import abstention_report
from partner_copilot.evaluation.correction import load_source, run_correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    settings = Settings(prompt_version="partner-copilot-v2", parser_version="parser-v2")
    if args.source.resolve() == args.output.resolve():
        parser.error("Source and output must differ")
    if any(
        args.output.resolve().is_relative_to(path.resolve())
        for path in (
            settings.data_raw_dir,
            settings.data_eval_dir,
            settings.data_gold_dir,
            settings.data_splits_dir,
            settings.chroma_path,
        )
    ):
        parser.error("Choose an output outside source data and production databases")
    rows, _ = load_source(args.source, settings.data_eval_dir, settings)
    if args.check_only:
        print(
            json.dumps(
                {
                    "questions": len(rows),
                    "prompt": settings.prompt_version,
                    "parser": settings.parser_version,
                    "max_corrective_calls_per_question": 1,
                }
            )
        )
        return
    import torch

    if not torch.cuda.is_available():
        parser.error("CUDA required; no fake results will be produced")
    from partner_copilot.generation.provider import get_llm

    settings.export_hf_env()
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted((root / "src/partner_copilot").rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_text(encoding="utf-8").encode())
    environment = {
        "python": platform.python_version(),
        "packages": {
            name: version(name) for name in ("torch", "transformers", "bitsandbytes", "accelerate")
        },
        "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "torch_cuda_version": torch.version.cuda,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "source_code_sha256": digest.hexdigest(),
    }
    results = run_correction(
        args.source,
        args.output,
        settings.data_eval_dir,
        settings,
        lambda: get_llm(settings),
        environment=environment,
        backend="real_mistral_nf4",
        resume=args.resume,
    )
    summary = {
        "experiment": "D",
        "questions": len(results),
        "corrections_requested": sum(r["correction_requested"] for r in results),
        "final_errors": sum(r["error"] is not None for r in results),
        "accepted_llm_outputs": sum(r["llm_called"] and r["status"] == "ok" for r in results),
        "abstention_diagnostics": abstention_report(results),
    }
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "abstention_diagnostics"}, indent=2))


if __name__ == "__main__":
    main()
