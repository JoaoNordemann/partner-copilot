#!/usr/bin/env python
"""Check reserved evaluation integrity without revealing questions or calling models."""

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/eval/reserved-final-v1"


def text_hash(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def canonical(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", text))


def check(folder: Path, verify_runtime: bool = False) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for filename, key in [
        ("questions.jsonl", "questions_sha256_lf"),
        ("label-audit.jsonl", "label_audit_sha256_lf"),
    ]:
        if text_hash(folder / filename) != manifest[key]:
            raise ValueError("Reserved artifact checksum mismatch")
    corpus_path = folder / manifest["corpus_relative_path"]
    if text_hash(corpus_path) != manifest["corpus_sha256_lf"]:
        raise ValueError("Reserved corpus checksum mismatch")
    corpus = {r["id"]: r for r in load_rows(corpus_path)}
    questions = load_rows(folder / "questions.jsonl")
    if [q["id"] for q in questions] != manifest["question_ids"]:
        raise ValueError("Question IDs/order differ")
    if len(questions) != manifest["question_count"] or len(questions) != 10:
        raise ValueError("Requires ten reserved questions")
    if sum(q["deve_abster"] for q in questions) != manifest["negative_count"]:
        raise ValueError("Negative composition differs")
    if manifest["negative_count"] != 3:
        raise ValueError("Requires three negatives")
    previous = []
    for path in [
        ROOT / "data/eval/human-v2/questions.jsonl",
        ROOT / "data/eval/json-verification-v1/questions.jsonl",
        ROOT / "data/eval/v3-final-check/questions.jsonl",
    ]:
        previous.extend(load_rows(path))
    old_texts = {canonical(q["pergunta"]) for q in previous}
    new_texts = {canonical(q["pergunta"]) for q in questions}
    if len(new_texts) != 10 or old_texts & new_texts:
        raise ValueError("Duplicate question text; check before freezing")
    audits = {a["question_id"]: a for a in load_rows(folder / "label-audit.jsonl")}
    if set(audits) != set(manifest["question_ids"]):
        raise ValueError("Audit coverage differs")
    for q in questions:
        if type(q["deve_abster"]) is not bool or q["deve_abster"] != (not q["relevantes"]):
            raise ValueError("Abstention/relevance inconsistent")
        if set(q["filtros"]) != {"restaurant_id", "item"}:
            raise ValueError("Only the declared structural filters are allowed")
        scope = {
            i: r for i, r in corpus.items() if all(r.get(k) == v for k, v in q["filtros"].items())
        }
        if not scope or len(q["relevantes"]) != len(set(q["relevantes"])):
            raise ValueError("Empty scope or duplicate labels")
        if not set(q["relevantes"]) <= scope.keys():
            raise ValueError("Relevant source outside scope")
        audit = audits[q["id"]]
        if audit["scope_review_ids"] != sorted(scope):
            raise ValueError("Audit scope differs")
        if audit["relevant_source_texts"] != {i: corpus[i]["text"] for i in q["relevantes"]}:
            raise ValueError("Audit source text differs")
    commit = manifest["frozen_source_commit"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Source commit must be immutable")
    for relative, expected in manifest["frozen_files_sha256_lf"].items():
        blob = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)
        actual = hashlib.sha256(blob.decode("utf-8").replace("\r\n", "\n").encode()).hexdigest()
        if actual != expected:
            raise ValueError("Frozen source snapshot differs")
        if verify_runtime and text_hash(ROOT / relative) != expected:
            raise ValueError("Working runtime differs from frozen generation core")
    policy = manifest["execution_policy"]
    if (
        policy["planned_rounds"],
        policy["max_new_inference_per_question"],
        policy["corrective_retries"],
    ) != (1, 1, 0):
        raise ValueError("Single-round policy differs")
    return {
        "version": manifest["version"],
        "question_count": len(questions),
        "positive_count": len(questions) - manifest["negative_count"],
        "negative_count": manifest["negative_count"],
        "integrity": "ok",
        "runtime_snapshot_checked": verify_runtime,
        "questions_printed": False,
        "new_retrieval_or_generation_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-runtime", action="store_true")
    args = parser.parse_args()
    print(json.dumps(check(FOLDER, args.verify_runtime), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
