"""Calibrate a fixed min_score protocol using frozen pre-threshold rankings."""

import argparse
import json
from pathlib import Path

from partner_copilot.config import get_settings
from partner_copilot.evaluation.calibration import calibrate
from partner_copilot.evaluation.dataset import load_eval_set


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    folder = args.eval_dir if args.eval_dir else settings.data_eval_dir
    if args.output.resolve() in {args.input.resolve(), args.protocol.resolve()} or any(
        args.output.resolve().is_relative_to(path.resolve())
        for path in (
            folder,
            settings.data_raw_dir,
            settings.data_gold_dir,
            settings.data_splits_dir,
            settings.data_external_dir,
            settings.chroma_path,
        )
    ):
        parser.error("Output must not overwrite inputs or source datasets")
    questions, _, manifest = load_eval_set(folder)
    comparison = json.loads(args.input.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if manifest["file_sha256_lf"] != protocol["snapshot_sha256_lf"]:
        parser.error("Eval set differs from the calibration protocol")
    report = calibrate(questions, comparison, protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"threshold": report["selected_threshold"], "modes": report["modes"]}))


if __name__ == "__main__":
    main()
