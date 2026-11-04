from datetime import date
from unittest.mock import Mock

import pytest

from partner_copilot.config import Settings
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.retrieval.retriever import Retriever
from partner_copilot.schemas import RetrievedDoc, Review


def review(identifier="review", **changes):
    return Review.model_validate(
        {
            "id": identifier,
            "restaurant_id": "rest_001",
            "text": "O pedido chegou atrasado.",
            "rating": 2,
            "created_at": "2026-11-01",
            "category": "pizza",
            "bairro": "Centro",
            "aspects": {"tempo_entrega": "neg"},
            **changes,
        }
    )


def test_candidate_budget_threshold_inclusive_and_fewer_than_k():
    store = Mock()
    store.query.return_value = [
        RetrievedDoc(review=review(str(i)), score=score)
        for i, score in enumerate([0.9, 0.5, 0.49, -0.2])
    ]
    retriever = Retriever(store, k=3, min_score=0.5)
    result = retriever.retrieve("entrega", "rest_001")
    store.query.assert_called_once_with("entrega", 6, {"restaurant_id": "rest_001"})
    assert [doc.score for doc in result] == [0.9, 0.5]
    store.query.return_value = [RetrievedDoc(review=review(str(i)), score=0.9) for i in range(6)]
    assert len(retriever.retrieve("entrega", "rest_001")) == 3
    store.query.return_value = [RetrievedDoc(review=review(), score=0.1)]
    assert retriever.retrieve("entrega", "rest_001") == []


def test_settings_and_combined_filters():
    store = Mock()
    store.query.return_value = []
    retriever = Retriever(store, settings=Settings(retrieval_k=4, retrieval_min_score=0.6))
    retriever.retrieve(
        "entrega",
        "rest_001",
        "tempo_entrega",
        start_date=date(2026, 10, 19),
        end_date=date(2026, 11, 1),
        category="pizza",
        city="São Paulo",
        bairro="Centro",
    )
    assert retriever.min_score == 0.6
    store.query.assert_called_once_with(
        "entrega",
        8,
        {
            "$and": [
                {"restaurant_id": "rest_001"},
                {"aspect_tempo_entrega": "neg"},
                {"category": "pizza"},
                {"city": "São Paulo"},
                {"bairro": "Centro"},
                {"created_at_int": {"$gte": 20261019}},
                {"created_at_int": {"$lte": 20261101}},
            ]
        },
    )


def test_inverted_date_window_fails_before_query():
    store = Mock()
    with pytest.raises(ValueError, match="start_date"):
        Retriever(store).retrieve(
            "entrega", "rest_001", start_date=date(2026, 11, 2), end_date=date(2026, 11, 1)
        )
    store.query.assert_not_called()


def test_empty_store_result_abstains_without_calling_llm():
    store, llm = Mock(), Mock()
    store.query.return_value = []
    retriever = Retriever(store, k=3)
    assert retriever.retrieve("entrega", "rest_001") == []
    answer = RAGPipeline(retriever, llm).ask("entrega", "rest_001")
    assert answer.sources == []
    assert answer.answer == "Não há evidência suficiente nas avaliações fornecidas."
    llm.generate.assert_not_called()


@pytest.mark.parametrize("bound,operator", [("start_date", "$gte"), ("end_date", "$lte")])
def test_item_and_one_sided_date_filters(bound, operator):
    store = Mock()
    store.query.return_value = []
    Retriever(store, k=2).retrieve(
        "sabor", "rest_001", item="Pizza Calabresa", **{bound: date(2026, 11, 1)}
    )
    store.query.assert_called_once_with(
        "sabor",
        4,
        {
            "$and": [
                {"restaurant_id": "rest_001"},
                {"item": "Pizza Calabresa"},
                {"created_at_int": {operator: 20261101}},
            ]
        },
    )
