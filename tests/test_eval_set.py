import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from shutil import copytree

import pytest
from pydantic import ValidationError

from partner_copilot.config import Settings
from partner_copilot.evaluation.dataset import (
    EXPECTED_COUNTS,
    EvalQuestion,
    QueryFilters,
    load_eval_set,
    text_hash,
)
from partner_copilot.evaluation.retrieval import evaluate, summarize
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.retrieval.retriever import Retriever

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/eval"


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_snapshot_is_gold_only_and_sources_match_frozen_hashes():
    questions, corpus, manifest = load_eval_set(FOLDER)
    gold = {row["id"]: row for row in read_rows(ROOT / "data/splits/gold.jsonl")}
    assert {review.id for review in corpus} == set(gold)
    assert Counter(q.tipo for q in questions) == EXPECTED_COUNTS
    assert {q.filtros.restaurant_id for q in questions} == {f"rest_{i:03}" for i in range(1, 9)}
    for review in corpus:
        assert review.text == gold[review.id]["text"]
        assert review.aspects == gold[review.id]["aspects"]
    for split in ("train_pool", "rag", "quarantine"):
        assert not set(gold) & {row["id"] for row in read_rows(ROOT / f"data/splits/{split}.jsonl")}
    for filename, digest in manifest["sources_sha256_lf"].items():
        assert text_hash(ROOT / filename) == digest
    assert manifest["independent_human_reviewed_count"] == 0
    assert not manifest["filters_use_aspect_labels"]
    negatives = [q for q in questions if q.deve_abster]
    assert sum(any(q.filtros.matches(r) for r in corpus) for q in negatives) == 4


def test_relevance_is_consistent_with_blinded_annotations_and_structural_scope():
    questions, corpus, _ = load_eval_set(FOLDER)
    aspects = (
        [
            "embalagem",
            "atendimento",
            "temperatura",
            "sabor",
            "embalagem",
            "temperatura",
            "sabor",
            "preco",
        ]
        + ["tempo_entrega"] * 5
        + ["sabor"] * 5
        + ["temperatura", "tempo_entrega", "embalagem", "sabor", "atendimento", "preco"]
    )
    for question, aspect in zip(questions[:24], aspects, strict=True):
        expected = {
            r.id for r in corpus if question.filtros.matches(r) and r.aspects.get(aspect) == "neg"
        }
        assert set(question.relevantes) == expected, question.id
    for q in questions[8:13]:
        assert (q.filtros.end_date - q.filtros.start_date).days == 13


def test_detailed_audit_has_actual_text_and_rejected_controls_for_ten_questions():
    questions, corpus, _ = load_eval_set(FOLDER)
    by_id = {r.id: r for r in corpus}
    queries = {q.id: q for q in questions}
    audits = read_rows(FOLDER / "relevance_audit.jsonl")
    assert len({entry["question_id"] for entry in audits}) == 10
    for entry in audits:
        q = queries[entry["question_id"]]
        assert {row["id"] for row in entry["accepted"]} == set(q.relevantes)
        assert entry["rejected"] and entry["decision"]
        assert not {row["id"] for row in entry["rejected"]} & set(q.relevantes)
        for row in entry["accepted"] + entry["rejected"]:
            assert row["text"] == by_id[row["id"]].text


def test_tampered_snapshot_is_rejected(tmp_path):
    folder = tmp_path / "eval"
    copytree(FOLDER, folder)
    with (folder / "questions.jsonl").open("a", encoding="utf-8") as target:
        target.write("{}\n")
    with pytest.raises(ValueError, match="checksum"):
        load_eval_set(folder)


@pytest.mark.parametrize("identifier", ["not_in_corpus", "rev_000212"])
def test_relevant_id_must_exist_and_match_restaurant_even_after_rehash(tmp_path, identifier):
    folder = tmp_path / "eval"
    copytree(FOLDER, folder)
    rows = read_rows(folder / "questions.jsonl")
    rows[0]["relevantes"] = [identifier]
    (folder / "questions.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    manifest["file_sha256_lf"]["questions.jsonl"] = text_hash(folder / "questions.jsonl")
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="outside corpus or filters"):
        load_eval_set(folder)


def test_eval_schema_rejects_aspect_filter_and_contradictory_abstention():
    with pytest.raises(ValidationError):
        QueryFilters(restaurant_id="rest_001", aspect="sabor")
    with pytest.raises(ValidationError):
        QueryFilters(
            restaurant_id="rest_001", start_date=date(2026, 11, 2), end_date=date(2026, 11, 1)
        )
    row = read_rows(FOLDER / "questions.jsonl")[0]
    with pytest.raises(ValidationError):
        EvalQuestion.model_validate(row | {"deve_abster": True})


class FakeEmbedder:
    model_name = "test/eval"
    document_prefix = query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def test_two_modes_use_separate_temporary_database_and_never_relax_filters(tmp_path):
    settings = Settings(retrieval_k=3, retrieval_min_score=0.25)
    database = tmp_path / "evaluation"
    report = evaluate(FOLDER, database, FakeEmbedder(), settings)
    for mode in ("sem_filtro", "com_filtro"):
        assert len(report["modes"][mode]["questions"]) == 30
    filtered = {row["id"]: row for row in report["modes"]["com_filtro"]["questions"]}
    unfiltered = {row["id"]: row for row in report["modes"]["sem_filtro"]["questions"]}
    assert filtered["q29"]["returned_ids"] == filtered["q30"]["returned_ids"] == []
    assert len(unfiltered["q29"]["returned_ids"]) == 3
    store = ChromaStore(database, collection="isolated_gold_eval", embedder=FakeEmbedder())
    docs = Retriever(store, k=8).retrieve("sabor", "rest_001", item="Pizza Calabresa")
    assert docs and all(doc.review.item == "Pizza Calabresa" for doc in docs)
    with pytest.raises(ValueError, match="empty database"):
        evaluate(FOLDER, database, FakeEmbedder(), settings)
    assert store.count() == 100


def test_metric_denominators_separate_abstention_and_answerable_questions():
    rows = [
        {"deve_abster": False, "recall_at_k": 0.5, "reciprocal_rank": 0.5, "returned_ids": ["a"]},
        {"deve_abster": False, "recall_at_k": 0.0, "reciprocal_rank": 0.0, "returned_ids": []},
        {"deve_abster": True, "returned_ids": []},
        {"deve_abster": True, "returned_ids": ["wrong"]},
    ]
    metrics = summarize(rows)
    assert metrics["recall_at_k"] == metrics["mrr_at_k"] == 0.25
    assert metrics["correct_abstention_rate"] == metrics["false_answer_rate"] == 0.5
    assert metrics["answerable_abstention_rate"] == 0.5
    assert summarize(rows[:2])["correct_abstention_rate"] is None


def test_check_only_cli_validates_without_loading_model():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_retrieval.py"),
            "--eval-dir",
            str(FOLDER),
            "--check-only",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {"questions": 30, "corpus": 100, "valid": True}


def test_versioned_baseline_matches_snapshot_and_its_metrics():
    _, _, manifest = load_eval_set(FOLDER)
    report = json.loads((ROOT / "reports/retrieval-baseline.json").read_text(encoding="utf-8"))
    assert report["snapshot_sha256_lf"] == manifest["file_sha256_lf"]
    assert report["k"] == 8 and report["min_score"] == 0.25
    assert report["runtime_versions"] and len(report["model_revision"]) == 40
    for mode in ("sem_filtro", "com_filtro"):
        result = report["modes"][mode]
        assert result["summary"] == summarize(result["questions"])
