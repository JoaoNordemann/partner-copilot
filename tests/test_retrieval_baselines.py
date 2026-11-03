from pathlib import Path

import pytest

from partner_copilot.evaluation.baselines import (
    KS,
    aggregate,
    compare_baselines,
    question_metrics,
    tokens,
)
from partner_copilot.evaluation.dataset import EvalQuestion

ROOT = Path(__file__).resolve().parents[1]


def question(relevant=None, abstain=False):
    return EvalQuestion(
        id="q01",
        pergunta="Entrega atrasada?",
        tipo=("sem_resposta" if abstain else "restaurante_aspecto"),
        filtros={"restaurant_id": "rest_001"},
        relevantes=([] if abstain else relevant or [f"r{i}" for i in range(10)]),
        deve_abster=abstain,
        criterio="Evidência explícita",
    )


def test_capped_recall_is_distinct_from_classic_recall_and_precision():
    result = question_metrics(question(), ["wrong", "r1", "r2", "r3"], 3)
    assert result["hit_at_k"] == 1
    assert result["recall_capped_at_k"] == pytest.approx(2 / 3)
    assert result["recall_classic_at_k"] == 0.2
    assert result["precision_at_k"] == pytest.approx(2 / 3)
    assert result["mrr_at_k"] == 0.5
    short = question_metrics(question(["r1"]), ["r1"], 8)
    assert short["recall_capped_at_k"] == 1
    assert short["precision_at_k"] == 1 / 8
    assert question_metrics(question(), ["wrong"], 1)["hit_at_k"] == 0


def test_empty_results_and_no_answer_questions_have_separate_denominators():
    positive = question_metrics(question(), [], 5)
    negative = question_metrics(question(abstain=True), ["wrong"], 5)
    assert negative["recall_capped_at_k"] is None
    result = aggregate([positive, negative])
    assert result["hit_at_k"] == result["precision_at_k"] == 0
    assert result["answerable_abstention_rate"] == result["false_evidence_rate"] == 1
    assert result["correct_abstention_rate"] == 0
    assert aggregate([negative])["mrr_at_k"] is None


def test_duplicate_predictions_cannot_inflate_metrics():
    with pytest.raises(ValueError):
        question_metrics(question(), ["r1", "r1"], 3)
    with pytest.raises(ValueError):
        question_metrics(question(), [], 0)


def test_lexical_tokens_ignore_case_accents_punctuation_and_function_words():
    assert tokens("A ENTREGA, na São Paulo: atrasou! atrasou") == {"entrega", "paulo", "atrasou"}


class FakeEmbedder:
    model_name = "test/comparison"
    document_prefix = query_prefix = ""

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def test_comparison_is_reproducible_and_respects_empty_and_single_candidate_filters():
    first = compare_baselines(ROOT / "data/eval", FakeEmbedder())
    second = compare_baselines(ROOT / "data/eval", FakeEmbedder())
    assert first == second
    assert first["ks"] == list(KS)
    assert first["random"]["repetitions"] == 200
    for method in ("semantic", "keyword"):
        results = first["methods"][method]["com_filtro"]
        rows = {row["id"]: row for row in results["questions"]}
        assert rows["q29"]["ranked_ids"] == rows["q30"]["ranked_ids"] == []
        assert rows["q10"]["ranked_ids"] == ["rev_002237"]
        assert set(results["ranking"]) == {"1", "3", "5", "8"}
    random = first["methods"]["random"]["com_filtro"]
    assert random["seed_42_rankings"]["q10"] == ["rev_002237"]
    assert random["seed_42_rankings"]["q30"] == []
    for k in map(str, KS):
        assert 0 <= random["ranking"][k]["mean"]["hit_at_k"] <= 1
        assert random["ranking"][k]["std"]["hit_at_k"] >= 0
