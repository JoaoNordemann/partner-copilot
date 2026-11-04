"""Measure random and shared-word retrieval without embeddings or Chroma."""

import argparse
import json
from pathlib import Path

from partner_copilot.config import get_settings
from partner_copilot.evaluation.baselines import measure_cheap_baselines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = get_settings()
    folder = args.eval_dir if args.eval_dir is not None else settings.data_eval_dir
    if any(
        args.output.resolve().is_relative_to(path.resolve())
        for path in (
            folder,
            settings.data_raw_dir,
            settings.data_splits_dir,
            settings.data_gold_dir,
            settings.data_external_dir,
            settings.chroma_path,
        )
    ):
        parser.error("Output must be outside datasets and database directories")
    report = measure_cheap_baselines(folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report": str(args.output),
                "model_loaded": False,
                "repetitions": report["random_repetitions"],
            }
        )
    )


if __name__ == "__main__":
    main()
