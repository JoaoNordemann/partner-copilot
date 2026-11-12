"""Run each precision in a fresh Kaggle worker and journal each observation."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path("reports/final-v3")
MODEL = "mistralai/Mistral-7B-Instruct-v0.2"


def append(path, **row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def cases():
    hashes = dict(line.split()[::-1] for line in (ROOT / "SHA256SUMS").read_text().splitlines())
    result = {}
    for group, file in (
        ("limpo_original", "generation-v3-new.jsonl"),
        ("contaminado", "generation-v3-contaminated.jsonl"),
    ):
        data = (ROOT / file).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != hashes[file]:
            raise ValueError(f"Hash mismatch: {file}")
        result[group] = [r for line in data.splitlines() if (r := json.loads(line))["llm_called"]]
    if [len(v) for v in result.values()] != [9, 27]:
        raise ValueError("Unexpected cohort sizes")
    return result


def gpu_worker(mode, snapshot, path):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    from partner_copilot.generation.contracts import GenerationContractError
    from partner_copilot.generation.output import parse_generation
    from partner_copilot.generation.output_v3 import decode_output
    from partner_copilot.schemas import RetrievedDoc, Review

    if torch.cuda.device_count() != 1 or torch.cuda.get_device_name(0) != "Tesla T4":
        raise RuntimeError("Exactly one visible Tesla T4 is required")

    def memory():
        free, total = torch.cuda.mem_get_info(0)
        return {
            "free_bytes": free,
            "total_bytes": total,
            "allocated_bytes": torch.cuda.memory_allocated(0),
            "reserved_bytes": torch.cuda.memory_reserved(0),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(0),
        }

    append(
        path,
        event="environment",
        mode=mode,
        gpu=torch.cuda.get_device_name(0),
        cuda=torch.version.cuda,
        revision=snapshot.name,
        python=sys.version.split()[0],
        memory=memory(),
        commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        driver=subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True,
        ).splitlines()[0],
        packages={
            name: version(name)
            for name in ("torch", "transformers", "accelerate", "bitsandbytes", "chromadb")
        },
    )
    groups = cases()
    stage, identifier = "load", None
    try:
        torch.cuda.reset_peak_memory_stats(0)
        started = perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        kwargs = {}
        if mode == "nf4":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
        model = AutoModelForCausalLM.from_pretrained(
            snapshot,
            local_files_only=True,
            dtype=torch.float16,
            device_map={"": 0},
            attn_implementation="sdpa",
            **kwargs,
        ).eval()
        torch.cuda.synchronize(0)
        append(path, event="load", seconds=perf_counter() - started, memory=memory())
        for group, rows in (("warmup", groups["contaminado"][:2]), *groups.items()):
            stage = group
            torch.cuda.reset_peak_memory_stats(0)
            for row in rows:
                identifier = row["question_id"]
                torch.cuda.synchronize(0)
                started = perf_counter()
                chat = tokenizer.apply_chat_template(
                    [{"role": "user", "content": row["rendered_prompt"]}],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                inputs = tokenizer(chat, return_tensors="pt", add_special_tokens=False).to("cuda:0")
                prompt_tokens = inputs["input_ids"].shape[-1]
                if prompt_tokens + 512 + 256 > min(
                    model.config.max_position_embeddings, tokenizer.model_max_length
                ):
                    raise ValueError("Prompt exceeds frozen context budget")
                torch.manual_seed(42)
                torch.cuda.synchronize(0)
                generation_start = perf_counter()
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=512,
                        do_sample=False,
                        pad_token_id=tokenizer.eos_token_id,
                        use_cache=True,
                    )[0, prompt_tokens:]
                torch.cuda.synchronize(0)
                generation_seconds = perf_counter() - generation_start
                raw = tokenizer.decode(output, skip_special_tokens=True)
                latency = perf_counter() - started
                docs = [
                    RetrievedDoc(
                        review=Review.model_construct(id=d["review_id"], text=d["text"]),
                        score=d["score"],
                    )
                    for d in row["context"]
                ]
                parsed, error = None, None
                try:
                    parse_generation(raw, docs, parser_version="parser-v3")
                    parsed = decode_output(raw).value.model_dump(mode="json")
                except GenerationContractError as exc:
                    error = type(exc).__name__
                append(
                    path,
                    event="generation",
                    group=group,
                    id=identifier,
                    raw=raw,
                    accepted=error is None,
                    structured=parsed,
                    parser_error=error,
                    seconds=latency,
                    generated_tokens=len(output),
                    generation_seconds=generation_seconds,
                    prompt_tokens=prompt_tokens,
                    memory=memory(),
                )
    except torch.OutOfMemoryError as exc:
        append(path, event="oom", stage=stage, id=identifier, error=str(exc), memory=memory())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("nf4", "fp16"))
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    args.output.touch(exist_ok=False)
    gpu_worker(args.mode, args.snapshot, args.output)


if __name__ == "__main__":
    main()
