import json

import pytest
from filelock import Timeout

from partner_copilot.evaluation.journal import QuestionJournal


def row(identifier):
    return {"question_id": identifier, "experiment_id": "experiment", "status": "ok"}


def test_each_question_is_on_disk_before_the_next_one_and_resume_skips_prefix(tmp_path):
    path = tmp_path / "results.jsonl"
    with (
        pytest.raises(KeyboardInterrupt),
        QuestionJournal(path, "experiment", ["q01", "q02"]) as journal,
    ):
        journal.append(row("q01"))
        assert json.loads(path.read_text(encoding="utf-8"))["question_id"] == "q01"
        raise KeyboardInterrupt()
    with QuestionJournal(path, "experiment", ["q01", "q02"], resume=True) as journal:
        assert len(journal.records) == 1
        journal.append(row("q02"))
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    with (
        pytest.raises(ValueError, match="exists"),
        QuestionJournal(path, "experiment", ["q01", "q02"]),
    ):
        pass


def test_resume_recovers_only_incomplete_tail_and_preserves_valid_last_line(tmp_path):
    path = tmp_path / "results.jsonl"
    prefix = (json.dumps(row("q01")) + "\n").encode()
    path.write_bytes(prefix + b'{"question_id":"q02",')
    with QuestionJournal(path, "experiment", ["q01", "q02"], resume=True) as journal:
        assert journal.records == [row("q01")]
        assert path.read_bytes() == prefix
        assert path.with_name(path.name + ".interrupted-tail").exists()
        journal.append(row("q02"))
    path.write_text(json.dumps(row("q01")), encoding="utf-8")
    with QuestionJournal(path, "experiment", ["q01"], resume=True) as journal:
        assert journal.records == [row("q01")]
    assert path.read_bytes().endswith(b"\n")


def test_changed_identity_corruption_duplicates_and_second_writer_are_rejected(tmp_path):
    path = tmp_path / "results.jsonl"
    with QuestionJournal(path, "experiment", ["q01", "q02"]) as journal:
        journal.append(row("q01"))
        with pytest.raises(ValueError):
            journal.append(row("q01"))
        with pytest.raises(Timeout), QuestionJournal(path, "experiment", ["q01"], resume=True):
            pass
    with (
        pytest.raises(ValueError, match="identity"),
        QuestionJournal(path, "other", ["q01"], resume=True),
    ):
        pass
    path.write_text("broken\n" + json.dumps(row("q01")), encoding="utf-8")
    before = path.read_bytes()
    with (
        pytest.raises(ValueError, match="Corrupt"),
        QuestionJournal(path, "experiment", ["q01"], resume=True),
    ):
        pass
    assert path.read_bytes() == before
