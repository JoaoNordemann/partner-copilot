"""CPU launcher defaults stay explicit and respect external configuration."""

import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_cpu_defaults_and_environment_override(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("API_ALLOW_MODEL_DOWNLOAD", raising=False)
    settings = runpy.run_path(str(ROOT / "scripts/run_mvp.py"))["LocalSettings"]
    assert settings(_env_file=None).llm_backend == "fake"
    assert settings(_env_file=None).api_allow_model_download
    monkeypatch.setenv("LLM_BACKEND", "replay")
    monkeypatch.setenv("API_ALLOW_MODEL_DOWNLOAD", "false")
    assert settings(_env_file=None).llm_backend == "replay"
    assert not settings(_env_file=None).api_allow_model_download


def test_real_backend_is_refused_before_loading_models():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_mvp.py")],
        env={**os.environ, "LLM_BACKEND": "real"},
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "CPU MVP accepts fake/replay" in result.stderr
