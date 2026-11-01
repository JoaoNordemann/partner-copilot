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

# Text fragments express exactly one labeled aspect. Food-specific language is selected below.
TEMPLATES: Final[dict[Aspect, dict[Polarity, list[str]]]] = {
    "sabor": {
        "pos": [
            "Gostei bastante do sabor de {item}.",
            "Gostei muito de {item}.",
            "O sabor estava ótimo, pediria {item} de novo.",
            "Achei {item} uma delícia.",
            "{item} veio com o sabor que eu esperava.",
            "Dessa vez acertaram no sabor de {item}.",
            "O sabor de {item} estava muito bom.",
            "Aqui em casa todo mundo gostou de {item}.",
            "O gosto de {item} me surpreendeu pra melhor.",
            "{item} estava uma delícia, gostei até o fim.",
            "O sabor de {item} valeu o pedido.",
            "Nada a reclamar do sabor de {item}.",
        ],
        "neg": [
            "Não gostei do sabor de {item}.",
            "{item} veio com um gosto estranho.",
            "Achei {item} bem sem graça.",
            "O sabor de {item} deixou a desejar.",
            "{item} estava com gosto de produto velho.",
            "Não consegui terminar {item}, o gosto não estava bom.",
            "Já pedi {item} antes e dessa vez o sabor estava pior.",
            "{item} estava com um gosto ruim no final.",
            "Pelo sabor, não pediria {item} de novo.",
            "Esperava mais do sabor de {item}.",
            "O gosto de {item} estava bem diferente do habitual.",
            "{item} não estava gostoso como das outras vezes.",
        ],
    },
    "tempo_entrega": {
        "pos": [
            "Chegou em {min} minutos, antes do previsto.",
            "Em {min} min já estava aqui.",
            "O pedido levou só {min} minutos pra chegar.",
            "A entrega foi rápida, uns {min} minutos.",
            "Entregaram dentro do prazo.",
            "Chegou no horário que o app mostrou.",
            "Não precisei esperar muito, deu {min} min.",
            "Dessa vez chegou rapidinho, em {min} minutos.",
            "O entregador chegou em {min} minutos.",
            "Pedido feito e entregue em {min} min.",
        ],
        "neg": [
            "Levou {min} minutos pra chegar, passou bastante do prazo.",
            "Fiquei esperando {min} min pelo pedido.",
            "Esperei quase duas horas e já tinha passado da previsão.",
            "A entrega demorou demais, deu {min} minutos.",
            "O prazo passou e o pedido nada de chegar.",
            "Chegou bem depois do horário mostrado no app.",
            "Foram {min} minutos de espera, atrapalhou meu almoço.",
            "Pedi com antecedência e mesmo assim atrasou bastante.",
            "O pedido levou {min} min e eu já estava desistindo.",
            "Mais de uma hora esperando, muito além do combinado.",
        ],
    },
    # Temperature fragments come from TEMPERATURE_TEMPLATES according to the item.
    "temperatura": {"pos": [], "neg": []},
    "embalagem": {
        "pos": [
            "A embalagem veio bem fechada.",
            "A embalagem protegeu bem {item}.",
            "A sacola estava lacrada e tudo no lugar.",
            "Embalagem firme, nada ficou solto.",
            "Capricharam na embalagem de {item}.",
            "Tudo bem acomodado, sem embalagem aberta.",
            "O lacre estava inteiro quando recebi.",
            "Gostei de como embalaram {item}.",
            "Veio numa embalagem bem resistente.",
            "Dava pra ver o cuidado com a embalagem.",
        ],
        "neg": [
            "A embalagem de {item} chegou aberta.",
            "Veio sem lacre na sacola.",
            "A tampa veio solta, não gostei disso.",
            "A embalagem rasgou no caminho.",
            "A embalagem não segurou {item}, veio tudo bagunçado.",
            "A sacola estava amassada e a embalagem abriu.",
            "Precisam melhorar essa embalagem de {item}.",
            "O recipiente era fraco e chegou danificado.",
            "Não fecharam direito a embalagem.",
            "O lacre já estava rompido quando recebi.",
        ],
    },
    "preco": {
        "pos": [
            "Achei o preço justo.",
            "Valeu o que paguei por {item}.",
            "Bom custo-benefício nesse {item}.",
            "Pelo valor, achei uma boa compra.",
            "O preço de {item} estava bom.",
            "Gostei da porção pelo valor cobrado.",
            "Não achei caro pelo que veio.",
            "O valor coube no bolso.",
        ],
        "neg": [
            "Achei caro pelo que veio.",
            "{item} não vale o valor cobrado.",
            "A porção de {item} era pequena pro preço.",
            "O preço subiu demais.",
            "Paguei caro e esperava mais quantidade.",
            "O custo-benefício de {item} foi ruim.",
            "Em outros lugares pago menos por {item}.",
            "Não achei o preço justo.",
        ],
    },
    "atendimento": {
        "pos": [
            "Responderam minha dúvida rapidinho no chat.",
            "O pessoal foi educado quando entrei em contato.",
            "Consegui falar com o restaurante sem dificuldade.",
            "Me atenderam bem quando mandei mensagem.",
            "O atendimento foi atencioso.",
            "Tiraram minha dúvida com paciência.",
            "Gostei da forma como responderam no chat.",
            "Falei com o restaurante e foram bem prestativos.",
        ],
        "neg": [
            "Mandei mensagem e ninguém respondeu.",
            "O atendimento no chat foi bem ruim.",
            "Não consegui falar com ninguém do restaurante.",
            "Foram grossos quando entrei em contato.",
            "Demoraram demais pra responder minha dúvida.",
            "Fiquei sem resposta no chat.",
            "O restaurante ignorou minhas mensagens.",
            "Precisam melhorar o atendimento ao cliente.",
        ],
    },
}

TEMPERATURE_TEMPLATES: Final[dict[str, dict[Polarity, list[str]]]] = {
    "hot": {
        "pos": [
            "{item} chegou bem quente.",
            "Ainda estava quentinho quando abri.",
            "Não precisei esquentar {item}.",
            "A temperatura de {item} estava ótima.",
            "Veio quente como eu esperava.",
            "{item} ainda estava saindo fumaça.",
            "Chegou quente, deu pra comer na hora.",
            "Mantiveram o calor de {item} até a entrega.",
        ],
        "neg": [
            "{item} chegou frio.",
            "Tive que esquentar {item} no micro-ondas.",
            "Já estava morno quando abri.",
            "Veio frio, perdeu bastante a graça.",
            "{item} esfriou antes de chegar aqui.",
            "Esperava {item} quente, mas veio frio.",
            "Precisei requentar antes de comer.",
            "A comida já não estava quente ao chegar.",
        ],
    },
    "cold": {
        "pos": [
            "Veio bem gelado, na temperatura certa.",
            "Veio refrigerado como deveria.",
            "A temperatura de {item} estava boa.",
            "Veio gelado e pronto pra consumir.",
            "A refrigeração de {item} foi mantida na entrega.",
            "Veio geladinho, do jeito certo.",
            "{item} chegou na temperatura que eu esperava.",
            "Chegou fresco e bem refrigerado.",
        ],
        "neg": [
            "{item} chegou quente, devia ter vindo refrigerado.",
            "Veio sem refrigeração, já estava morno.",
            "{item} perdeu o gelado no caminho.",
            "A temperatura de {item} estava alta demais.",
            "Era pra vir gelado, mas chegou em temperatura ambiente.",
            "{item} esquentou durante a entrega.",
            "Não mantiveram {item} refrigerado.",
            "Veio morno e tive receio de consumir.",
        ],
    },
    "ambient": {
        "pos": [
            "{item} veio bem conservado, sem sinal de calor excessivo.",
            "A temperatura de {item} estava adequada.",
            "{item} não pegou calor no caminho.",
            "Veio protegido do calor, como deveria.",
        ],
        "neg": [
            "{item} pegou calor demais no caminho.",
            "Veio quente de ter ficado no sol.",
            "O calor da entrega alterou a textura de {item}.",
            "{item} veio abafado e quente demais.",
        ],
    },
}

OPENERS: Final[list[str]] = [
    "Pedi {item}.",
    "Sobre {item}:",
    "Meu pedido foi {item}.",
    "Já é a segunda vez que peço aqui.",
    "Foi minha primeira compra aqui.",
    "Recebi agora meu pedido.",
    "Pedi pra dividir aqui em casa.",
    "Resolvi experimentar {item}.",
]
CLOSERS: Final[dict[str, list[str]]] = {
    "low": [
        "Não pediria de novo.",
        "Fiquei decepcionado.",
        "Não valeu a pena.",
        "Espero que melhorem.",
        "Foi uma experiência ruim.",
    ],
    "mid": [
        "Dá pra melhorar.",
        "No geral, foi razoável.",
        "Fiquei dividido sobre o pedido.",
        "Algumas coisas precisam melhorar.",
        "Minha experiência foi mais ou menos.",
    ],
    "mixed": [
        "Gostei de algumas coisas, mas tem o que melhorar.",
        "Voltaria se resolvessem esse problema.",
        "O pedido teve pontos bons e ruins.",
        "Não foi tudo como eu esperava.",
        "Tomara que acertem isso na próxima.",
    ],
    "high": [
        "Pediria novamente.",
        "Gostei da experiência.",
        "Valeu a compra.",
        "Vou pedir de novo.",
        "Recomendo esse lugar.",
    ],
}


def temperature_profile(item: str, category: str) -> str:
    """Choose the expected serving temperature, including mixed-menu restaurants."""
    if category == "açaí" or item in {
        "Combo 20 Peças",
        "Temaki Salmão",
        "Bolo de Pote",
        "Torta de Limão",
    }:
        return "cold"
    if category == "doces":
        return "ambient"
    return "hot"


def _render_aspect(
    aspect: Aspect, polarity: Polarity, item: str, category: str, rng: random.Random
) -> str:
    pool = (
        TEMPERATURE_TEMPLATES[temperature_profile(item, category)][polarity]
        if aspect == "temperatura"
        else TEMPLATES[aspect][polarity]
    )
    template = rng.choice(pool)
    minutes = 0
    if "{min}" in template:
        minutes = rng.randint(70, 120) if polarity == "neg" else rng.randint(18, 35)
    return template.format(item=item.lower(), min=minutes)


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
        {"preco": 0.30, "sabor": 0.15},
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
    idx: int,
    rest: Restaurant,
    end: date,
    days: int,
    rng: random.Random,
    language_rng: random.Random,
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

    if n_neg:
        rating = min(rating, 4 if n_pos else 3)
    parts: list[str] = []
    ordered = list(aspects.items())
    language_rng.shuffle(ordered)
    for aspect, polarity in ordered:
        phrase = _render_aspect(aspect, polarity, item, rest.category, language_rng)
        parts.append(phrase)

    if rating <= 2:
        bucket = "low"
    elif rating == 3:
        bucket = "mid"
    else:
        bucket = "mixed" if n_neg else "high"
    # Most customers go straight to the point; optional wrappers must not dominate the corpus.
    if language_rng.random() < 0.20:
        parts.insert(0, language_rng.choice(OPENERS).format(item=item.lower()))
    if language_rng.random() < 0.20:
        parts.append(language_rng.choice(CLOSERS[bucket]))
    text = _add_noise(" ".join(parts), language_rng)

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
    # Stable language streams keep template edits from perturbing population statistics.
    return [
        _build_review(
            i + 1, rng.choice(RESTAURANTS), end, days, rng, random.Random(f"{seed}:language:{i}")
        )
        for i in range(n)
    ]


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
