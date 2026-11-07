"""Freeze ABSA splits and audit sentence leakage using the blind gold texts."""

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from generate_synthetic_data import TEMPERATURE_TEMPLATES, TEMPLATES
from partner_copilot.data_splits import file_key, load_absa_train_pool, read_jsonl

ROOT = Path(__file__).resolve().parents[1]
SEED = 2718
AMBIGUOUS = {
    "O gosto de {item} estava bem diferente do habitual.": "different_without_judgment",
    "O entregador chegou em {min} minutos.": "duration_without_judgment",
    "Pedido feito e entregue em {min} min.": "duration_without_judgment",
}


def normalize(text):
    plain = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())


def sentences(text):
    return [part for raw in re.split(r"[.!?\n]+", text) if (part := normalize(raw))]


def template_key(template):
    return sentences(template.format(item="__item__", min="__min__"))[0]


def rank(value):
    return hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()


def overlap(gold, reference):
    known = {sentence for row in reference for sentence in sentences(row.text)}
    occurrences = [sentence for row in gold for sentence in sentences(row["text"])]
    unique = set(occurrences)
    return {
        "matching_occurrences": sum(s in known for s in occurrences),
        "total_occurrences": len(occurrences),
        "matching_unique": len(unique & known),
        "total_unique": len(unique),
    }


def build_manifest():
    split_dir = ROOT / "data/splits"
    pool = load_absa_train_pool(split_dir)
    original = json.loads((split_dir / "manifest.json").read_text(encoding="utf-8"))
    blind = ROOT / "data/gold/reviews_100.blind.jsonl"
    annotation = ROOT / "data/gold/annotation_manifest.json"
    annotation_meta = json.loads(annotation.read_text(encoding="utf-8"))
    if hashlib.sha256(blind.read_bytes()).hexdigest() != annotation_meta["blind_sample_sha256"]:
        raise ValueError("Blind gold hash mismatch")
    gold = read_jsonl(blind)
    if sorted(row["id"] for row in gold) != original["ids"]["gold"]:
        raise ValueError("Blind gold IDs mismatch")
    gold_texts = {tuple(sentences(row["text"])) for row in gold}

    restaurants = ROOT / "data/raw/restaurants.json"
    menus = json.loads(restaurants.read_text(encoding="utf-8"))
    items = {normalize(item) for restaurant in menus for item in restaurant["menu"]}
    pattern = "|".join(re.escape(item) for item in sorted(items, key=lambda s: (-len(s), s)))
    item_pattern = re.compile(rf"(?<!\w)(?:{pattern})(?!\w)")
    catalog = {}
    sources = list(TEMPLATES.items()) + [
        ("temperatura", pool) for pool in TEMPERATURE_TEMPLATES.values()
    ]
    for aspect, polarities in sources:
        for polarity, templates in polarities.items():
            for template in templates:
                key = template_key(template)
                label = (aspect, polarity)
                if key in catalog and catalog[key] != label:
                    raise ValueError("A template family maps to multiple labels")
                catalog[key] = label
    ambiguous = {template_key(text): reason for text, reason in AMBIGUOUS.items()}

    def families(text):
        keys = set()
        for sentence in sentences(text):
            masked = item_pattern.sub("__item__", sentence).removeprefix("sobre __item__:").strip()
            keys.add(re.sub(r"\b\d+\b", "__min__", masked))
        return keys & catalog.keys()

    groups = defaultdict(list)
    for row in pool:
        groups[tuple(sentences(row.text))].append(row)
    excluded = defaultdict(dict)
    clean = []
    family_by_id = {}
    for text, group in groups.items():
        group.sort(key=lambda row: row.id)
        labels = {tuple(sorted(row.aspects.items())) for row in group}
        if text in gold_texts or len(labels) != 1:
            reason = "gold_normalized_text" if text in gold_texts else "conflicting_duplicate"
            excluded[reason].update(dict.fromkeys(row.id for row in group))
            continue
        row, *duplicates = group
        if duplicates:
            excluded["duplicate"].update({other.id: row.id for other in duplicates})
        keys = families(row.text)
        if {catalog[key] for key in keys} != set(row.aspects.items()):
            raise ValueError(f"Template recovery disagrees with generator labels: {row.id}")
        reasons = sorted({ambiguous[key] for key in keys & ambiguous.keys()})
        if reasons:
            excluded["ambiguous"][row.id] = reasons
            continue
        family_by_id[row.id] = keys
        clean.append(row)

    frequencies = Counter(key for keys in family_by_id.values() for key in keys)
    heldout = set()
    for label in sorted(set(catalog.values())):
        eligible = [key for key, pair in catalog.items() if pair == label and frequencies[key] >= 5]
        heldout.add(min(eligible, key=rank))
    development, template_test = [], []
    for row in clean:
        target = template_test if family_by_id[row.id] & heldout else development
        target.append(row)
    development.sort(key=lambda row: rank(row.id))
    validation_ids = set()
    # Keep every aspect/polarity represented in the early-stopping set.
    for aspect, polarity in sorted(set(catalog.values())):
        candidates = [row for row in development if row.aspects.get(aspect) == polarity]
        needed = max(0, 5 - sum(row.id in validation_ids for row in candidates))
        available = [row.id for row in candidates if row.id not in validation_ids]
        validation_ids.update(available[:needed])
    for row in development:
        if len(validation_ids) >= len(development) // 10:
            break
        validation_ids.add(row.id)
    validation = [row for row in development if row.id in validation_ids]
    train = [row for row in development if row.id not in validation_ids]
    splits = {"train": train, "validation": validation, "template_test": template_test}
    ids = {name: sorted(row.id for row in rows) for name, rows in splits.items()}
    allocated = [identifier for partition in ids.values() for identifier in partition]
    discarded = [identifier for reasons in excluded.values() for identifier in reasons]
    if len(set(allocated + discarded)) != len(pool) or len(allocated + discarded) != len(pool):
        raise ValueError("Train pool allocation is incomplete or overlapping")
    if set(allocated) & set(original["gold_reserved_ids"]):
        raise ValueError("Reserved gold ID leaked")
    if any(family_by_id[row.id] & heldout for row in train + validation):
        raise ValueError("Held-out template leaked into development")
    support = {
        name: dict(
            sorted(Counter(f"{a}:{p}" for row in rows for a, p in row.aspects.items()).items())
        )
        for name, rows in splits.items()
    }
    if any(len(counts) != len(set(catalog.values())) for counts in support.values()):
        raise ValueError("An ABSA partition lacks a polarity/aspect pair")
    if min(support["validation"].values()) < 5:
        raise ValueError("Insufficient validation coverage")

    seen = set().union(*(family_by_id[row.id] for row in train))

    def strata(rows):
        groups = {name: [] for name in ("seen_only", "unseen_only", "mixed", "unmapped")}
        for identifier, keys in rows:
            if not keys:
                bucket = "unmapped"
            elif keys <= seen:
                bucket = "seen_only"
            elif keys.isdisjoint(seen):
                bucket = "unseen_only"
            else:
                bucket = "mixed"
            groups[bucket].append(identifier)
        return {name: sorted(group) for name, group in groups.items()}

    return {
        "protocol": "absa-splits-v1",
        "seed": SEED,
        "input_sha256_lf": {
            path.relative_to(ROOT).as_posix(): file_key(path)
            for path in (
                split_dir / "train_pool.jsonl",
                split_dir / "manifest.json",
                blind,
                annotation,
                restaurants,
                ROOT / "scripts/generate_synthetic_data.py",
            )
        },
        "gold_annotation_status": annotation_meta["status"],
        "counts": {
            "train_pool": len(pool),
            "gold": len(gold),
            **{k: len(v) for k, v in ids.items()},
        },
        "ids": ids,
        "aspect_polarity_counts": support,
        "exclusions": {key: dict(sorted(value.items())) for key, value in sorted(excluded.items())},
        "duplicate_review_groups": sum(len(group) > 1 for group in groups.values()),
        "duplicate_reviews_beyond_first": sum(len(group) - 1 for group in groups.values()),
        "heldout_families": [
            {"key": key, "label": catalog[key], "reviews": frequencies[key]}
            for key in sorted(heldout)
        ],
        "gold_literal_overlap": {"pool": overlap(gold, pool), "train": overlap(gold, train)},
        "gold_template_strata_ids": strata((row["id"], families(row["text"])) for row in gold),
        "template_test_strata_ids": strata((row.id, family_by_id[row.id]) for row in template_test),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest()
    path = ROOT / "data/absa/splits-v1.json"
    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text(encoding="utf-8") != content:
            raise SystemExit("ABSA manifest differs from registered inputs")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "counts": manifest["counts"],
                "literal_overlap": manifest["gold_literal_overlap"],
                "duplicates": manifest["duplicate_reviews_beyond_first"],
                "exclusions": {key: len(value) for key, value in manifest["exclusions"].items()},
                "gold_strata": {
                    key: len(value) for key, value in manifest["gold_template_strata_ids"].items()
                },
                "test_strata": {
                    key: len(value) for key, value in manifest["template_test_strata_ids"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
