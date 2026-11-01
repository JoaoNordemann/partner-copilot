import importlib.util
import json
import random
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import pytest

from partner_copilot.schemas import Review

# Load the actual standalone script without relying on a package named "scripts".
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_synthetic_data.py"
spec = importlib.util.spec_from_file_location("synthetic_generator", SCRIPT)
assert spec is not None and spec.loader is not None
_generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = _generator
spec.loader.exec_module(_generator)

END = date(2026, 11, 1)


def test_seed_is_deterministic_and_local():
    state = random.getstate()
    first = _generator.generate(100, 42, END, 90)
    assert first == _generator.generate(100, 42, END, 90)
    assert first != _generator.generate(100, 43, END, 90)
    assert random.getstate() == state


def test_generated_reviews_match_domain_schema():
    rows = _generator.generate(300, 42, END, 90)
    assert len({row.id for row in rows}) == 300
    restaurants = {rest.restaurant_id: rest for rest in _generator.RESTAURANTS}
    for row in rows:
        review = Review.model_validate(asdict(row))
        restaurant = restaurants[review.restaurant_id]
        assert END - timedelta(days=89) <= review.created_at <= END
        assert review.category == restaurant.category
        assert review.bairro == restaurant.bairro
        assert review.item in restaurant.menu
        assert review.aspects
        assert set(review.aspects) <= set(_generator.ASPECTS)
        assert set(review.aspects.values()) <= {"pos", "neg"}
        assert review.created_at_int == int(review.created_at.strftime("%Y%m%d"))


def test_jsonl_is_reproducible_and_round_trips(tmp_path):
    rows = _generator.generate(20, 42, END, 90)
    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    _generator.write_jsonl(rows, first)
    _generator.write_jsonl(_generator.generate(20, 42, END, 90), second)
    assert first.read_bytes() == second.read_bytes()
    payloads = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
    assert payloads == [asdict(row) for row in rows]
    assert all(Review.model_validate(payload) for payload in payloads)


@pytest.mark.parametrize("n,days", [(0, 90), (-1, 90), (10, 0), (10, -1)])
def test_invalid_generation_size(n, days):
    with pytest.raises(ValueError, match="positive"):
        _generator.generate(n, 42, END, days)


def test_delivery_trend_is_present_only_for_configured_restaurants():
    """Check the emitted dataset, with enough observations in both date windows."""
    rows = _generator.generate(12000, 42, END, 90)
    counts = {
        restaurant.restaurant_id: {"recent": [], "historical": []}
        for restaurant in _generator.RESTAURANTS
    }
    for row in rows:
        polarity = row.aspects.get("tempo_entrega")
        if polarity is None:
            continue
        age = (END - date.fromisoformat(row.created_at)).days
        window = "recent" if age < 14 else "historical"
        counts[row.restaurant_id][window].append(polarity == "neg")

    for restaurant in _generator.RESTAURANTS:
        recent = counts[restaurant.restaurant_id]["recent"]
        historical = counts[restaurant.restaurant_id]["historical"]
        assert len(recent) >= 30, restaurant.restaurant_id
        assert len(historical) >= 100, restaurant.restaurant_id
        difference = sum(recent) / len(recent) - sum(historical) / len(historical)
        if restaurant.late_trend:
            assert difference > 0.30, restaurant.restaurant_id
        else:
            assert abs(difference) < 0.20, restaurant.restaurant_id


@pytest.mark.parametrize(
    "item,category,profile",
    [
        ("Açaí 500ml", "açaí", "cold"),
        ("Vitamina de Morango", "açaí", "cold"),
        ("Temaki Salmão", "japonês", "cold"),
        ("Combo 20 Peças", "japonês", "cold"),
        ("Bolo de Pote", "doces", "cold"),
        ("Cookie Recheado", "doces", "ambient"),
        ("Brigadeiro Gourmet", "doces", "ambient"),
        ("Hot Roll", "japonês", "hot"),
        ("Yakisoba", "japonês", "hot"),
        ("Feijoada Individual", "marmita", "hot"),
    ],
)
def test_temperature_language_matches_the_item(item, category, profile):
    assert _generator.temperature_profile(item, category) == profile
    for polarity in ("pos", "neg"):
        for seed in range(40):
            phrase = _generator._render_aspect(
                "temperatura", polarity, item, category, random.Random(seed)
            ).lower()
            if profile != "hot":
                assert "micro-ondas" not in phrase
                assert "requentar" not in phrase
            if profile == "cold" and polarity == "pos":
                assert "quente" not in phrase
                assert "quentinho" not in phrase
            if profile == "hot" and polarity == "pos":
                assert "refrigerado" not in phrase
                assert "gelado" not in phrase


def test_ratings_remain_consistent_with_negative_aspects():
    for row in _generator.generate(3000, 42, END, 90):
        if "neg" in row.aspects.values():
            assert row.rating <= 4
        if set(row.aspects.values()) == {"neg"}:
            assert row.rating <= 3


def test_each_configured_weakness_is_visible_in_the_population():
    rows = _generator.generate(12000, 42, END, 90)
    for restaurant in _generator.RESTAURANTS:
        for aspect in restaurant.weak_aspects:
            baseline_ids = {
                rest.restaurant_id
                for rest in _generator.RESTAURANTS
                if aspect not in rest.weak_aspects
            }
            eligible = [
                row
                for row in rows
                if aspect in row.aspects
                and (
                    aspect != "tempo_entrega"
                    or (END - date.fromisoformat(row.created_at)).days >= 14
                )
            ]
            target = [
                row.aspects[aspect] == "neg"
                for row in eligible
                if row.restaurant_id == restaurant.restaurant_id
            ]
            baseline = [
                row.aspects[aspect] == "neg"
                for row in eligible
                if row.restaurant_id in baseline_ids
            ]
            assert len(target) >= 100
            difference = sum(target) / len(target) - sum(baseline) / len(baseline)
            assert difference > 0.03, (restaurant.restaurant_id, aspect, difference)
