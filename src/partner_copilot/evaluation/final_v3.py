"""Frozen final V3 check: new n11-n20 first, contaminated q01-q30 separately."""

import hashlib
import json
from pathlib import Path
from time import perf_counter

from partner_copilot.config import MISTRAL_INSTRUCT_MODEL, MULTILINGUAL_MINILM_MODEL, Settings
from partner_copilot.evaluation.dataset import load_eval_set, text_hash
from partner_copilot.evaluation.generation import RecordingLLM, RecordingRetriever, experiment
from partner_copilot.evaluation.journal import QuestionJournal
from partner_copilot.evaluation.structured import VerificationQuestion
from partner_copilot.generation.contracts import GenerationContractError, InvalidCitationError
from partner_copilot.generation.output import parser_identity
from partner_copilot.generation.output_v3 import inspect_generation
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.schemas import RetrievedDoc, Review


def final_settings() -> Settings:
    return Settings(
        prompt_version="partner-copilot-v3",
        parser_version="parser-v3",
        retrieval_k=8,
        retrieval_min_score=0.25,
        context_k=8,
        temperature=0,
        generation_seed=42,
        max_new_tokens=512,
        top_p=0.9,
        generation_context_margin_tokens=256,
        embedding_model=MULTILINGUAL_MINILM_MODEL,
        embedding_device="cpu",
        embedding_batch_size=32,
        embedding_prefix_mode="auto",
        llm_model_id=MISTRAL_INSTRUCT_MODEL,
    )


def load_final_set(cohort: str, folder: Path, old_folder: Path):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    corpus_path = folder / manifest["corpus_relative_path"]
    if (
        text_hash(folder / "questions.jsonl") != manifest["questions_sha256_lf"]
        or text_hash(corpus_path) != manifest["corpus_sha256_lf"]
    ):
        raise ValueError("Frozen final dataset changed")
    if (
        hashlib.sha256(load_prompt_template(manifest["prompt_version"]).encode()).hexdigest()
        != manifest["prompt_sha256"]
    ):
        raise ValueError("Frozen final prompt changed")
    parser_identity(manifest["parser_version"])
    for filename, digest in manifest["parser_sha256_files"].items():
        path = Path(__file__).resolve().parents[1] / "generation" / filename
        if text_hash(path) != digest:
            raise ValueError("Frozen final parser changed")
    if cohort == "contaminated":
        questions, corpus, old_manifest = load_eval_set(old_folder)
        snapshot = old_manifest["file_sha256_lf"]
    elif cohort == "new":
        questions = [
            VerificationQuestion.model_validate_json(line)
            for line in (folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        corpus = [
            Review.model_validate_json(line)
            for line in corpus_path.read_text(encoding="utf-8").splitlines()
        ]
        if [q.id for q in questions] != [f"n{i:02}" for i in range(11, 21)] or sum(
            q.deve_abster for q in questions
        ) != 3:
            raise ValueError("Final set must contain n11-n20 and three negatives")
        snapshot = {
            "questions": manifest["questions_sha256_lf"],
            "corpus": manifest["corpus_sha256_lf"],
        }
    else:
        raise ValueError("Unknown cohort")
    by_id = {r.id: r for r in corpus}
    if len(by_id) != len(corpus):
        raise ValueError("Duplicate corpus ID")
    for q in questions:
        if q.deve_abster != (not q.relevantes) or len(set(q.relevantes)) != len(q.relevantes):
            raise ValueError("Inconsistent labels")
        if any(
            identifier not in by_id or not q.filtros.matches(by_id[identifier])
            for identifier in q.relevantes
        ):
            raise ValueError("Relevant document outside scope")
    return questions, corpus, manifest, snapshot


def run_final_v3(
    cohort: str,
    output: Path,
    folder: Path,
    old_folder: Path,
    settings: Settings,
    retriever,
    llm_factory,
    *,
    environment: dict,
    backend: str = "test_double",
    resume: bool = False,
):
    questions, corpus, manifest, snapshot = load_final_set(cohort, folder, old_folder)
    if (
        settings.prompt_version != manifest["prompt_version"]
        or settings.parser_version != manifest["parser_version"]
    ):
        raise ValueError("Wrong frozen prompt/parser")
    expected = final_settings()
    for name in (
        "retrieval_k",
        "retrieval_min_score",
        "context_k",
        "temperature",
        "generation_seed",
        "max_new_tokens",
        "top_p",
        "llm_model_id",
        "embedding_model",
        "embedding_device",
        "embedding_batch_size",
        "embedding_prefix_mode",
        "generation_context_margin_tokens",
    ):
        if getattr(settings, name) != getattr(expected, name):
            raise ValueError("Final settings differ: " + name)
    by_id = {review.id: review for review in corpus}
    identity = {
        **experiment(settings, {"file_sha256_lf": snapshot}, environment, backend),
        "cohort": cohort,
        "contaminated": cohort == "contaminated",
        "protocol": "final-v3",
        "protocol_sha256": text_hash(folder / "manifest.json"),
    }
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
                code = getattr(exc, "code", None) or (
                    "schema_or_contract_error"
                    if isinstance(exc, GenerationContractError)
                    else "runtime_error"
                )
                error = {"code": code, "type": type(exc).__name__}
                if isinstance(exc, InvalidCitationError):
                    error["invalid_ids"] = list(exc.invalid_ids)
                fatal = trace["stage"] == "model_load" or code == "runtime_error"
            docs = [
                RetrievedDoc(
                    review=by_id[d["review_id"]].model_copy(update={"text": d["text"]}),
                    score=d["score"],
                )
                for d in trace["context"]
            ]
            diagnostics = inspect_generation(trace["raw_response"], docs)
            if not trace["llm_called"]:
                diagnostics = dict.fromkeys(diagnostics)
                diagnostics["content_supported"] = None
            row = {
                **identity,
                "question_id": q.id,
                "pergunta": q.pergunta,
                "deve_abster": q.deve_abster,
                "relevant_ids": q.relevantes,
                "filtros": q.filtros.model_dump(mode="json", exclude_none=True),
                **trace,
                "context_ids": [d["review_id"] for d in trace["context"]],
                "retrieved_ids": [d["review_id"] for d in trace["retrieved"]],
                "diagnostics": diagnostics,
                "answer": answer.model_dump() if answer else None,
                "error": error,
                "status": "error" if error else "ok",
                "latency_ms": (perf_counter() - started) * 1000,
                "corrective_calls": 0,
            }
            journal.append(row)
            if fatal:
                raise RuntimeError("Runtime failure saved; resolve before resuming")
        return journal.records.copy()


def summarize_final(rows, expected_ids, negative_count):
    if [r["question_id"] for r in rows] != expected_ids[: len(rows)]:
        raise ValueError("Unexpected IDs or order")
    if rows and len({r["experiment_id"] for r in rows}) != 1:
        raise ValueError("Mixed experiments")
    complete = len(rows) == len(expected_ids)
    calls = [r for r in rows if r["llm_called"]]
    responses = [
        r for r in calls if r["diagnostics"]["schema_valid"] and not r["diagnostics"]["abstained"]
    ]
    quotes = [r for r in responses if r["diagnostics"]["ids_in_context"]]
    positive = [r for r in rows if not r["deve_abster"]]
    negative = [r for r in rows if r["deve_abster"]]

    def fraction(n, d):
        return {"numerator": n, "denominator": d, "rate": n / d if complete and d else None}

    def abstained(r):
        return bool(r["answer"] and r["answer"]["abstained"])

    return {
        "complete": complete,
        "questions": len(rows),
        "cohort": rows[0]["cohort"] if rows else None,
        "contaminated": rows[0]["contaminated"] if rows else None,
        "llm_calls": len(calls),
        "schema_first_object_valid": fraction(
            sum(r["diagnostics"]["schema_valid"] for r in calls), len(calls)
        ),
        "schema_valid_without_ignored_suffix": fraction(
            sum(
                bool(
                    r["diagnostics"]["schema_valid"]
                    and not r["diagnostics"]["trailing_text_ignored"]
                )
                for r in calls
            ),
            len(calls),
        ),
        "output_token_cap_hits": sum(
            bool(
                r.get("generation_metrics")
                and r["generation_metrics"]["generated_tokens"]
                == r["generation_metrics"]["max_new_tokens"]
            )
            for r in calls
        ),
        "trailing_text_ignored": sum(
            bool(r["diagnostics"]["trailing_text_ignored"]) for r in calls
        ),
        "ids_in_context": fraction(
            sum(r["diagnostics"]["ids_in_context"] for r in responses), len(responses)
        ),
        "quotes_literal": fraction(
            sum(r["diagnostics"]["quotes_literal"] for r in quotes), len(quotes)
        ),
        "parser_accepted_llm": sum(bool(r["diagnostics"]["parser_accepted"]) for r in calls),
        "correct_negative_abstention": fraction(
            sum(abstained(r) for r in negative), negative_count
        ),
        "negative_llm_calls": sum(r["llm_called"] for r in negative),
        "retriever_empty_abstentions": sum(
            bool(r["answer"] and r["answer"].get("abstention_reason") == "retriever_empty")
            for r in rows
        ),
        "undue_positive_abstention": fraction(
            sum(abstained(r) for r in positive), len(expected_ids) - negative_count
        ),
        "context_evidence_positive": fraction(
            sum(bool(set(r["relevant_ids"]) & set(r["context_ids"])) for r in positive),
            len(expected_ids) - negative_count,
        ),
        "errors": sum(r["error"] is not None for r in rows),
        "content_supported": None,
        "factual_review_completed": False,
        "corrective_calls": 0,
    }
