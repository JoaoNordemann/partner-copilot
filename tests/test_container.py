"""Bootstrap tests use a fake index builder, without Docker or model downloads."""

import json
from pathlib import Path
from unittest.mock import Mock
from urllib.error import URLError

import pytest

from partner_copilot import container
from partner_copilot.api_models import APISettings
from partner_copilot.config import Settings


@pytest.fixture
def setup(tmp_path, monkeypatch):
    split = tmp_path / "splits"
    split.mkdir()
    (split / "rag.jsonl").write_text("{}\n", encoding="utf-8")
    (split / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(container, "validate_rag_input", Mock())
    settings = Settings(_env_file=None, chroma_path=tmp_path / "chroma", data_splits_dir=split)
    api = APISettings(_env_file=None, llm_backend="fake")

    def build(settings, api):
        (settings.chroma_path / "chroma.sqlite3").touch()

    return settings, api, Mock(side_effect=build)


def test_first_start_builds_once_and_restart_reuses(setup):
    settings, api, builder = setup
    assert container.prepare_index(settings, api, builder=builder)
    assert not container.prepare_index(settings, api, builder=builder)
    builder.assert_called_once()
    assert (settings.chroma_path / "container-index.json").is_file()


def test_changed_inputs_are_refused_without_reset(setup):
    settings, api, builder = setup
    container.prepare_index(settings, api, builder=builder)
    (settings.data_splits_dir / "rag.jsonl").write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="inputs changed"):
        container.prepare_index(settings, api, builder=builder)
    assert builder.call_count == 1


def test_failed_initialization_leaves_no_marker_and_can_resume(setup):
    settings, api, builder = setup
    with pytest.raises(RuntimeError):
        container.prepare_index(settings, api, builder=Mock(side_effect=RuntimeError()))
    assert not (settings.chroma_path / "container-index.json").exists()
    assert container.prepare_index(settings, api, builder=builder)


def test_missing_database_is_rebuilt(setup):
    settings, api, builder = setup
    container.prepare_index(settings, api, builder=builder)
    (settings.chroma_path / "chroma.sqlite3").unlink()
    assert container.prepare_index(settings, api, builder=builder)
    assert builder.call_count == 2


def test_replay_needs_no_index_and_real_is_refused(setup):
    settings, _, builder = setup
    replay = APISettings(_env_file=None, llm_backend="replay")
    assert not container.prepare_index(settings, replay, builder=builder)
    builder.assert_not_called()
    with pytest.raises(ValueError, match="only fake or replay"):
        container.prepare_index(settings, APISettings(_env_file=None, llm_backend="real"))


def test_healthcheck_success_and_failure(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=Mock(status=200))
    response.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(container, "urlopen", Mock(return_value=response))
    assert container.healthcheck() == 0
    monkeypatch.setattr(container, "urlopen", Mock(side_effect=URLError("unavailable")))
    assert container.healthcheck() == 1


def test_image_is_nonroot_and_excludes_credentials():
    root = Path(__file__).resolve().parents[1]
    docker = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "USER 10001:10001" in docker and "HEALTHCHECK" in docker
    assert "COPY . " not in docker and "COPY .env" not in docker
    assert "download.pytorch.org/whl/cpu" in docker
    assert not json.loads((root / "configs/replay-catalog.example.json").read_text())["entries"]
