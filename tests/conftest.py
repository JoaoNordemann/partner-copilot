"""Isolate settings from the developer's real environment and secrets."""

import os

import pytest

from partner_copilot.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    keys = {name.upper() for name in Settings.model_fields}
    for name in list(os.environ):
        if name.upper() in keys:
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def pytest_addoption(parser):
    parser.addoption(
        "--run-gpu",
        action="store_true",
        default=False,
        help="Enable explicitly marked real GPU tests; no model downloads",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-gpu"):
        return
    skip = pytest.mark.skip(reason="Real GPU test: enable explicitly with --run-gpu")
    for item in items:
        if "gpu" in item.keywords:
            item.add_marker(skip)
