import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from partner_copilot.config import Settings
from partner_copilot.generation import provider
from partner_copilot.generation.contracts import GenerationContractError
from partner_copilot.pipeline import RAGPipeline


def test_provider_loads_once_even_for_concurrent_first_requests(monkeypatch):
    constructor = Mock()
    monkeypatch.setitem(
        sys.modules, "partner_copilot.generation.llm", SimpleNamespace(Mistral4bit=constructor)
    )
    monkeypatch.setattr(provider, "_instance", None)
    monkeypatch.setattr(provider, "_configuration", None)
    settings = Settings()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: provider.get_llm(settings), range(8)))
    constructor.assert_called_once_with(settings=settings)
    assert all(result is results[0] for result in results)
    with pytest.raises(GenerationContractError, match="restart"):
        provider.get_llm(Settings(temperature=0.1))


def test_pipeline_empty_retrieval_does_not_load_the_model(monkeypatch):
    retriever = Mock()
    retriever.retrieve.return_value = []
    loader = Mock()
    monkeypatch.setattr("partner_copilot.pipeline.get_llm", loader)
    answer = RAGPipeline(retriever).ask("Pergunta", "rest_fixture")
    assert answer.abstained and answer.metadata.generation is None
    loader.assert_not_called()


def test_pipeline_carries_per_request_measurements_on_llm_abstention():
    from partner_copilot.generation.contracts import (
        ABSTENTION_MARKER,
        GenerationMetrics,
        GenerationResult,
        MeasuredLLM,
    )
    from partner_copilot.schemas import RetrievedDoc, Review

    metrics = GenerationMetrics(
        latency_ms=20,
        model_load_latency_ms=100,
        prompt_tokens=12,
        generated_tokens=2,
        max_new_tokens=16,
        context_window_tokens=128,
        context_margin_tokens=8,
        seed=42,
        temperature=0,
        do_sample=False,
        compute_dtype="float16",
        vram_baseline_allocated_bytes=None,
        vram_peak_allocated_bytes=None,
        vram_peak_reserved_bytes=None,
    )

    class MeasuredFake(MeasuredLLM):
        def generate_with_metrics(self, user_prompt, max_new_tokens=None):
            return GenerationResult(ABSTENTION_MARKER, metrics)

    retriever = Mock()
    retriever.retrieve.return_value = [
        RetrievedDoc(
            review=Review(
                id="fonte_a",
                restaurant_id="rest_fixture",
                text="O adesivo se soltou.",
                rating=2,
                created_at="2026-01-15",
                category="teste",
                bairro="Teste",
            ),
            score=0.8,
        )
    ]
    answer = RAGPipeline(retriever, MeasuredFake()).ask("Pergunta", "rest_fixture")
    assert answer.abstained and answer.abstention_reason == "llm_insufficient_evidence"
    assert answer.metadata.generation == metrics
    assert answer.metadata.model_dump()["generation"]["prompt_tokens"] == 12
