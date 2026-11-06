from datetime import date

import pytest

from partner_copilot.evaluation.ablations import (
    KS,
    cheap_methods,
    eligible_reviews,
    measure_question,
    paired,
)
from partner_copilot.evaluation.dataset import EvalQuestion
from partner_copilot.schemas import Review


def question(identifier="q01", negative=False):
    return EvalQuestion(
        id=identifier,
        pergunta="Entrega atrasada?",
        tipo="sem_resposta" if negative else "temporal",
        filtros={"restaurant_id": "rest_001", "item": "pizza", "start_date": "2026-11-01"},
        relevantes=[] if negative else ["r1"],
        deve_abster=negative,
        criterio="Explicit delay",
    )


def review(identifier, restaurant="rest_001"):
    return Review(
        id=identifier,
        restaurant_id=restaurant,
        text="Entrega atrasada",
        rating=2,
        created_at=date(2026, 1, 1),
        item="sushi",
        category="comida",
        bairro="Centro",
    )


def test_restaurant_factor_does_not_leak_item_or_date_filters():
    q = question()
    corpus = [review("r1"), review("r2", "rest_002")]
    assert not q.filtros.matches(corpus[0])
    assert [r.id for r in eligible_reviews(q, corpus, "restaurante")] == ["r1"]
    assert len(eligible_reviews(q, corpus, "sem_filtro")) == 2
    with pytest.raises(ValueError):
        eligible_reviews(q, corpus, "invalid")


def test_paired_reports_wins_ties_losses_and_excludes_negatives():
    reference, variant = [], []
    for index, (a, b) in enumerate([([], ["r1"]), (["r1"], ["r1"]), (["r1"], [])], 1):
        q = question(f"q{index:02}")
        reference.append(measure_question(q, a, 5))
        variant.append(measure_question(q, b, 5))
    negative = measure_question(question("q04", True), ["r1"], 5)
    reference.append(negative)
    variant.append(negative)
    result = paired(reference, list(reversed(variant)), "hit_at_k")
    assert (result["wins"], result["ties"], result["losses"], result["questions"]) == (1, 1, 1, 3)
    assert result["mean_delta"] == 0
    with pytest.raises(ValueError, match="Incomplete"):
        paired(reference, variant[:-1], "hit_at_k")
    with pytest.raises(ValueError, match="Duplicate"):
        paired(reference + reference[:1], variant, "hit_at_k")


def test_k12_short_results_keep_fixed_precision_denominator():
    row = measure_question(question(), ["r1", "wrong"], 12)
    assert row["precision_at_k"] == pytest.approx(1 / 12)
    assert row["recall_capped_at_k"] == 1
    assert row["retrieved_relevant"] == row["retrieved_irrelevant"] == 1
    assert KS == (1, 3, 5, 8, 12)


def test_random_is_mean_per_question_and_shares_candidate_scope():
    questions = [question(), question("q02", True)]
    corpus = [review("r1"), review("r2"), review("r3", "rest_002")]
    result = cheap_methods(questions, corpus)
    random = result["random"]["restaurante"]
    assert random["repetitions"] == 200
    assert set(random["seed_42_rankings"]["q01"]) == {"r1", "r2"}
    assert random["ranking"]["3"]["questions"][0]["hit_at_k"] == 1
    assert random["ranking"]["3"]["summary"]["false_evidence_rate"] == 1
    assert random["ranking"]["1"]["aggregate_std_across_seeds"]["hit_at_k"] > 0
    assert random["ranking"] == random["operational"]
    keyword = result["keyword"]["restaurante"]["ranking"]["12"]["questions"][0]
    assert keyword["returned_ids"] == ["r1", "r2"]
