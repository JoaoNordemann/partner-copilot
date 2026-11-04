"""Rescore a reviewed eval version using existing model and lexical rankings."""

import argparse
import json
from pathlib import Path

from partner_copilot.config import get_settings
from partner_copilot.evaluation.rescore import rescore_review


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--parent-eval-dir", type=Path)
    parser.add_argument("--source-reports", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    settings = get_settings()
    parent = args.parent_eval_dir if args.parent_eval_dir else settings.data_eval_dir
    output = args.output_dir.resolve()
    sources = args.source_reports.resolve()
    if output == sources or any(
        output.is_relative_to(path.resolve())
        for path in (
            parent,
            args.eval_dir,
            settings.data_raw_dir,
            settings.data_gold_dir,
            settings.data_splits_dir,
            settings.chroma_path,
            settings.data_external_dir,
        )
    ):
        parser.error("Write reviewed reports outside source reports, datasets and databases")
    names = ("retrieval-baseline.json", "retrieval-comparison.json", "min-score-protocol.json")
    inputs = [json.loads((sources / name).read_text(encoding="utf-8")) for name in names]
    results = rescore_review(parent, args.eval_dir, *inputs)
    output.mkdir(parents=True, exist_ok=True)
    for name, result in results.items():
        (output / name).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "reports": str(output),
                "changed_questions": results[names[0]]["rescore_provenance"][
                    "changed_question_ids"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
