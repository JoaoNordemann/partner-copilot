"""Frozen ten-question verification for structured output, without corrective retries."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import QueryFilters, text_hash
from partner_copilot.evaluation.generation import RecordingLLM, RecordingRetriever, experiment
from partner_copilot.evaluation.journal import QuestionJournal
from partner_copilot.generation.contracts import (
    GenerationContractError,
    InvalidCitationError,
    MeasuredLLM,
)
from partner_copilot.generation.output_json_v1 import inspect_generation
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.schemas import RetrievedDoc, Review


class VerificationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^n[0-9]{2}$")
    pergunta: str = Field(min_length=1)
    filtros: QueryFilters
    relevantes: list[str]
    deve_abster: bool
    criterio: str = Field(min_length=1)


def load_verification(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    corpus_path = folder / manifest["corpus_relative_path"]
    if (
        text_hash(folder / "questions.jsonl") != manifest["questions_sha256_lf"]
        or text_hash(corpus_path) != manifest["corpus_sha256_lf"]
    ):
        raise ValueError("Verification snapshot checksum differs")
    prompt = load_prompt_template(manifest["prompt_version"])
    if hashlib.sha256(prompt.encode()).hexdigest() != manifest["prompt_sha256"]:
        raise ValueError("Frozen verification prompt differs")
    questions = [
        VerificationQuestion.model_validate_json(line)
        for line in (folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    corpus = [
        Review.model_validate_json(line)
        for line in corpus_path.read_text(encoding="utf-8").splitlines()
    ]
    if [q.id for q in questions] != [f"n{i:02}" for i in range(1, 11)] or sum(
        q.deve_abster for q in questions
    ) != 3:
        raise ValueError("Requires ten ordered questions with three negatives")
    reviews = {r.id: r for r in corpus}
    if len(reviews) != len(corpus):
        raise ValueError("Duplicate corpus IDs")
    for q in questions:
        if q.deve_abster != (not q.relevantes) or len(set(q.relevantes)) != len(q.relevantes):
            raise ValueError("Question labels inconsistent")
        if any(
            identifier not in reviews or not q.filtros.matches(reviews[identifier])
            for identifier in q.relevantes
        ):
            raise ValueError("Relevant ID outside corpus or scope")
    return questions, corpus, manifest


def run_structured_verification(
    folder: Path,
    output: Path,
    settings: Settings,
    retriever,
    llm_factory: Callable[[], MeasuredLLM],
    *,
    environment: dict,
    backend: str = "test_double",
    resume: bool = False,
):
    questions, corpus, manifest = load_verification(folder)
    reviews = {review.id: review for review in corpus}
    if (
        settings.prompt_version != manifest["prompt_version"]
        or settings.parser_version != manifest["parser_version"]
    ):
        raise ValueError("Use the frozen structured prompt/parser pair")
    snapshot = {
        "file_sha256_lf": {
            "questions": manifest["questions_sha256_lf"],
            "corpus": manifest["corpus_sha256_lf"],
        }
    }
    identity = experiment(settings, snapshot, environment, backend)
    identity["verification_version"] = manifest["version"]
    identity["experiment_id"] = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()
    trace = {}
    pipeline = RAGPipeline(
        RecordingRetriever(retriever, trace, settings),
        RecordingLLM(llm_factory, trace),
        settings=settings,
    )
    with QuestionJournal(
        output, identity["experiment_id"], [q.id for q in questions], resume=resume
    ) as journal:
        for q in questions[len(journal.records) :]:
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
                answer = pipeline.ask(q.pergunta, **q.filtros.model_dump(exclude_none=True))
            except Exception as exc:
                code = (
                    "invalid_citation"
                    if isinstance(exc, InvalidCitationError)
                    else "schema_or_contract_error"
                    if isinstance(exc, GenerationContractError)
                    else "runtime_error"
                )
                error = {"code": code, "type": type(exc).__name__}
                fatal = trace["stage"] == "model_load" or code == "runtime_error"
            # Membership diagnostics need IDs only; no labels are sent back to the model.
            docs = [
                RetrievedDoc(review=reviews[d["review_id"]], score=d["score"])
                for d in trace["context"]
            ]
            diagnostics = (
                inspect_generation(trace["raw_response"], docs)
                if trace["llm_called"]
                else {
                    "schema_valid": None,
                    "abstained": None,
                    "ids_in_context": None,
                    "parser_accepted": None,
                    "content_supported": None,
                }
            )
            row = {
                **identity,
                "question_id": q.id,
                "pergunta": q.pergunta,
                "filtros": q.filtros.model_dump(mode="json", exclude_none=True),
                "deve_abster": q.deve_abster,
                "relevant_ids": q.relevantes,
                **trace,
                "context_ids": [d["review_id"] for d in trace["context"]],
                "retrieved_ids": [d["review_id"] for d in trace["retrieved"]],
                "answer": answer.model_dump() if answer else None,
                "error": error,
                "status": "ok" if error is None else "error",
                "diagnostics": diagnostics,
                "latency_ms": (perf_counter() - started) * 1000,
                "corrective_calls": 0,
            }
            journal.append(row)
            if fatal:
                raise RuntimeError("Runtime failure saved; resolve before resuming")
        return journal.records.copy()


def summarize_structured(rows: list[dict]):
    ids = [r["question_id"] for r in rows]
    if len(set(ids)) != len(ids) or not set(ids) <= {f"n{i:02}" for i in range(1, 11)}:
        raise ValueError("Invalid verification IDs")
    complete = len(rows) == 10
    calls = [r for r in rows if r["llm_called"]]
    id_cases = [
        r for r in calls if r["diagnostics"]["schema_valid"] and not r["diagnostics"]["abstained"]
    ]

    def fraction(n, d):
        return {"numerator": n, "denominator": d, "rate": n / d if complete and d else None}

    def abstained(row):
        return bool(row["answer"] and row["answer"]["abstained"])

    negatives = [r for r in rows if r["deve_abster"]]
    positives = [r for r in rows if not r["deve_abster"]]
    negative_calls = [r for r in negatives if r["llm_called"]]
    return {
        "complete": complete,
        "questions": len(rows),
        "llm_calls": len(calls),
        "schema_valid": fraction(sum(r["diagnostics"]["schema_valid"] for r in calls), len(calls)),
        "ids_in_context": fraction(
            sum(r["diagnostics"]["ids_in_context"] for r in id_cases), len(id_cases)
        ),
        "correct_negative_abstention": fraction(sum(abstained(r) for r in negatives), 3),
        "negative_llm_calls": len(negative_calls),
        "correct_negative_llm_abstention": fraction(
            sum(abstained(r) for r in negative_calls), len(negative_calls)
        ),
        "retriever_empty_abstentions": sum(
            bool(r["answer"] and r["answer"].get("abstention_reason") == "retriever_empty")
            for r in rows
        ),
        "undue_positive_abstention": fraction(sum(abstained(r) for r in positives), 7),
        "parser_accepted_llm": sum(bool(r["diagnostics"]["parser_accepted"]) for r in calls),
        "errors": sum(r["error"] is not None for r in rows),
        "context_evidence_positive": fraction(
            sum(bool(set(r["relevant_ids"]) & set(r["context_ids"])) for r in positives), 7
        ),
        "content_supported": None,
        "factual_review_completed": False,
        "review_ids": ids,
        "corrective_calls": 0,
    }
