"""Full RAG generation attempts, raw traces and conservative summary metrics."""

import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import load_eval_set
from partner_copilot.evaluation.journal import QuestionJournal
from partner_copilot.generation.contracts import (
    ABSTENTION_MARKER,
    GenerationContractError,
    GenerationResult,
    InvalidCitationError,
    MeasuredLLM,
)
from partner_copilot.generation.prompts import build_prompt, load_prompt_template
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.retrieval.retriever import Retriever

PUBLIC_SETTINGS = (
    "embedding_model",
    "embedding_device",
    "embedding_prefix_mode",
    "embedding_batch_size",
    "llm_model_id",
    "retrieval_k",
    "retrieval_min_score",
    "context_k",
    "max_new_tokens",
    "temperature",
    "top_p",
    "generation_seed",
    "generation_context_margin_tokens",
    "prompt_version",
)


def experiment(settings: Settings, manifest: dict, environment: dict, backend: str) -> dict:
    template = load_prompt_template(settings.prompt_version)
    value = {
        "schema_version": 1,
        "backend": backend,
        "settings": {name: getattr(settings, name) for name in PUBLIC_SETTINGS},
        "snapshot_sha256_lf": manifest["file_sha256_lf"],
        "prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
        "prompt_version": settings.prompt_version,
        "environment": environment,
    }
    value["experiment_id"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def _document(doc) -> dict:
    review = doc.review
    return {
        "review_id": review.id,
        "document_id": doc.document_id,
        "text": review.text,
        "restaurant_id": review.restaurant_id,
        "item": review.item,
        "created_at": review.created_at.isoformat(),
        "score": doc.score,
        "chunk_index": doc.chunk_index,
        "chunk_count": doc.chunk_count,
    }


class RecordingRetriever:
    def __init__(self, retriever, trace, settings):
        self.retriever, self.trace, self.settings = retriever, trace, settings

    def retrieve(self, *args, **kwargs):
        self.trace["stage"] = "retrieval"
        docs = self.retriever.retrieve(*args, **kwargs)
        context = docs[: self.settings.context_k]
        self.trace["retrieved"] = [_document(doc) for doc in docs]
        self.trace["context"] = [_document(doc) for doc in context]
        if context:
            self.trace["rendered_prompt"] = build_prompt(
                args[0], context, prompt_version=self.settings.prompt_version
            )
        return docs


class RecordingLLM(MeasuredLLM):
    def __init__(self, factory: Callable[[], MeasuredLLM], trace: dict):
        self.factory, self.trace, self.instance = factory, trace, None

    def generate_with_metrics(self, user_prompt, max_new_tokens=None) -> GenerationResult:
        if self.instance is None:
            self.trace["stage"] = "model_load"
            self.instance = self.factory()
        self.trace["stage"] = "generation"
        self.trace["llm_called"] = True
        result = self.instance.generate_with_metrics(user_prompt, max_new_tokens)
        self.trace["raw_response"] = result.text
        self.trace["generation_metrics"] = result.metrics.model_dump()
        self.trace["stage"] = "validation"
        return result


def run_generation(
    folder: Path,
    output: Path,
    settings: Settings,
    retriever: Retriever,
    llm_factory: Callable[[], MeasuredLLM],
    *,
    environment: dict,
    backend: str = "test_double",
    resume: bool = False,
) -> list[dict]:
    questions, _, manifest = load_eval_set(folder)
    identity = experiment(settings, manifest, environment, backend)
    trace = {}
    recording = RecordingLLM(llm_factory, trace)
    pipeline = RAGPipeline(
        RecordingRetriever(retriever, trace, settings), recording, settings=settings
    )
    with QuestionJournal(
        output, identity["experiment_id"], [q.id for q in questions], resume=resume
    ) as journal:
        for question in questions[len(journal.records) :]:
            trace.clear()
            trace.update(
                stage="retrieval",
                retrieved=[],
                context=[],
                rendered_prompt=None,
                raw_response=None,
                llm_called=False,
                generation_metrics=None,
            )
            started = perf_counter()
            answer, error = None, None
            fatal = False
            try:
                answer = pipeline.ask(
                    question.pergunta, **question.filtros.model_dump(exclude_none=True)
                )
            except Exception as exc:
                code = (
                    "invalid_citation"
                    if isinstance(exc, InvalidCitationError)
                    else "generation_contract_error"
                    if isinstance(exc, GenerationContractError)
                    else "runtime_error"
                )
                message = str(exc)
                if settings.hf_token:
                    message = message.replace(settings.hf_token.get_secret_value(), "[REDACTED]")
                message = re.sub(r"hf_[A-Za-z0-9]{20,}", "[REDACTED]", message)
                error = {"code": code, "type": type(exc).__name__, "message": message}
                if isinstance(exc, InvalidCitationError):
                    error.update(
                        invalid_ids=list(exc.invalid_ids),
                        invalid_citation_count=exc.invalid_citation_count,
                    )
                fatal = trace["stage"] == "model_load" or type(exc).__name__ == "OutOfMemoryError"
            row = {
                **identity,
                "question_id": question.id,
                "pergunta": question.pergunta,
                "tipo": question.tipo,
                "filtros": question.filtros.model_dump(mode="json", exclude_none=True),
                "deve_abster": question.deve_abster,
                "relevant_ids": question.relevantes,
                **trace,
                "status": "ok" if error is None else "error",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "retrieved_ids": [doc["review_id"] for doc in trace["retrieved"]],
                "context_ids": [doc["review_id"] for doc in trace["context"]],
                "answer": answer.model_dump() if answer else None,
                "error": error,
                "latency_ms": (perf_counter() - started) * 1000,
            }
            journal.append(row)
            if fatal:
                raise RuntimeError("Fatal generation failure recorded; resolve it before resuming")
        return journal.records.copy()


def summarize_generation(rows: list[dict]) -> dict:
    expected = 30
    ids = [row["question_id"] for row in rows]
    allowed = {f"q{i:02}" for i in range(1, 31)}
    if len(ids) != len(set(ids)) or not set(ids) <= allowed:
        raise ValueError("Summary requires unique IDs from the 30-question protocol")
    complete = len(rows) == expected and len({r["question_id"] for r in rows}) == expected
    negative = [r for r in rows if r["deve_abster"]]
    positive = [r for r in rows if not r["deve_abster"]]
    hard = [r for r in rows if r["question_id"] in {"q25", "q26", "q27", "q28"}]

    def abstained(row):
        return bool(row["answer"] and row["answer"]["abstained"])

    def fraction(n, d):
        return {"numerator": n, "denominator": d, "rate": n / d if complete and d else None}

    candidates = [
        r
        for r in rows
        if r["llm_called"]
        and r["raw_response"] is not None
        and r["raw_response"].strip() != ABSTENTION_MARKER
    ]
    valid_citations = 0
    for row in candidates:
        citations = re.findall(r"\[([^\[\]\r\n]+)\]", row["raw_response"])
        allowed = {doc["review_id"] for doc in row["context"]}
        valid_citations += bool(citations) and all(citation in allowed for citation in citations)
    return {
        "complete": complete,
        "completed_questions": len(rows),
        "expected_questions": expected,
        "backend": rows[0]["backend"] if rows else None,
        "negative_abstention": fraction(sum(abstained(r) for r in negative), 6),
        "hard_negative_abstention": fraction(sum(abstained(r) for r in hard), 4),
        "hard_negative_llm_calls": sum(r["llm_called"] for r in hard),
        "hard_negative_llm_abstention": fraction(
            sum(
                abstained(r) and r["answer"]["abstention_reason"] == "llm_insufficient_evidence"
                for r in hard
            ),
            sum(r["llm_called"] for r in hard),
        ),
        "negative_answers_without_abstention": sum(
            r["answer"] is not None and not abstained(r) for r in negative
        ),
        "positive_answers_without_abstention": sum(
            r["answer"] is not None and not abstained(r) for r in positive
        ),
        "negative_errors": sum(r["error"] is not None for r in negative),
        "positive_errors": sum(r["error"] is not None for r in positive),
        "positive_undue_abstention": fraction(sum(abstained(r) for r in positive), 24),
        "citation_scope_valid": fraction(valid_citations, len(candidates)),
        "errors": {
            code: sum(r["error"] is not None and r["error"]["code"] == code for r in rows)
            for code in ["invalid_citation", "generation_contract_error", "runtime_error"]
        },
        "negative_abstention_reasons": {
            reason: sum(
                abstained(r) and r["answer"]["abstention_reason"] == reason for r in negative
            )
            for reason in ["retriever_empty", "llm_insufficient_evidence"]
        },
        "manual_review_ids": ["q01", "q09", "q13", "q22", "q25", "q26", "q27", "q28", "q29", "q30"],
        "manual_review_completed": False,
    }
