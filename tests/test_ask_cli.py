import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from partner_copilot import cli
from partner_copilot.asking import AskPreflightError
from partner_copilot.generation.contracts import (
    ABSTENTION_MESSAGE,
    GenerationContractError,
    InvalidCitationError,
)
from partner_copilot.schemas import Answer, AnswerMetadata

ROOT = Path(__file__).resolve().parents[1]


def answer():
    return Answer(
        answer=ABSTENTION_MESSAGE,
        sources=[],
        abstained=True,
        abstention_reason="retriever_empty",
        metadata=AnswerMetadata(
            latency_ms=1,
            retrieved_documents=0,
            context_documents=0,
            prompt_version="partner-copilot-v1",
            llm_called=False,
        ),
    )


def test_cli_propagates_filters_and_constructor_settings_override_environment(monkeypatch, capsys):
    monkeypatch.setenv("RETRIEVAL_K", "8")
    run = Mock(return_value=answer())
    monkeypatch.setattr(cli, "run_ask", run)
    code = cli.main(
        [
            "ask",
            "A caixa foi danificada?",
            "--restaurant-id",
            "rest_fixture",
            "--item",
            "Caixa",
            "--aspect",
            "embalagem",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--category",
            "teste",
            "--city",
            "Teste",
            "--bairro",
            "Centro",
            "--db-path",
            "custom-db",
            "--collection",
            "existing_reviews",
            "--embedding-model",
            "test/model",
            "--llm-model",
            "test/llm",
            "--retrieval-k",
            "3",
            "--context-k",
            "2",
            "--min-score",
            "0.4",
            "--seed",
            "7",
            "--temperature",
            "0",
            "--max-new-tokens",
            "64",
            "--json",
        ]
    )
    assert code == 0
    settings, request = run.call_args.args
    assert settings.retrieval_k == 3 and settings.context_k == 2
    assert settings.chroma_path == Path("custom-db") and settings.embedding_model == "test/model"
    assert settings.llm_model_id == "test/llm" and settings.generation_seed == 7
    assert request.start_date.isoformat() == "2026-01-01" and request.item == "Caixa"
    assert request.aspect == "embalagem" and request.city == "Teste"
    assert run.call_args.kwargs == {"collection": "existing_reviews"}
    result = json.loads(capsys.readouterr().out)
    assert result["abstained"] and result["metadata"]["llm_called"] is False


def test_text_output_contains_answer_sources_and_metadata(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_ask", Mock(return_value=answer()))
    assert cli.main(["ask", "Pergunta", "--restaurant-id", "rest_fixture"]) == 0
    output = capsys.readouterr().out
    assert ABSTENTION_MESSAGE in output and "Fontes: nenhuma" in output
    assert "Metadados:" in output and "prompt_version" in output


@pytest.mark.parametrize(
    "flags",
    [
        ["--retrieval-k", "0"],
        ["--start-date", "2026-02-01", "--end-date", "2026-01-01"],
        ["--context-k", "0"],
    ],
)
def test_invalid_configuration_never_reaches_backend(monkeypatch, capsys, flags):
    run = Mock()
    monkeypatch.setattr(cli, "run_ask", run)
    code = cli.main(["ask", "Pergunta", "--restaurant-id", "rest_fixture", "--json", *flags])
    assert (
        code == 2
        and json.loads(capsys.readouterr().out)["error"]["code"] == "invalid_configuration"
    )
    run.assert_not_called()


@pytest.mark.parametrize(
    "failure,expected_exit,expected_code",
    [
        (
            InvalidCitationError(["inventada", "inventada", "outra"], {"fonte_a"}),
            3,
            "invalid_citation",
        ),
        (GenerationContractError("Missing citations"), 4, "generation_contract_error"),
        (AskPreflightError("No index"), 2, "ask_preflight_failed"),
        (RuntimeError("backend unavailable"), 1, "runtime_error"),
    ],
)
def test_errors_are_machine_readable_and_never_emit_success(
    monkeypatch, capsys, failure, expected_exit, expected_code
):
    monkeypatch.setattr(cli, "run_ask", Mock(side_effect=failure))
    assert (
        cli.main(["ask", "Pergunta", "--restaurant-id", "rest_fixture", "--json"]) == expected_exit
    )
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == expected_code and "answer" not in result
    if expected_code == "invalid_citation":
        assert result["error"]["invalid_citation_count"] == 3
        assert result["error"]["invalid_ids"] == ["inventada", "outra"]


def test_help_and_missing_database_work_without_chroma_or_model_libraries(tmp_path):
    code = """
import importlib.abc
import sys
class BlockHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'chromadb','torch','transformers','sentence_transformers'}:
            raise ImportError('Forbidden dependency: ' + fullname)
sys.meta_path.insert(0,BlockHeavy())
sys.path.insert(0,sys.argv[1])
from partner_copilot.cli import main
raise SystemExit(main(sys.argv[2:]))
"""
    command = [sys.executable, "-c", code, str(ROOT / "src")]
    help_result = subprocess.run([*command, "ask", "--help"], capture_output=True, text=True)
    assert help_result.returncode == 0 and "--restaurant-id" in help_result.stdout
    result = subprocess.run(
        [
            *command,
            "ask",
            "Pergunta",
            "--restaurant-id",
            "rest_fixture",
            "--db-path",
            str(tmp_path / "absent"),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 2
        and json.loads(result.stdout)["error"]["code"] == "ask_preflight_failed"
    )
    assert not (tmp_path / "absent").exists()
