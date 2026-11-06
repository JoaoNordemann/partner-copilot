import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_results", ROOT / "scripts/build_results.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def test_random_counts_are_events_not_independent_questions():
    block = {
        "questions": [
            {
                "id": "q01",
                "deve_abster": False,
                "hit_at_k": 0.25,
                "retrieved_relevant": 0.25,
                "retrieved_irrelevant": 4.75,
            },
            {"id": "q02", "deve_abster": True, "hit_at_k": None},
        ]
    }
    assert builder.raw_counts(block, 200) == "Hit 50/200; relevantes 50; irrelevantes 950"
    with pytest.raises(ValueError, match="integral"):
        builder.raw_counts(block)
    block["questions"].append(block["questions"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        builder.raw_counts(block, 200)


def test_undefined_contract_fields_are_not_reported_as_zero():
    assert builder.fraction({"passed": 0, "applicable": 0}) == "N/A"
    assert builder.fraction({"passed": 0, "applicable": 27}) == "0/27"


def test_inputs_require_the_exact_cited_git_contents(tmp_path, monkeypatch):
    (tmp_path / "data.json").write_bytes(b'{"value":1}\r\n')
    monkeypatch.setattr(builder.subprocess, "check_output", lambda *a, **k: b'{"value":1}\n')
    inputs = builder.Inputs(tmp_path, "a" * 40)
    assert inputs.read("data.json") == {"value": 1}
    assert inputs.files["data.json"]["commit"] == "a" * 40
    (tmp_path / "data.json").write_text('{"value":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="differs from cited commit"):
        builder.Inputs(tmp_path, "a" * 40).read("data.json")
    with pytest.raises(ValueError, match="immutable"):
        builder.Inputs(tmp_path, "main")


def test_readme_update_is_idempotent_and_preserves_manual_content():
    original = "# Project\n\nManual section.\n"
    updated = builder.replace_section(original, "## Results\n\nGenerated.\n")
    assert "Manual section." in updated
    assert builder.replace_section(updated, "## Results\n\nGenerated.\n") == updated
    assert "Replacement" in builder.replace_section(updated, "Replacement")
    with pytest.raises(ValueError, match="Incomplete"):
        builder.replace_section(original + builder.BEGIN, "Generated")


def test_k_comparison_validates_nested_paired_counts():
    record = {
        "method": "multilingual",
        "metrics": {"recall_classic_at_k": {"wins": 1, "ties": 2, "losses": 1, "questions": 4}},
    }
    report = {"paired": {"k_increments": [record]}}
    assert builder.find_pair(report, "k_increments", method="multilingual") == record
    record["metrics"]["recall_classic_at_k"]["questions"] = 5
    with pytest.raises(ValueError, match="Inconsistent"):
        builder.find_pair(report, "k_increments", method="multilingual")


def test_readme_has_five_headlines_and_links_to_full_results():
    context = {
        "primary": {
            "questions": 2,
            "wins": 1,
            "ties": 1,
            "losses": 0,
            "per_question": [
                {"reference": 0.2, "variant": 0.4},
                {"reference": 0.4, "variant": 0.4},
            ],
        },
        "generation": {
            "experiments": {
                "v3-new": {
                    "accepted": {"passed": 3, "applicable": 4},
                    "diagnostics": {
                        "good": {"parser_accepted": True, "abstained": False},
                        "bad": {"parser_accepted": True, "abstained": False},
                        "refusal": {"parser_accepted": True, "abstained": True},
                    },
                }
            }
        },
        "correction": {"corrections_requested": 25, "corrections_accepted": 0},
        "ai": [
            {
                "experiment": "v3-new",
                "question_id": "good",
                "support": "sustentada",
                "answers_question": "sim",
            },
            {
                "experiment": "v3-new",
                "question_id": "bad",
                "support": "sem_suporte",
                "answers_question": "nao",
            },
        ],
    }
    text = builder.headlines(context)
    assert sum(line.startswith("- ") for line in text.splitlines()) == 5
    assert "1/2 substantivas" in text
    assert "3/4 saídas" in text
    assert "reports/final-results-v1/RESULTADOS.md" in text
    assert len(text.splitlines()) <= 7
