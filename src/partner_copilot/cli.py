"""Command-line entry point for debugging and demonstrating evidence-grounded answers."""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from partner_copilot.asking import AskPreflightError, AskRequest, run_ask
from partner_copilot.config import Settings
from partner_copilot.generation.contracts import GenerationContractError, InvalidCitationError

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="partner-copilot", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="Ask about the registered production RAG reviews")
    ask.add_argument("question")
    ask.add_argument("--restaurant-id", required=True)
    for name in ("aspect", "item", "category", "city", "bairro"):
        ask.add_argument(f"--{name}")
    ask.add_argument("--start-date", type=date.fromisoformat)
    ask.add_argument("--end-date", type=date.fromisoformat)
    ask.add_argument("--db-path", type=Path)
    ask.add_argument("--collection", help="Existing literal name; default: model-aware collection")
    ask.add_argument("--embedding-model")
    ask.add_argument("--llm-model")
    ask.add_argument("--retrieval-k", type=int)
    ask.add_argument("--context-k", type=int)
    ask.add_argument("--min-score", type=float)
    ask.add_argument("--temperature", type=float)
    ask.add_argument("--seed", type=int)
    ask.add_argument("--max-new-tokens", type=int)
    ask.add_argument("--prompt-version")
    ask.add_argument(
        "--parser-version", choices=("parser-v1", "parser-v2", "parser-json-v1", "parser-v3")
    )
    ask.add_argument(
        "--json", action="store_true", help="JSON on stdout for answers or application errors"
    )
    return parser


def _error(args: argparse.Namespace, code: str, message: str, exit_code: int, **details) -> int:
    payload = {"error": {"code": code, "message": message, **details}}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Erro [{code}]: {message}", file=sys.stderr)
        if details:
            print(json.dumps(details, ensure_ascii=False), file=sys.stderr)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    fields = {
        "chroma_path": args.db_path,
        "chroma_collection": args.collection,
        "embedding_model": args.embedding_model,
        "llm_model_id": args.llm_model,
        "retrieval_k": args.retrieval_k,
        "context_k": args.context_k,
        "retrieval_min_score": args.min_score,
        "temperature": args.temperature,
        "generation_seed": args.seed,
        "max_new_tokens": args.max_new_tokens,
        "prompt_version": args.prompt_version,
        "parser_version": args.parser_version,
    }
    try:
        settings = Settings(**{key: value for key, value in fields.items() if value is not None})
        request = AskRequest(**{name: getattr(args, name) for name in AskRequest.model_fields})
    except ValidationError as exc:
        return _error(
            args,
            "invalid_configuration",
            "Invalid request or configuration",
            2,
            details=exc.errors(include_input=False, include_context=False, include_url=False),
        )
    try:
        answer = run_ask(settings, request, collection=args.collection)
    except AskPreflightError as exc:
        return _error(args, "ask_preflight_failed", str(exc), 2)
    except InvalidCitationError as exc:
        return _error(
            args,
            exc.code,
            str(exc),
            3,
            invalid_ids=list(exc.invalid_ids),
            invalid_citation_count=exc.invalid_citation_count,
            allowed_context_ids=list(exc.allowed_context_ids),
        )
    except GenerationContractError as exc:
        return _error(args, "generation_contract_error", str(exc), 4)
    except Exception as exc:
        logger.error("ask_failed error_type=%s", type(exc).__name__)
        return _error(args, "runtime_error", "Query execution failed; see stderr logs", 1)
    if args.json:
        print(answer.model_dump_json(indent=2))
    else:
        print(f"Resposta:\n{answer.answer}")
        print("Fontes: " + (", ".join(answer.sources) or "nenhuma"))
        print("Abstenção: " + ("sim" if answer.abstained else "não"))
        if answer.abstention_reason:
            print(f"Motivo: {answer.abstention_reason}")
        print("Metadados:\n" + answer.metadata.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
