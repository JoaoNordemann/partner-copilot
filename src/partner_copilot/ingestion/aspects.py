"""Aspect extraction backends and the shared opt-in retrieval predicate."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from partner_copilot.config import Settings
    from partner_copilot.schemas import Review

ASPECTS = frozenset({"sabor", "tempo_entrega", "temperatura", "embalagem", "preco", "atendimento"})
ADAPTER = "jnordemann/partnercopilot-absa-qlora-v1"
ADAPTER_REVISION = "742d1dcb93d71aee84fda6a84f5ca23dd8c281d6"
ADAPTER_HASH = "ef97282c03432c22c9735f419463d1e936b0729ac099052ac96e7b170c7e1d05"
BASE_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
INSTRUCTION = (
    "Classifique os aspectos sabor, tempo_entrega, temperatura, embalagem, preco e atendimento. "
    "Use pos ou neg e omita aspectos sem opinião clara. Responda só com um objeto JSON "
    'com a chave "aspects".\n\nReview:\n'
)
Polarity = Literal["pos", "neg"]


def unique_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


@dataclass(frozen=True)
class AspectExtraction:
    aspects: dict[str, Polarity] = field(default_factory=dict)
    status: Literal["ok", "inválido"] = "ok"

    def __post_init__(self):
        if (
            self.status not in ("ok", "inválido")
            or (self.status == "inválido" and self.aspects)
            or any(
                key not in ASPECTS or value not in ("pos", "neg")
                for key, value in self.aspects.items()
            )
        ):
            raise ValueError("invalid aspect extraction")

    @classmethod
    def from_json(cls, raw: str) -> AspectExtraction:
        try:
            parsed = json.loads(raw, object_pairs_hook=unique_keys)
            if not isinstance(parsed, dict) or parsed.keys() != {"aspects"}:
                raise ValueError("expected an aspects object")
            if not isinstance(parsed["aspects"], dict):
                raise ValueError("expected an aspect map")
            return cls(parsed["aspects"])
        except ValueError:
            return cls(status="inválido")


class AspectExtractor(Protocol):
    version: str

    def extract(self, review: Review) -> AspectExtraction: ...


class FakeAspectExtractor:
    version = "fake-v1"

    def __init__(self, outputs: Mapping[str, str] | None = None):
        self.outputs = dict(outputs or {})

    def extract(self, review: Review) -> AspectExtraction:
        return AspectExtraction.from_json(self.outputs.get(review.id, '{"aspects":{}}'))


class PrecomputedAspectExtractor:
    def __init__(self, path: Path, corpus_path: Path):
        manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        self.version = manifest["extractor_version"]
        self.adapter_sha256 = manifest["adapter_weights_sha256"]
        predictions = path.read_text(encoding="utf-8")
        corpus = corpus_path.read_text(encoding="utf-8")
        for content, key in (
            (predictions, "predictions_sha256_lf"),
            (corpus, "corpus_sha256_lf"),
        ):
            if hashlib.sha256(content.encode()).hexdigest() != manifest[key]:
                raise ValueError(f"Precomputed aspect checksum mismatch: {key}")
        self._texts = {row["id"]: row["text"] for row in map(json.loads, corpus.splitlines())}
        self._predictions = {}
        for row in map(json.loads, predictions.splitlines()):
            review_id = row["review_id"]
            if (
                review_id in self._predictions
                or row["absa_extractor_version"] != self.version
                or row["adapter_sha256"] != self.adapter_sha256
            ):
                raise ValueError("Inconsistent precomputed aspect metadata")
            self._predictions[review_id] = AspectExtraction(row["aspects"], row["status"])
        if self._predictions.keys() != self._texts.keys():
            raise ValueError("Precomputed aspects must cover the source corpus")

    def extract(self, review: Review) -> AspectExtraction:
        if review.id not in self._predictions or self._texts[review.id] != review.text:
            return AspectExtraction(status="inválido")
        return self._predictions[review.id]


class QLoRAAspectExtractor:
    version = "partnercopilot-absa-qlora-v1/checkpoint-253"
    adapter_sha256 = ADAPTER_HASH

    def __init__(self):
        self._runtime = None

    def _load(self):
        import torch
        from huggingface_hub import snapshot_download
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        if not torch.cuda.is_available():
            raise RuntimeError("QLoRA aspect extraction requires a CUDA GPU")
        path = Path(snapshot_download(ADAPTER, revision=ADAPTER_REVISION, token=False))
        if (
            hashlib.sha256((path / "adapter_model.safetensors").read_bytes()).hexdigest()
            != ADAPTER_HASH
        ):
            raise ValueError("QLoRA adapter checksum mismatch")
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        base = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-1.5B-Instruct",
            revision=BASE_REVISION,
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
        return torch, tokenizer, PeftModel.from_pretrained(base, path).eval()

    def extract(self, review: Review) -> AspectExtraction:
        if self._runtime is None:
            self._runtime = self._load()
        torch, tokenizer, model = self._runtime
        inputs = tokenizer.apply_chat_template(
            [{"role": "user", "content": INSTRUCTION + review.text}],
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda:0")
        with torch.inference_mode():
            result = model.generate(**inputs, do_sample=False, max_new_tokens=96, use_cache=True)
        ids = result[0, inputs["input_ids"].shape[1] :].tolist()
        eos = model.generation_config.eos_token_id
        eos = {eos} if isinstance(eos, int) else set(eos or ())
        end = next((i for i, token in enumerate(ids) if token in eos), len(ids))
        return AspectExtraction.from_json(tokenizer.decode(ids[:end], skip_special_tokens=False))


def build_aspect_extractor(settings: Settings) -> AspectExtractor | None:
    if not settings.aspect_enrichment_enabled:
        return None
    if settings.aspect_extractor == "fake":
        return FakeAspectExtractor()
    if settings.aspect_extractor == "precomputed":
        if settings.aspect_predictions_path is None:
            raise ValueError("ASPECT_PREDICTIONS_PATH is required for precomputed extraction")
        return PrecomputedAspectExtractor(
            settings.aspect_predictions_path, settings.data_eval_dir / "corpus.jsonl"
        )
    return QLoRAAspectExtractor()


def aspect_filter(aspect: str, enabled: bool) -> dict | None:
    if not enabled:
        return {f"aspect_{aspect}": "neg"}
    if aspect in ASPECTS:
        return {f"aspect_exclude_{aspect}": {"$ne": True}}
    return None
