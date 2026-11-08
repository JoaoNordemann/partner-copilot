"""Evaluate the frozen ABSA checkpoint on Kaggle, with a validation gate."""

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ASPECTS = ("sabor", "tempo_entrega", "temperatura", "embalagem", "preco", "atendimento")
CLASSES = tuple((aspect, polarity) for aspect in ASPECTS for polarity in ("pos", "neg"))
RULES = {
    "sabor": (
        r"delicia|gostoso|saboros|gosto.*(bom|otimo)",
        r"sem gosto|gosto ruim|gosto de.*velh|sem sabor|nao.*gostos|sabor.*(ruim|pior)",
    ),
    "tempo_entrega": (
        r"rapido|antes do prazo|no prazo|pontual",
        r"atras|demor|alem do combinado|hora esperando|prazo passou",
    ),
    "temperatura": (
        r"quentinh|bem quente|temperatura certa",
        r"fri[oa]|morn[oa]|esfri|sem refriger",
    ),
    "embalagem": (
        r"bem embalad|bem fechad|lacrad|embalagem.*intact",
        r"vazou|rasg|tampa solta|embalagem.*(abert|amass)|nao fecharam",
    ),
    "preco": (
        r"preco justo|valeu a pena|nao achei caro|bom custo beneficio",
        r"preco.*(subiu|aumentou|abusivo)|caro demais|nao valeu a pena|preco nao.*justo",
    ),
    "atendimento": (
        r"respondeu rapido|atencios|educad",
        r"sem retorno|ignor|nao respond|mal educad",
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(path, commit, expected_hash):
    url = f"https://raw.githubusercontent.com/JoaoNordemann/partner-copilot/{commit}/{path}"
    with urlopen(url, timeout=60) as response:
        data = response.read().replace(b"\r\n", b"\n")
    if digest(data) != expected_hash:
        raise ValueError(f"Hash mismatch: {path}")
    return data


def unique_keys(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("chave duplicada")
    return obj


def parse(raw):
    try:
        obj = json.loads(raw.strip(), object_pairs_hook=unique_keys)
        if not isinstance(obj, dict) or obj.keys() != {"aspects"}:
            raise ValueError("raiz deve conter apenas aspects")
        aspects = obj["aspects"]
        if not isinstance(aspects, dict) or any(
            key not in ASPECTS or value not in ("pos", "neg") for key, value in aspects.items()
        ):
            raise ValueError("aspecto ou polaridade fora do contrato")
        return aspects, None
    except ValueError as exc:
        return {}, str(exc)


def rows(data):
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def chat_rows(data):
    result = []
    for row in rows(data):
        user, assistant = row["messages"]
        expected, error = parse(assistant["content"])
        if error:
            raise ValueError(f"Invalid reference {row['id']}: {error}")
        _, text = user["content"].split("\n\nReview:\n", 1)
        result.append(
            {"id": row["id"], "text": text, "prompt": user["content"], "expected": expected}
        )
    return result


def output(row, raw):
    predicted, error = parse(raw)
    return {**row, "raw": raw, "predicted": predicted, "error": error}


def compact(aspects):
    return json.dumps({"aspects": aspects}, separators=(",", ":"), ensure_ascii=False)


def journal(path, inputs, raw_batches):
    result = []
    with path.open("x", encoding="utf-8") as file:
        for row, raw in zip(inputs, raw_batches, strict=True):
            record = output(row, raw)
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            file.flush()
            result.append(record)
    return result


def generate(model, tokenizer, inputs, generation, examples=()):
    import torch

    batch_size = generation["batch_size"]
    for start in range(0, len(inputs), batch_size):
        chats = [
            [*examples, {"role": "user", "content": row["prompt"]}]
            for row in inputs[start : start + batch_size]
        ]
        batch = tokenizer.apply_chat_template(
            chats,
            tokenize=True,
            add_generation_prompt=True,
            padding=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda:0")
        with torch.inference_mode():
            generated = model.generate(
                **batch,
                do_sample=False,
                max_new_tokens=generation["max_new_tokens"],
                pad_token_id=tokenizer.pad_token_id,
                use_cache=True,
            )
        for tokens in generated[:, batch["input_ids"].shape[1] :]:
            # Decode the actual content while stripping only terminal EOS/padding.
            ids = tokens.tolist()
            eos = model.generation_config.eos_token_id
            eos = {eos} if isinstance(eos, int) else set(eos or ())
            end = next((i for i, token in enumerate(ids) if token in eos), len(ids))
            yield tokenizer.decode(ids[:end], skip_special_tokens=False)
        print(f"generated={min(start + batch_size, len(inputs))}/{len(inputs)}", flush=True)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def score(tp, fp, fn):
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "support": tp + fn,
        "precision": ratio(tp, tp + fp) if tp + fp else (0.0 if fn else None),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def evaluate(records):
    tp, fp, fn = Counter(), Counter(), Counter()
    for row in records:
        expected, predicted = set(row["expected"].items()), set(row["predicted"].items())
        tp.update(expected & predicted)
        fp.update(predicted - expected)
        fn.update(expected - predicted)

    def aggregate(classes):
        return score(*(sum(counter[c] for c in classes) for counter in (tp, fp, fn)))

    by_pair = {f"{a}={p}": aggregate([(a, p)]) for a, p in CLASSES}
    supported = [item["f1"] for item in by_pair.values() if item["support"]]
    invalid = sum(row["error"] is not None for row in records)
    return {
        "n": len(records),
        "valid": len(records) - invalid,
        "invalid": invalid,
        "macro_f1": ratio(sum(supported), len(supported)),
        "macro_class_count": len(supported),
        "by_pair": by_pair,
        "by_aspect": {a: aggregate([(a, p) for p in ("pos", "neg")]) for a in ASPECTS},
        "by_polarity": {p: aggregate([(a, p) for a in ASPECTS]) for p in ("pos", "neg")},
    }


def review_f1(row):
    if row["error"] is not None:
        return 0.0
    expected, predicted = set(row["expected"].items()), set(row["predicted"].items())
    return (
        ratio(2 * len(expected & predicted), len(expected) + len(predicted))
        if (expected or predicted)
        else 1.0
    )


def compare(a, b):
    assert [row["id"] for row in a] == [row["id"] for row in b]
    count = {"wins": 0, "ties": 0, "losses": 0}
    for left, right in zip(a, b, strict=True):
        delta = review_f1(left) - review_f1(right)
        count["wins" if delta > 0 else "losses" if delta < 0 else "ties"] += 1
    return count


def demonstrations(train):
    available = train.copy()
    covered = set()
    messages = []
    for _ in range(4):
        row = min(
            available,
            key=lambda r: (
                -len(set(r["expected"].items()) - covered),
                -len(r["expected"]),
                r["id"],
            ),
        )
        available.remove(row)
        covered.update(row["expected"].items())
        messages.extend(
            [
                {"role": "user", "content": row["prompt"]},
                {"role": "assistant", "content": compact(row["expected"])},
            ]
        )
    return messages


def keywords(text):
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )
    result = {}
    for aspect, (pos, neg) in RULES.items():
        if re.search(neg, normalized):
            result[aspect] = "neg"
        elif re.search(pos, normalized):
            result[aspect] = "pos"
    return result


def tfidf_predictions(train, inputs):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)
    features = vectorizer.fit_transform([row["text"] for row in train])
    test_features = vectorizer.transform([row["text"] for row in inputs])
    labels = []
    for aspect in ASPECTS:
        classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=2718)
        classifier.fit(features, [row["expected"].get(aspect, "ausente") for row in train])
        labels.append(classifier.predict(test_features))
    return (
        compact({a: p for a, p in zip(ASPECTS, labels_per_row, strict=True) if p != "ausente"})
        for labels_per_row in zip(*labels, strict=True)
    )


def load_final(commit, manifest, instruction):
    def load(path, hash_value):
        return download(path, commit, hash_value)

    splits = json.loads(load("data/absa/splits-v1.json", manifest["splits_manifest_sha256_lf"]))
    reference = manifest["gold_reference"]
    human = json.loads(
        load("data/gold/human_review_manifest.json", reference["review_manifest_sha256_lf"])
    )
    labels = rows(load("data/gold/aspects_100.human.jsonl", reference["annotations_sha256"]))
    gold_text = rows(load("data/gold/reviews_100.blind.jsonl", human["blind_sample_sha256"]))
    texts = {r["id"]: r["text"] for r in gold_text}
    assert len(texts) == len(labels) == 100 and set(texts) == {r["id"] for r in labels}
    pool_path = "data/splits/train_pool.jsonl"
    pool = {r["id"]: r for r in rows(load(pool_path, splits["input_sha256_lf"][pool_path]))}
    reserved_ids = splits["ids"]["template_test"]
    assert len(set(reserved_ids)) == 346 and set(reserved_ids).isdisjoint(texts)

    def item(row, text):
        return {
            "id": row["id"],
            "text": text,
            "prompt": instruction + text,
            "expected": row["aspects"],
        }

    gold = [item(r, texts[r["id"]]) for r in labels]
    reserved = [item(pool[i], pool[i]["text"]) for i in reserved_ids]
    strata = splits["template_test_strata_ids"]
    return gold + reserved, {
        "gold": set(texts),
        "gold_without_ambiguity": set(texts) - set(human["ambiguous_ids"]),
        "reserved": set(reserved_ids),
        "reserved_unseen_only": set(strata["unseen_only"]),
        "reserved_mixed": set(strata["mixed"]),
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.manifest.read_text(encoding="utf-8"))
    commit = cfg["dataset_commit"]
    out = args.output
    out.mkdir()
    write_json(out / "protocol.json", cfg)
    files = cfg["adapter_files_sha256"]
    adapter = out.parent / f"{out.name}-adapter"
    adapter.mkdir()
    if args.adapter.is_dir():
        members = {name: (args.adapter / name).read_bytes() for name in files}
    else:
        with ZipFile(args.adapter) as z:
            members = {name: z.read(name) for name in files}
    for name, data in members.items():
        if digest(data) != files[name]:
            raise ValueError(f"Adapter hash mismatch: {name}")
        (adapter / name).write_bytes(data)

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    assert torch.cuda.device_count() == 1 and torch.cuda.get_device_name(0) == "Tesla T4"
    manifest = json.loads(
        download("data/absa/dataset-v1.json", commit, cfg["dataset_manifest_sha256_lf"])
    )
    assert manifest["revision"] == cfg["model_revision"]
    tokenizer = AutoTokenizer.from_pretrained(adapter, local_files_only=True)
    assert digest(tokenizer.chat_template.encode()) == manifest["chat_template_sha256"]
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        manifest["model"],
        revision=manifest["revision"],
        token=False,
        dtype=torch.float16,
        device_map={"": 0},
        attn_implementation="sdpa",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        ),
    )
    model = PeftModel.from_pretrained(base, adapter).eval()
    validation = chat_rows(
        download(
            "data/absa/validation-v1.jsonl", commit, manifest["splits"]["validation"]["sha256_lf"]
        )
    )
    assert len(validation) == cfg["gate"]["validation_size"]
    records = journal(
        out / "validation.jsonl",
        validation,
        generate(model, tokenizer, validation, cfg["generation"]),
    )
    report = evaluate(records)
    report["gate_passed"] = report["invalid"] <= cfg["gate"]["maximum_invalid"]
    write_json(out / "validation.json", report)
    write_json(
        out / "environment.json",
        {
            "gpu": torch.cuda.get_device_name(0),
            "cuda": torch.version.cuda,
            "packages": {
                p: version(p)
                for p in ("torch", "transformers", "bitsandbytes", "peft", "scikit-learn")
            },
            "worker_sha256": digest(Path(__file__).read_bytes()),
        },
    )
    print(
        f"VALIDATION valid={report['valid']} invalid={report['invalid']} "
        f"gate_passed={report['gate_passed']}",
        flush=True,
    )
    if not report["gate_passed"]:
        return

    train = chat_rows(
        download("data/absa/train-v1.jsonl", commit, manifest["splits"]["train"]["sha256_lf"])
    )
    examples = demonstrations(train)
    write_json(out / "few-shot.json", examples)
    instruction = validation[0]["prompt"].split("\n\nReview:\n", 1)[0] + "\n\nReview:\n"
    inputs, subsets = load_final(commit, manifest, instruction)
    assert len(inputs) == 446 and len(subsets["reserved_unseen_only"]) == 36
    assert {r["id"] for r in train + validation}.isdisjoint(r["id"] for r in inputs)
    runs = {}
    runs["qlora"] = journal(
        out / "qlora.jsonl", inputs, generate(model, tokenizer, inputs, cfg["generation"])
    )
    with model.disable_adapter():
        runs["fewshot"] = journal(
            out / "fewshot.jsonl",
            inputs,
            generate(model, tokenizer, inputs, cfg["generation"], examples),
        )
    runs["keywords"] = journal(
        out / "keywords.jsonl", inputs, (compact(keywords(r["text"])) for r in inputs)
    )
    runs["tfidf"] = journal(out / "tfidf.jsonl", inputs, tfidf_predictions(train, inputs))
    final = {}
    for split, ids in subsets.items():
        selected = {
            name: [r for r in predictions if r["id"] in ids] for name, predictions in runs.items()
        }
        final[split] = {
            "metrics": {name: evaluate(reviews) for name, reviews in selected.items()},
            "qlora_comparison": {
                name: compare(selected["qlora"], reviews)
                for name, reviews in selected.items()
                if name != "qlora"
            },
        }
    write_json(out / "final.json", final)
    print("FINAL_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
