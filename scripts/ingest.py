#!/usr/bin/env python
"""Ingest review JSONL using the configured multilingual embedding model.

Run from the repository root after installing the package:
    python scripts/ingest.py --batch-size 128
"""

import argparse
import logging
from pathlib import Path

from partner_copilot.config import get_settings
from partner_copilot.ingestion.indexer import ingest_reviews

logger = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Default: DATA_RAW_DIR/reviews.jsonl")
    parser.add_argument("--batch-size", type=positive_int, default=128)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    settings = get_settings()
    path = args.input or settings.data_raw_dir / "reviews.jsonl"
    if not path.is_file():
        parser.error(f"Input file does not exist: {path}")
    settings.export_hf_env()
    from partner_copilot.retrieval.store import ChromaStore

    store = ChromaStore(
        path=settings.chroma_path,
        model=settings.embedding_model,
        collection=settings.chroma_collection,
    )
    processed = ingest_reviews(path, store, batch_size=args.batch_size)
    logger.info(
        "Processed %d reviews; collection=%s; path=%s; total=%d",
        processed,
        settings.chroma_collection,
        settings.chroma_path,
        store.col.count(),
    )


if __name__ == "__main__":
    main()
