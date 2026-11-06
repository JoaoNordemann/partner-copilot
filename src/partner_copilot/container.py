"""CPU container bootstrap; no ML imports until an index actually needs building."""

import hashlib
import json
import logging
import os
import sys
from urllib.request import urlopen

from filelock import FileLock

from partner_copilot.api_models import APISettings
from partner_copilot.api_runtime import profile
from partner_copilot.config import Settings
from partner_copilot.data_splits import file_key, validate_rag_input

logger = logging.getLogger(__name__)


def build_index(settings: Settings, api: APISettings) -> None:
    from partner_copilot.api_runtime import load_embedder
    from partner_copilot.ingestion.chroma_store import ChromaStore
    from partner_copilot.ingestion.chunking import TokenTextSplitter
    from partner_copilot.ingestion.pipeline import IngestionPipeline

    embedder = load_embedder(settings, api)
    store = ChromaStore(settings=settings, embedder=embedder, collection=api.api_collection)
    expected = {
        json.loads(line)["id"]
        for line in (settings.data_splits_dir / "rag.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    if set(store.review_ids()) - expected:
        raise ValueError("Index contains IDs outside the registered RAG split")
    splitter = TokenTextSplitter(
        embedder,
        max_tokens=settings.ingestion_chunk_max_tokens,
        overlap_tokens=settings.ingestion_chunk_overlap_tokens,
    )
    report = IngestionPipeline(
        store,
        splitter,
        batch_size=settings.embedding_batch_size,
        max_review_chars=settings.ingestion_max_review_chars,
    ).run(settings.data_splits_dir / "rag.jsonl")
    if report.invalid or report.ignored or set(store.review_ids()) != expected:
        raise ValueError("Incomplete ingestion; initialization marker was not written")


def prepare_index(settings: Settings, api: APISettings, *, builder=build_index) -> bool:
    """Resume interrupted upserts; never silently reset an existing volume."""
    if api.llm_backend == "replay":
        return False  # Recorded context only; no search, embedder or index is needed.
    if api.llm_backend != "fake":
        raise ValueError("CPU image accepts only fake or replay")
    source = settings.data_splits_dir / "rag.jsonl"
    validate_rag_input(source, settings.data_splits_dir)
    identity = {
        "version": "container-index-v1",
        "rag_sha256_lf": file_key(source),
        "manifest_sha256_lf": file_key(settings.data_splits_dir / "manifest.json"),
        "model": settings.embedding_model,
        "prefix": settings.embedding_prefix_mode,
        "collection": api.api_collection or settings.chroma_collection,
        "chunk_max_tokens": settings.ingestion_chunk_max_tokens,
        "chunk_overlap_tokens": settings.ingestion_chunk_overlap_tokens,
        "max_review_chars": settings.ingestion_max_review_chars,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = settings.chroma_path
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "container-index.json"
    with FileLock(str(folder / ".bootstrap.lock"), timeout=60):
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8"))["identity_sha256"] != digest:
                raise ValueError("Index inputs changed; use a new CHROMA_PATH/volume")
            if (folder / "chroma.sqlite3").is_file():
                logger.info("container_index_reused")
                return False
        builder(settings, api)
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(json.dumps({"identity_sha256": digest, **identity}), encoding="utf-8")
        temporary.replace(marker)
        logger.info("container_index_initialized")
        return True


def healthcheck() -> int:
    try:
        port = int(os.environ.get("API_PORT", "8000"))
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
            return 0 if response.status == 200 else 1
    except Exception:
        return 1


def main() -> int:
    if sys.argv[1:] == ["healthcheck"]:
        return healthcheck()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        api = APISettings()
        settings = profile(Settings(), api)
        prepare_index(settings, api)
        port = int(os.environ.get("API_PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid API_PORT")
    except Exception as exc:
        logger.error("container_initialization_failed error_type=%s", type(exc).__name__)
        return 1
    # Separate bootstrap process releases the encoder before the API owns its resources.
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "partner_copilot.api:app",
            "--host",
            os.environ.get("API_HOST", "0.0.0.0"),
            "--port",
            str(port),
            "--workers",
            "1",
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
