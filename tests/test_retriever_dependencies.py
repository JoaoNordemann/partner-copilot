"""Verify the core retriever imports with heavy optional modules explicitly blocked."""

import subprocess
import sys
from pathlib import Path


def test_core_retriever_does_not_import_chroma_or_model_frameworks():
    root = Path(__file__).resolve().parents[1]
    source = """
import importlib.abc
import sys
class BlockHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'chromadb','torch','transformers','sentence_transformers'}:
            raise ImportError('Forbidden dependency: ' + fullname)
sys.meta_path.insert(0, BlockHeavy())
sys.path.insert(0, sys.argv[1])
from partner_copilot.retrieval.retriever import Retriever
from partner_copilot.pipeline import RAGPipeline
class EmptyStore:
    def query(self, text, k, where): return []
class NoLLM:
    def generate(self, prompt): raise AssertionError('LLM must not be called')
assert RAGPipeline(Retriever(EmptyStore()), NoLLM()).ask('entrega', 'rest_001').sources == []
"""
    subprocess.run(
        [sys.executable, "-c", source, str(root / "src")],
        check=True,
        capture_output=True,
        text=True,
    )
