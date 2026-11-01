import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from partner_copilot.config import Settings, get_settings


def test_defaults():
    settings = Settings()
    assert settings.retrieval_k == 8
    assert settings.data_raw_dir == Path("data/raw")
    assert settings.hf_token is None


def test_env_overrides_dotenv_and_parses_types(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "RETRIEVAL_K=12\nCHROMA_PATH=custom/index\nUNRELATED=value\n", encoding="utf-8"
    )
    assert Settings().retrieval_k == 12
    monkeypatch.setenv("RETRIEVAL_K", "4")
    settings = Settings()
    assert settings.retrieval_k == 4
    assert settings.chroma_path == Path("custom/index")
    assert Settings(retrieval_k=6).retrieval_k == 6


@pytest.mark.parametrize(
    "name,value",
    [
        ("retrieval_k", 0),
        ("retrieval_k", 51),
        ("retrieval_min_score", -0.1),
        ("retrieval_min_score", 1.1),
        ("max_new_tokens", 15),
        ("max_new_tokens", 2049),
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("top_p", 0),
        ("top_p", 1.1),
    ],
)
def test_numeric_validation(name, value):
    with pytest.raises(ValidationError):
        Settings(**{name: value})


def test_invalid_environment_value(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_K", "invalid")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "name",
    ["ab", "a" * 64, "-reviews", "reviews_", "bad name", "a/b", "a..b", "127.0.0.1", "avaliações"],
)
def test_invalid_collection(name):
    with pytest.raises(ValidationError):
        Settings(chroma_collection=name)


@pytest.mark.parametrize("name", ["reviews", "reviews-v2", "reviews_2026", "reviews.v2"])
def test_valid_collection(name):
    assert Settings(chroma_collection=name).chroma_collection == name


def test_token_is_secret_and_required_only_when_requested(monkeypatch):
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        Settings().require_hf_token()
    monkeypatch.setenv("HF_TOKEN", "placeholder")
    monkeypatch.delenv("HF_TOKEN")
    settings = Settings(hf_token="fake-test-token")
    assert "fake-test-token" not in repr(settings)
    assert settings.require_hf_token() == "fake-test-token"
    settings.export_hf_env()
    assert os.environ["HF_TOKEN"] == "fake-test-token"
    monkeypatch.setenv("HF_TOKEN", "existing-test-token")
    settings.export_hf_env()
    assert os.environ["HF_TOKEN"] == "existing-test-token"


def test_get_settings_caches(monkeypatch):
    first = get_settings()
    monkeypatch.setenv("RETRIEVAL_K", "3")
    assert get_settings() is first
    get_settings.cache_clear()
    assert get_settings().retrieval_k == 3


def test_blank_token_is_missing(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "")
    settings = Settings()
    assert settings.hf_token is None
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        settings.require_hf_token()
