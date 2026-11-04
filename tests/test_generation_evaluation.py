from pathlib import Path

import pytest

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.evaluation.generation import run_generation, summarize_generation
from partner_copilot.generation.contracts import (
    ABSTENTION_MARKER,
    GenerationMetrics,
    GenerationResult,
    MeasuredLLM,
)
from partner_copilot.schemas import RetrievedDoc

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/eval/human-v2"


class FakeRetriever:
    def __init__(self, questions, corpus):
        self.questions = {q.pergunta: q for q in questions}
        self.corpus = {r.id: r for r in corpus}
        self.calls = 0

    def retrieve(self, query, restaurant_id, aspect=None, **filters):
        self.calls += 1
        q = self.questions[query]
        if q.id in {"q29", "q30"}:
            return []
        review = (
            self.corpus[q.relevantes[0]]
            if q.relevantes
            else next(r for r in self.corpus.values() if q.filtros.matches(r))
        )
        return [RetrievedDoc(review=review, score=0.8)]


class FakeLLM(MeasuredLLM):
    def __init__(self):
        self.calls = 0

    def generate_with_metrics(self, prompt, max_new_tokens=None):
        self.calls += 1
        return GenerationResult(
            ABSTENTION_MARKER,
            GenerationMetrics(
                latency_ms=1,
                model_load_latency_ms=1,
                prompt_tokens=10,
                generated_tokens=2,
                max_new_tokens=400,
                context_window_tokens=32768,
                context_margin_tokens=256,
                seed=42,
                temperature=0,
                do_sample=False,
                compute_dtype="float16",
                vram_baseline_allocated_bytes=None,
                vram_peak_allocated_bytes=None,
                vram_peak_reserved_bytes=None,
            ),
        )


def test_full_trace_raw_output_resume_and_secret_exclusion(tmp_path):
    questions, corpus, _ = load_eval_set(FOLDER)
    retriever = FakeRetriever(questions, corpus)
    llm = FakeLLM()
    output = tmp_path / "results.jsonl"
    settings = Settings(hf_token="secret-not-for-output")
    rows = run_generation(
        FOLDER, output, settings, retriever, lambda: llm, environment={"test": True}
    )
    assert len(rows) == 30 and llm.calls == 28
    assert all(row["backend"] == "test_double" for row in rows)
    assert rows[0]["raw_response"] == ABSTENTION_MARKER and rows[0]["rendered_prompt"]
    assert rows[0]["retrieved"][0]["text"]
    assert "secret-not-for-output" not in output.read_text(encoding="utf-8")
    before = output.read_bytes()
    retriever.calls = 0
    resumed = run_generation(
        FOLDER,
        output,
        settings,
        retriever,
        lambda: pytest.fail("Must not reload"),
        environment={"test": True},
        resume=True,
    )
    assert len(resumed) == 30 and retriever.calls == 0 and output.read_bytes() == before
    with pytest.raises(ValueError, match="identity"):
        run_generation(
            FOLDER,
            output,
            Settings(temperature=0.1),
            retriever,
            lambda: llm,
            environment={"test": True},
            resume=True,
        )
    summary = summarize_generation(rows)
    assert summary["negative_abstention"] == {"numerator": 6, "denominator": 6, "rate": 1.0}
    assert summary["positive_undue_abstention"]["numerator"] == 24
    assert summary["hard_negative_llm_calls"] == 4
    assert summary["citation_scope_valid"]["denominator"] == 0
    assert not summary["manual_review_completed"]
    assert summarize_generation(rows[:5])["negative_abstention"]["rate"] is None


def test_invalid_citations_preserve_raw_and_are_included_in_metrics(tmp_path):
    questions, corpus, _ = load_eval_set(FOLDER)

    class WrongCitation(FakeLLM):
        def generate_with_metrics(self, prompt, max_new_tokens=None):
            result = super().generate_with_metrics(prompt, max_new_tokens)
            return GenerationResult("Afirmação [inventada].", result.metrics)

    rows = run_generation(
        FOLDER,
        tmp_path / "errors.jsonl",
        Settings(),
        FakeRetriever(questions, corpus),
        WrongCitation,
        environment={"test": True},
    )
    assert rows[0]["raw_response"] == "Afirmação [inventada]."
    assert rows[0]["error"]["code"] == "invalid_citation"
    assert rows[0]["generation_metrics"]["prompt_tokens"] == 10
    summary = summarize_generation(rows)
    assert summary["errors"]["invalid_citation"] == 28
    assert summary["citation_scope_valid"] == {"numerator": 0, "denominator": 28, "rate": 0.0}
    assert summary["negative_abstention"]["numerator"] == 2


def test_interruption_retains_prefix_and_resumes_remaining_questions(tmp_path):
    questions, corpus, _ = load_eval_set(FOLDER)

    class Interrupted(FakeLLM):
        def generate_with_metrics(self, prompt, max_new_tokens=None):
            if self.calls == 2:
                raise KeyboardInterrupt()
            return super().generate_with_metrics(prompt, max_new_tokens)

    output = tmp_path / "interrupted.jsonl"
    with pytest.raises(KeyboardInterrupt):
        run_generation(
            FOLDER,
            output,
            Settings(),
            FakeRetriever(questions, corpus),
            Interrupted,
            environment={"test": True},
        )
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
    llm = FakeLLM()
    rows = run_generation(
        FOLDER,
        output,
        Settings(),
        FakeRetriever(questions, corpus),
        lambda: llm,
        environment={"test": True},
        resume=True,
    )
    assert len(rows) == 30 and llm.calls == 26
    assert len({r["question_id"] for r in rows}) == 30
