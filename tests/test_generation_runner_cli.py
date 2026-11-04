"""CLI preparation checks do not load model weights or write fake evaluation results."""

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_only_validates_dataset_without_writing_questions(tmp_path):
    output = tmp_path / "questions.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_generation.py"),
            "--eval-dir",
            str(ROOT / "data/eval/human-v2"),
            "--output",
            str(output),
            "--check-only",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    value = json.loads(result.stdout)
    assert value["questions"] == 30 and value["corpus"] == 100
    assert not output.exists()


def test_notebook_is_parseable_and_has_no_outputs_or_literal_tokens():
    notebook = json.loads((ROOT / "notebooks/generation_eval.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert len({cell["id"] for cell in notebook["cells"]}) == len(notebook["cells"])
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
            assert not cell["outputs"] and cell["execution_count"] is None
    source = json.dumps(notebook)
    assert "userdata.get('HF_TOKEN')" in source
    assert "--resume" in source and "/content/drive/MyDrive/" in source

    assert not re.search(r"(?:hf_|ghp_|github_pat_)[A-Za-z0-9_]{20,}", source)
