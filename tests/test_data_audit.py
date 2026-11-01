import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_synthetic_data.py"
spec = importlib.util.spec_from_file_location("data_audit", SCRIPT)
assert spec is not None and spec.loader is not None
_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_audit)


def test_literal_repetition_counts_distinct_phrases_and_excess_occurrences():
    metrics = _audit.repetition_metrics(
        [
            {"text": "Bom. Bom."},
            {"text": "Bom. Ruim!"},
            {"text": "Bom. Bom."},
        ]
    )
    assert metrics["sentence_occurrences"] == 6
    assert metrics["distinct_sentences"] == 2
    assert metrics["distinct_repeated_sentences"] == 1
    assert metrics["excess_sentence_occurrences"] == 4
    assert metrics["repeated_sentence_occurrences"] == 5
    assert metrics["distinct_duplicate_review_texts"] == 1
    assert metrics["excess_duplicate_review_texts"] == 1
