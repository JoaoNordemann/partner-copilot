"""Extract three known historical cases; never runs retrieval or inference."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "success",
        "Sucesso: atendimento prestativo",
        "reports/final-v3/generation-v3-new.jsonl",
        "n17",
        "O parser v3 aceitou a resposta. Na leitura de IA, a review sustenta "
        "a avaliação positiva do atendimento.",
    ),
    (
        "abstention",
        "Abstenção correta: marca do forno",
        "reports/final-v3/generation-v3-new.jsonl",
        "n20",
        "Sem evidência sobre marca de forno no contexto. "
        "Abstenção considerada correta na leitura de IA.",
    ),
    (
        "failure",
        "Limitação: elogio seletivo",
        "reports/final-v3/generation-v3-new.jsonl",
        "n12",
        "Falha confirmada pelo autor, em leitura própria. A review elogia "
        "o custo-benefício e relata gosto ruim no final.",
    ),
]


def render():
    corpus_path = ROOT / "data/eval/human-v2/corpus.jsonl"
    corpus_bytes = corpus_path.read_bytes()
    corpus_hash = hashlib.sha256(corpus_bytes.replace(b"\r\n", b"\n")).hexdigest()
    corpus = {r["id"]: r for r in map(json.loads, corpus_bytes.decode().splitlines())}
    examples = []
    for identifier, title, source, question_id, note in CASES:
        raw = (ROOT / source).read_bytes()
        row = next(
            r for r in map(json.loads, raw.decode().splitlines()) if r["question_id"] == question_id
        )
        assert row["snapshot_sha256_lf"]["corpus"] == corpus_hash
        context = []
        for doc in row["context"]:
            review = corpus[doc["review_id"]]
            assert review["text"] == doc["text"]
            context.append(review)
        examples.append(
            {
                "id": identifier,
                "title": title,
                "note": note,
                "source_file": source,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "corpus_sha256_lf": corpus_hash,
                "record": row,
                "full_context_reviews": context,
            }
        )
    return (
        json.dumps(
            {"schema_version": "demo-history-v1", "new_inference": False, "examples": examples},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "configs/demo-examples.json"
    text = render()
    if args.check:
        assert path.read_text(encoding="utf-8") == text, "Historical examples changed"
        print("Three historical demo examples verified; no inference.")
    else:
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
