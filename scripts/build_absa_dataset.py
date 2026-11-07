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
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    from transformers import AutoTokenizer

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
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL, revision=REVISION, token=False, local_files_only=args.local_files_only
    )
    report = {
        "dataset_version": "absa-chat-v1",
        "model": MODEL,
        "revision": REVISION,
        "transformers_version": version("transformers"),
        "chat_template_sha256": hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        "splits_manifest_sha256_lf": file_key(split_path),
        "train_budget": 1500,
        "aspect_order": ASPECTS,
        "splits": {},
    }
    exports = {}
    for name, ids in (("train", train_ids), ("validation", validation_ids)):
        rows = [pool[identifier] for identifier in ids]
        examples = [example(row) for row in rows]
        content = "".join(compact(row) + "\n" for row in examples)
        exports[DATA / f"{name}-v1.jsonl"] = content
        report["splits"][name] = {
            **distribution(rows),
            "chat_tokens": token_stats(tokenizer, examples),
            "sha256_lf": hashlib.sha256(content.encode()).hexdigest(),
        }
    longest = max(split["chat_tokens"]["max"] for split in report["splits"].values())
    report["suggested_max_length"] = 2 ** (longest - 1).bit_length()
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    for path, content in exports.items():
        write_or_check(path, content, args.check)
    write_or_check(DATA / "dataset-v1.json", report_text, args.check)
    print(report_text)


if __name__ == "__main__":
    main()
