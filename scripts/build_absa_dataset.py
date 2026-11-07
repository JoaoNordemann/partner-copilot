"""Export the audited ABSA train and validation splits and profile Qwen token lengths."""

import argparse
import hashlib
import json
import math
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from statistics import median

from generate_synthetic_data import ASPECTS
from partner_copilot.data_splits import file_key, load_absa_train_pool

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/absa"
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
CORPUS_COMMIT = "d6aedfd3eff5acc58609ee75e04d8c46fa6a532e"
CORPUS_GENERATOR_SHA = "b8da98d182c18fd9e401fa58adabeb3331f3ccc07f195375695aa30fe90b58a0"
INSTRUCTION = (
    "Classifique os aspectos sabor, tempo_entrega, temperatura, embalagem, preco e atendimento. "
    "Use pos ou neg e omita aspectos sem opinião clara. "
    'Responda só com um objeto JSON com a chave "aspects".'
)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def example(review):
    if set(review.aspects) - set(ASPECTS):
        raise ValueError(f"Unsupported aspect in {review.id}")
    aspects = {aspect: review.aspects[aspect] for aspect in ASPECTS if aspect in review.aspects}
    return {
        "id": review.id,
        "messages": [
            {"role": "user", "content": f"{INSTRUCTION}\n\nReview:\n{review.text}"},
            {"role": "assistant", "content": compact({"aspects": aspects})},
        ],
    }


def distribution(rows):
    counts = Counter(pair for row in rows for pair in row.aspects.items())
    by_size = Counter(min(len(row.aspects), 3) for row in rows)
    return {
        "reviews": len(rows),
        "by_aspect_polarity": {
            aspect: {polarity: counts[aspect, polarity] for polarity in ("pos", "neg")}
            for aspect in ASPECTS
        },
        "aspects_per_review": {
            "0": by_size[0],
            "1": by_size[1],
            "2": by_size[2],
            "3+": by_size[3],
        },
        "mixed_polarity_reviews": sum(set(row.aspects.values()) == {"pos", "neg"} for row in rows),
    }


def token_stats(tokenizer, examples):
    encoded = tokenizer.apply_chat_template(
        [row["messages"] for row in examples],
        tokenize=True,
        add_generation_prompt=False,
        truncation=False,
        return_dict=True,
    )
    lengths = sorted(map(len, encoded["input_ids"]))
    return {
        "min": lengths[0],
        "median": median(lengths),
        "p95": lengths[math.ceil(0.95 * len(lengths)) - 1],
        "max": lengths[-1],
        "total": sum(lengths),
    }


def write_or_check(path, content, check):
    if check:
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"ABSA artifact differs: {path}")
    else:
        path.write_bytes(content.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-static", action="store_true", help="Verify data without tokenizer")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    split_path = DATA / "splits-v1.json"
    manifest = json.loads(split_path.read_text(encoding="utf-8"))
    for relative, checksum in manifest["input_sha256_lf"].items():
        if file_key(ROOT / relative) != checksum:
            raise ValueError(f"ABSA split input changed: {relative}")
    split_dir = ROOT / "data/splits"
    pool = {row.id: row for row in load_absa_train_pool(split_dir)}
    reserved = set(manifest["ids"]["template_test"])
    train_ids, validation_ids = (manifest["ids"][name] for name in ("train", "validation"))
    if (
        len(set(train_ids + validation_ids)) != len(train_ids) + len(validation_ids)
        or set(train_ids + validation_ids) & reserved
        or len(train_ids) > 1500
    ):
        raise ValueError("Invalid ABSA training allocation")
    corpus_path = ROOT / "data/raw/reviews.jsonl"
    corpus_manifest = json.loads((split_dir / "manifest.json").read_text(encoding="utf-8"))
    corpus_hash = file_key(corpus_path)
    if corpus_hash != corpus_manifest["source_sha256_lf"]:
        raise ValueError("ABSA corpus hash differs from the original split manifest")
    gold_path = ROOT / "data/gold/aspects_100.human.jsonl"
    gold_manifest_path = ROOT / "data/gold/human_review_manifest.json"
    gold_manifest = json.loads(gold_manifest_path.read_text(encoding="utf-8"))
    gold_hash = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    if gold_hash != gold_manifest["annotations_sha256"]:
        raise ValueError("Human gold differs from its frozen manifest")
    report = {
        "dataset_version": "absa-chat-v1",
        "model": MODEL,
        "revision": REVISION,
        "provenance": {
            "origin": "synthetic_generator_labels",
            "generator_commit": CORPUS_COMMIT,
            "generator_sha256_lf": CORPUS_GENERATOR_SHA,
            "corpus_sha256_lf": corpus_hash,
            "generator_parameters": {"n": 3000, "seed": 42, "end_date": "2026-11-01", "days": 90},
        },
        "split_counts": {
            key: manifest["counts"][key] for key in ("train", "validation", "template_test", "gold")
        },
        "splits_manifest_sha256_lf": file_key(split_path),
        "gold_reference": {
            "version": gold_manifest["version"],
            "annotations_sha256": gold_hash,
            "review_manifest_sha256_lf": file_key(gold_manifest_path),
        },
        "train_budget": 1500,
        "aspect_order": list(ASPECTS),
        "splits": {},
    }
    tokenizer = None
    if not args.check_static:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            MODEL, revision=REVISION, token=False, local_files_only=args.local_files_only
        )
        report["transformers_version"] = version("transformers")
        report["chat_template_sha256"] = hashlib.sha256(
            tokenizer.chat_template.encode()
        ).hexdigest()
    exports = {}
    for name, ids in (("train", train_ids), ("validation", validation_ids)):
        rows = [pool[identifier] for identifier in ids]
        examples = [example(row) for row in rows]
        content = "".join(compact(row) + "\n" for row in examples)
        exports[DATA / f"{name}-v1.jsonl"] = content
        report["splits"][name] = {
            **distribution(rows),
            "sha256_lf": hashlib.sha256(content.encode()).hexdigest(),
        }
        if tokenizer is not None:
            report["splits"][name]["chat_tokens"] = token_stats(tokenizer, examples)
    for path, content in exports.items():
        write_or_check(path, content, args.check or args.check_static)
    report_path = DATA / "dataset-v1.json"
    if args.check_static:
        frozen = json.loads(report_path.read_text(encoding="utf-8"))
        for key in ("transformers_version", "chat_template_sha256", "suggested_max_length"):
            del frozen[key]
        for split in frozen["splits"].values():
            del split["chat_tokens"]
        if frozen != report:
            raise ValueError("ABSA manifest differs from static dataset and inputs")
        print("Verified ABSA dataset, split counts and provenance without the tokenizer.")
        return
    longest = max(split["chat_tokens"]["max"] for split in report["splits"].values())
    report["suggested_max_length"] = 2 ** (longest - 1).bit_length()
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    write_or_check(report_path, report_text, args.check)
    print(report_text)


if __name__ == "__main__":
    main()
