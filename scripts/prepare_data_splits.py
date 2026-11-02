#!/usr/bin/env python
"""Create deterministic evaluation, ABSA training and RAG partitions."""

import argparse
import json
from pathlib import Path

from partner_copilot.data_splits import build_splits, validate_splits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--gold-dir", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--seed", type=int, default=2718)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    from partner_copilot.config import get_settings

    settings = get_settings()
    args.source = args.source if args.source is not None else settings.raw_reviews_path
    args.gold_dir = args.gold_dir if args.gold_dir is not None else settings.data_gold_dir
    args.out_dir = args.out_dir if args.out_dir is not None else settings.data_splits_dir
    manifest = (
        validate_splits(args.out_dir)
        if args.check_only
        else build_splits(
            args.source,
            args.gold_dir,
            args.out_dir,
            seed=args.seed,
            train_fraction=args.train_fraction,
        )
    )
    print(
        json.dumps(
            {
                "counts": manifest["counts"],
                "gold_status": manifest["gold_status"],
                "reserved_gold_ids": len(manifest["gold_reserved_ids"]),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
