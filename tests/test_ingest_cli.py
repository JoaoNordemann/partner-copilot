import importlib.util
import sys
from pathlib import Path

import pytest

from partner_copilot.config import Settings
from partner_copilot.ingestion import service
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.pipeline import IngestionReport
from partner_copilot.schemas import Review

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ingest_cli", ROOT / "scripts/ingest.py")
assert spec is not None and spec.loader is not None
_cli = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = _cli
spec.loader.exec_module(_cli)


class FixedEmbedder:
    model_name = "test/cli"
    document_prefix = ""
    query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


def review(review_id):
    return Review(
        id=review_id,
        restaurant_id="rest_001",
        text="Entrega atrasou.",
        rating=2,
        created_at="2026-11-01",
        category="pizza",
        bairro="Centro",
    )


def test_cli_overrides_environment_and_passes_all_flags_to_service(monkeypatch, tmp_path):
    received = {}
    monkeypatch.setenv("CHROMA_PATH", "env-database")
    monkeypatch.setenv("EMBEDDING_MODEL", "env-model")

    def run(settings, **kwargs):
        received.update(settings=settings, **kwargs)
        return service.IngestionOutcome(IngestionReport(), "selected", settings.chroma_path, 0)

    monkeypatch.setattr(_cli, "run_ingestion", run)
    result = _cli.main(
        [
            "--input",
            "data.jsonl",
            "--db-path",
            str(tmp_path / "cli-db"),
            "--embedding-model",
            "intfloat/multilingual-e5-small",
            "--batch-size",
            "7",
            "--reset",
        ]
    )
    assert result == 0
    assert received["settings"].chroma_path == tmp_path / "cli-db"
    assert received["settings"].embedding_model == "intfloat/multilingual-e5-small"
    assert received["input_path"] == Path("data.jsonl")
    assert received["batch_size"] == 7 and received["reset"] is True


def test_help_does_not_start_ingestion(monkeypatch, capsys):
    monkeypatch.setattr(_cli, "run_ingestion", lambda *a, **k: pytest.fail("Must not ingest"))
    with pytest.raises(SystemExit) as exc:
        _cli.main(["--help"])
    assert exc.value.code == 0
    assert "--db-path" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["--batch-size", "0"], ["--model", " ", "--reset"]])
def test_invalid_cli_arguments_do_not_reach_service(monkeypatch, arguments):
    monkeypatch.setattr(_cli, "run_ingestion", lambda *a, **k: pytest.fail("Must not ingest"))
    with pytest.raises(SystemExit) as exc:
        _cli.main(arguments)
    assert exc.value.code == 2


def test_bad_input_is_rejected_before_store_creation_even_with_reset(monkeypatch):
    monkeypatch.setattr(service, "_create_store", lambda *_: pytest.fail("Must not open database"))
    settings = Settings(data_splits_dir=ROOT / "data/splits")
    with pytest.raises(service.IngestionPreflightError, match="registered rag split"):
        service.run_ingestion(settings, input_path=ROOT / "data/raw/reviews.jsonl", reset=True)


@pytest.fixture
def context(monkeypatch, tmp_path):
    events = []
    settings = Settings(chroma_path=tmp_path / "database", embedding_model="test/cli")
    store = ChromaStore(settings=settings, collection="selected", embedder=FixedEmbedder())
    other = ChromaStore(settings=settings, collection="other", embedder=FixedEmbedder())
    store.upsert([review("old")])
    other.upsert([review("other_id")])
    path = tmp_path / "source.jsonl"
    path.write_text(review("new").model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.setattr(service, "validate_rag_input", lambda *a: events.append("validate"))
    monkeypatch.setattr(
        service, "validate_rag_collection_ids", lambda *a: events.append("membership")
    )

    def create_store(_):
        events.append("open_store")
        return store

    monkeypatch.setattr(service, "_create_store", create_store)
    original_reset = store.reset

    def reset():
        events.append("reset")
        return original_reset()

    monkeypatch.setattr(store, "reset", reset)

    class Splitter:
        def __init__(self, *args, **kwargs):
            pass

        def prepare(self):
            events.append("prepare_model")

        def split(self, text):
            return [text]

    monkeypatch.setattr(service, "TokenTextSplitter", Splitter)
    return settings, store, other, path, events


def test_reset_is_scoped_and_occurs_only_after_preflight(context):
    settings, store, other, path, events = context
    outcome = service.run_ingestion(settings, input_path=path, reset=True, batch_size=1)
    assert events[:4] == ["validate", "open_store", "prepare_model", "reset"]
    assert outcome.reset_removed == 1 and outcome.report.inserted == 1
    assert store.review_ids() == ["new"] and other.review_ids() == ["other_id"]
    again = service.run_ingestion(settings, input_path=path, reset=False)
    assert again.reset_removed == 0 and again.report.updated == 1 and store.count() == 1


def test_model_preparation_failure_does_not_delete_data(monkeypatch, context):
    settings, store, other, path, events = context

    class UnavailableModel:
        def __init__(self, *args, **kwargs):
            pass

        def prepare(self):
            raise OSError("model unavailable")

    monkeypatch.setattr(service, "TokenTextSplitter", UnavailableModel)
    with pytest.raises(OSError, match="model unavailable"):
        service.run_ingestion(settings, input_path=path, reset=True)
    assert "reset" not in events
    assert store.review_ids() == ["old"] and other.count() == 1


def test_without_reset_foreign_collection_ids_still_block_ingestion(monkeypatch, context):
    settings, store, _, path, events = context

    def reject(*args):
        raise ValueError("outside the RAG split")

    monkeypatch.setattr(service, "validate_rag_collection_ids", reject)
    with pytest.raises(service.IngestionPreflightError, match="outside"):
        service.run_ingestion(settings, input_path=path)
    assert "reset" not in events and store.review_ids() == ["old"]


def test_runtime_failure_returns_nonzero_exit_code(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(_cli, "run_ingestion", fail)
    assert _cli.main([]) == 1
