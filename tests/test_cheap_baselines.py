import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_baselines_match_recorded_comparison():
    report = json.loads(
        (ROOT / "reports/human-v2/cheap-baselines.json").read_text(encoding="utf-8")
    )
    comparison = json.loads(
        (ROOT / "reports/human-v2/retrieval-comparison-unfiltered-check.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["snapshot_sha256_lf"] == comparison["snapshot_sha256_lf"]
    assert not report["model_loaded"] and report["random_repetitions"] == 200
    for method in ("keyword", "random"):
        assert report["methods"][method] == comparison["methods"][method]


def test_cheap_baselines_run_with_model_frameworks_and_chroma_blocked(tmp_path):
    source = """
import importlib.abc
import runpy
import sys
class BlockModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','transformers','sentence_transformers','chromadb'}:
            raise ImportError('Forbidden: ' + fullname)
sys.meta_path.insert(0, BlockModels())
root, output = sys.argv[1:]
sys.path.insert(0, root + '/src')
sys.argv = [root + '/scripts/evaluate_cheap_baselines.py', '--eval-dir',
            root + '/data/eval/human-v2', '--output', output]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    output = tmp_path / "baselines.json"
    subprocess.run(
        [sys.executable, "-c", source, str(ROOT), str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert not report["model_loaded"]
    assert set(report["methods"]) == {"keyword", "random"}
