#!/usr/bin/env python
"""Ingest the registered RAG split into persistent Chroma storage."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pydantic import ValidationError

from partner_copilot.config import Settings
from partner_copilot.ingestion.service import IngestionPreflightError, run_ingestion

logger = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Data path; default: DATA_SPLITS_DIR/rag.jsonl (registered RAG split)",
    )
    parser.add_argument(
        "--db-path", type=Path, help="Persistent database path; default: CHROMA_PATH"
    )
    parser.add_argument(
        "--model",
        "--embedding-model",
        dest="model",
        help="Embedding model; default: EMBEDDING_MODEL",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=128,
        help="Document upsert batch size (default: 128)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear only the selected collection before re-ingestion",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    overrides = {}
    if args.db_path is not None:
        overrides["chroma_path"] = args.db_path
    if args.model is not None:
        overrides["embedding_model"] = args.model
    try:
        settings = Settings(**overrides)
    except ValidationError as exc:
        parser.error(str(exc))
    try:
        outcome = run_ingestion(
            settings, input_path=args.input, batch_size=args.batch_size, reset=args.reset
        )
    except IngestionPreflightError as exc:
        parser.error(str(exc))
    except Exception:
        logger.exception("Ingestion failed")
        return 1
    logger.info(
        "Ingestion report=%s; collection=%s; path=%s; total=%d; reset_removed=%d",
        outcome.report.to_dict(),
        outcome.collection,
        outcome.database_path,
        outcome.total_documents,
        outcome.reset_removed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
