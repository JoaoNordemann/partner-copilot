"""Prove API import and fake/replay tests run with heavy dependencies forbidden."""

import os
import subprocess
import sys
from pathlib import Path


def test_api_and_fake_tests_never_import_heavy_dependencies():
    root = Path(__file__).resolve().parents[1]
    source = """
import importlib.abc
import sys
blocked = {'torch', 'transformers', 'sentence_transformers', 'chromadb',
           'bitsandbytes', 'accelerate', 'huggingface_hub'}
class BlockHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked:
            raise AssertionError('Forbidden dependency: ' + fullname)
sys.meta_path.insert(0, BlockHeavy())
from partner_copilot.api import app
assert app is not None
assert not blocked.intersection(sys.modules)
import pytest
result = pytest.main(['tests/test_api.py', 'tests/test_api_replay.py', '-q', '-m', 'not gpu'])
assert result == 0
assert not blocked.intersection(sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env={
            **os.environ,
            "PYTHONPATH": str(root / "src"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "HF_HUB_OFFLINE": "1",
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
