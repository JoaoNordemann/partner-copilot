#!/usr/bin/env python
"""Gera reviews sintéticas de restaurantes de delivery (pt-BR) para o PartnerCopilot.

IMPORTANTE: os dados são 100% sintéticos e NÃO representam dados reais do iFood.
Os rótulos de `aspects` vêm da geração (não são anotação humana): servem para treino/bootstrap.
A avaliação final deve usar o gold set anotado à mão.

Uso:
    python scripts/generate_synthetic_data.py --n 3000 --seed 42
    python scripts/generate_synthetic_data.py --n 500 --format csv --validate
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Final, Literal

Polarity = Literal["pos", "neg"]
Aspect = Literal["sabor", "tempo_entrega", "temperatura", "embalagem", "preco", "atendimento"]

ASPECTS: Final[tuple[Aspect, ...]] = (
    "sabor",
    "tempo_entrega",
    "temperatura",
    "embalagem",
    "preco",
    "atendimento",
)

# Probabilidade de um aspecto ser mencionado numa review
MENTION_PROB: Final[dict[Aspect, float]] = {
    "sabor": 0.70,
    "tempo_entrega": 0.55,
    "temperatura": 0.35,
    "embalagem": 0.35,
    "preco": 0.20,
    "atendimento": 0.15,
}
BASE_NEG_PROB: Final[float] = 0.18
TREND_WINDOW_DAYS: Final[int] = 14
TREND_NEG_PROB: Final[float] = 0.75

# {item} aparece sem artigo para evitar problemas de gênero; {min} = minutos de entrega
TEMPLATES: Final[dict[Aspect, dict[Polarity, list[str]]]] = {
    "sabor": {
        "pos": [
            "{item} estava delicioso, tempero no ponto.",
            "O sabor de {item} surpreendeu, muito bem feito.",
            "{item} tem gosto de comida caseira, caprichado.",
            "Qualidade excelente em {item}, ingredientes frescos.",
        ],
        "neg": [
            "{item} veio sem tempero, bem sem graça.",
            "O sabor de {item} estava estranho, parecia requentado.",
            "{item} muito salgado, difícil de comer.",
            "Ingredientes de {item} pareciam velhos, gosto ruim.",
        ],
    },
    "tempo_entrega": {
        "pos": [
            "Chegou em {min} minutos, bem antes do previsto.",
            "Entrega rápida, em {min} min estava na porta.",
            "Pontual, chegou no horário combinado.",
        ],
        "neg": [
            "Demorou {min} minutos, muito além do prazo informado.",
            "Esperei mais de uma hora pelo pedido, atraso absurdo.",
            "A entrega atrasou {min} min e ninguém avisou nada.",
            "Prazo estourou, chegou quase {min} minutos depois do combinado.",
        ],
    },
    "temperatura": {
        "pos": [
            "Chegou quentinho, como se tivesse saído do forno.",
            "Temperatura perfeita, nada de comida morna.",
            "Bebida gelada e comida quente, tudo certo.",
        ],
        "neg": [
            "Chegou frio, tive que esquentar no micro-ondas.",
            "Comida morna, perdeu totalmente a graça.",
            "{item} chegou gelado, claramente ficou parado esperando.",
            "Veio frio e murcho, decepção.",
        ],
    },
    "embalagem": {
        "pos": [
            "Embalagem bem vedada, nada vazou.",
            "Muito bem embalado, chegou intacto.",
            "Embalagem térmica e organizada, nota 10.",
        ],
        "neg": [
            "Embalagem aberta, molho vazou pela sacola toda.",
            "{item} chegou amassado, embalagem fraca demais.",
            "Veio sem lacre e com a tampa solta, fiquei com receio.",
            "Pedido chegou todo derramado, embalagem péssima.",
        ],
    },
    "preco": {
        "pos": ["Preço justo pelo que entrega.", "Ótimo custo-benefício, porção generosa."],
        "neg": ["Caro pelo que entrega, porção pequena.", "Preço abusivo para a qualidade."],
    },
    "atendimento": {
        "pos": [
            "Atendimento atencioso, resolveram rápido.",
            "Restaurante muito educado no contato.",
        ],
        "neg": [
            "Atendimento ruim, ninguém respondeu minha reclamação.",
            "Falta item no pedido e o restaurante ignorou o contato.",
        ],
    },
}

OPENERS: Final[list[str]] = [
    "",
    "",
    "Pedi {item}. ",
    "Pedido de {item}: ",
    "Primeira vez pedindo aqui. ",
    "Pedi pro jantar. ",
]
CLOSERS: Final[dict[str, list[str]]] = {
    "low": [
        "Não recomendo.",
        "Vou pensar duas vezes antes de pedir de novo.",
        "Decepcionante.",
        "",
    ],
    "mid": ["Dá pra melhorar.", "Ok, nada demais.", "Foi razoável.", ""],
    "high": ["Recomendo!", "Já virou meu pedido fixo.", "Nota 10.", ""],
}


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: str
    name: str
    category: str
    bairro: str
    menu: tuple[str, ...]
    weak_aspects: dict[Aspect, float] = field(default_factory=dict)  # aspecto -> p(neg) extra
    late_trend: bool = False  # piora em tempo de entrega nos últimos 14 dias


RESTAURANTS: Final[tuple[Restaurant, ...]] = (
    Restaurant(
        "rest_001",
        "Pizzaria Forno Nobre",
        "pizza",
        "Jardim Aquarius",
        ("Pizza Margherita", "Pizza Calabresa", "Pizza Quatro Queijos", "Pizza Portuguesa"),
        {"temperatura": 0.35, "embalagem": 0.15},
    ),
    Restaurant(
        "rest_002",
        "Burger do Zé",
        "hamburguer",
        "Vila Ema",
        ("X-Bacon", "X-Salada", "Burger Duplo", "Batata Frita Grande"),
        {"embalagem": 0.30},
        late_trend=True,
    ),
    Restaurant(
        "rest_003",
        "Sushi Kaze",
        "japonês",
        "Centro",
        ("Combo 20 Peças", "Temaki Salmão", "Hot Roll", "Yakisoba"),
        {"sabor": 0.10, "tempo_entrega": 0.25},
    ),
    Restaurant(
        "rest_004",
        "Marmitaria da Dona Rosa",
        "marmita",
        "Jardim Satélite",
        ("Marmita Executiva", "Marmita Fit Frango", "Feijoada Individual", "Strogonoff"),
        {"temperatura": 0.20},
        late_trend=True,
    ),
    Restaurant(
        "rest_005",
        "Açaí Point",
        "açaí",
        "Urbanova",
        ("Açaí 500ml", "Açaí 300ml", "Copo da Felicidade", "Vitamina de Morango"),
        {"embalagem": 0.35, "temperatura": 0.30},
    ),
    Restaurant(
        "rest_006",
        "Cantina Bella Massa",
        "massas",
        "Bosque dos Eucaliptos",
        ("Lasanha Bolonhesa", "Fettuccine Alfredo", "Nhoque ao Sugo", "Ravióli de Queijo"),
        {"tempo_entrega": 0.15},
    ),
    Restaurant(
        "rest_007",
        "Churrasco Gaúcho Express",
        "churrasco",
        "Vila Industrial",
        ("Prato Executivo Picanha", "Espetinho Misto", "Costela no Bafo", "Linguiça Artesanal"),
        {"preco": 0.30, "sabor": 0.05},
    ),
    Restaurant(
        "rest_008",
        "Doceria Ateliê Doce",
        "doces",
        "Jardim Esplanada",
        ("Brigadeiro Gourmet", "Bolo de Pote", "Cookie Recheado", "Torta de Limão"),
        {"embalagem": 0.25},
    ),
)


@dataclass(frozen=True)
class SyntheticReview:
    id: str
    restaurant_id: str
    item: str
    text: str
    rating: int
    created_at: str  # ISO date
    aspects: dict[str, str]
    category: str
    bairro: str


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _neg_prob(rest: Restaurant, aspect: Aspect, review_date: date, end: date) -> float:
    p = BASE_NEG_PROB + rest.weak_aspects.get(aspect, 0.0)
    if (
        aspect == "tempo_entrega"
        and rest.late_trend
        and (end - review_date).days < TREND_WINDOW_DAYS
    ):
        p = TREND_NEG_PROB
    return _clamp(p, 0.0, 0.95)


def _add_noise(text: str, rng: random.Random) -> str:
    """Simula escrita informal: minúsculas, sem acento, pontuação solta."""
    r = rng.random()
    if r < 0.10:
        text = text.lower()
    elif r < 0.15:
        nfkd = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in nfkd if not unicodedata.combining(c))
    if rng.random() < 0.08:
        text = text.rstrip(".!")
    return text.strip()


def _build_review(
    idx: int, rest: Restaurant, end: date, days: int, rng: random.Random
) -> SyntheticReview:
    review_date = end - timedelta(days=rng.randrange(days))
    item = rng.choice(rest.menu)

    aspects: dict[Aspect, Polarity] = {}
    for a in ASPECTS:
        if rng.random() < MENTION_PROB[a]:
            aspects[a] = "neg" if rng.random() < _neg_prob(rest, a, review_date, end) else "pos"
    if not aspects:  # garante ao menos um aspecto
        a = rng.choice(("sabor", "tempo_entrega"))
        aspects[a] = "neg" if rng.random() < _neg_prob(rest, a, review_date, end) else "pos"

    n_neg = sum(p == "neg" for p in aspects.values())
    n_pos = len(aspects) - n_neg
    score = 3.8 + 0.4 * min(n_pos, 3) - 1.4 * n_neg + rng.gauss(0, 0.45)
    rating = round(_clamp(score, 1, 5))

    parts: list[str] = []
    ordered = list(aspects.items())
    rng.shuffle(ordered)
    for a, pol in ordered:
        minutes = rng.randint(70, 120) if pol == "neg" else rng.randint(18, 35)
        parts.append(rng.choice(TEMPLATES[a][pol]).format(item=item, min=minutes))

    bucket = "low" if rating <= 2 else "mid" if rating == 3 else "high"
    text = (
        rng.choice(OPENERS).format(item=item) + " ".join(parts) + " " + rng.choice(CLOSERS[bucket])
    )
    text = _add_noise(text, rng)

    return SyntheticReview(
        id=f"rev_{idx:06d}",
        restaurant_id=rest.restaurant_id,
        item=item,
        text=text,
        rating=rating,
        created_at=review_date.isoformat(),
        aspects=dict(aspects),
        category=rest.category,
        bairro=rest.bairro,
    )


def generate(n: int, seed: int, end: date, days: int) -> list[SyntheticReview]:
    if n < 1 or days < 1:
        raise ValueError("n and days must be positive")
    rng = random.Random(seed)
    return [_build_review(i + 1, rng.choice(RESTAURANTS), end, days, rng) for i in range(n)]


def write_jsonl(reviews: list[SyntheticReview], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in reviews:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def write_csv(reviews: list[SyntheticReview], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(reviews[0]).keys()))
        writer.writeheader()
        for r in reviews:
            row = asdict(r)
            row["aspects"] = json.dumps(row["aspects"], ensure_ascii=False)
            writer.writerow(row)


def write_restaurants(path: Path) -> None:
    payload = [
        {
            "restaurant_id": r.restaurant_id,
            "name": r.name,
            "category": r.category,
            "bairro": r.bairro,
            "menu": list(r.menu),
        }
        for r in RESTAURANTS
    ]  # Perfis de problema ficam fora: são o segredo da simulação.
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_against_schema(reviews: list[SyntheticReview]) -> None:
    """Valida contra partner_copilot.schemas.Review (requer `pip install -e .`)."""
    from partner_copilot.schemas import Review  # import tardio: script roda sem o pacote

    for r in reviews:
        Review.model_validate(asdict(r))
    print(f"[ok] {len(reviews)} reviews válidas no schema Review.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--n", type=int, default=3000, help="número de reviews (default: 3000)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--days", type=int, default=90, help="janela histórica em dias")
    p.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=date.today(),
        help="última data possível (ISO). Fixe para reprodutibilidade total.",
    )
    p.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    p.add_argument("--validate", action="store_true", help="valida contra o schema Review")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    reviews = generate(args.n, args.seed, args.end_date, args.days)
    out = args.out_dir / f"reviews.{args.format}"
    (write_jsonl if args.format == "jsonl" else write_csv)(reviews, out)
    write_restaurants(args.out_dir / "restaurants.json")

    neg_rate = sum("neg" in r.aspects.values() for r in reviews) / len(reviews)
    print(f"[ok] {len(reviews)} reviews -> {out} ({neg_rate:.0%} com ao menos um aspecto negativo)")

    if args.validate:
        validate_against_schema(reviews)


if __name__ == "__main__":
    main()
