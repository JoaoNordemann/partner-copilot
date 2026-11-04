"""Reusable NF4 Mistral inference with per-call RNG isolation and CUDA measurements."""

import logging
from threading import Lock
from time import perf_counter

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from partner_copilot.config import Settings, get_settings
from partner_copilot.generation.contracts import LLM as LLM
from partner_copilot.generation.contracts import (
    GenerationContractError,
    GenerationMetrics,
    GenerationResult,
    MeasuredLLM,
)

logger = logging.getLogger(__name__)
# RNG seeding and CUDA peak statistics are shared process state. Serialize all instances.
_INFERENCE_LOCK = Lock()


def _cuda_devices(model) -> list[int]:
    mapping = getattr(model, "hf_device_map", None)
    placements = list(mapping.values()) if isinstance(mapping, dict) else [model.device]
    devices = set()
    for value in placements:
        if isinstance(value, int) and value >= 0:
            devices.add(value)
        elif isinstance(value, (str, torch.device)) and str(value).startswith("cuda"):
            device = torch.device(value)
            devices.add(device.index if device.index is not None else torch.cuda.current_device())
    return sorted(devices)


def _synchronize(devices: list[int]) -> None:
    for device in devices:
        torch.cuda.synchronize(device)


class Mistral4bit(MeasuredLLM):
    def __init__(self, model_id: str | None = None, *, settings: Settings | None = None) -> None:
        config = settings if settings is not None else get_settings()
        self.settings = config.model_copy(deep=True)
        self.model_id = model_id if model_id is not None else self.settings.llm_model_id
        if not torch.cuda.is_available():
            raise RuntimeError("Mistral4bit requires a CUDA GPU; use a fake LLM for CPU tests")
        token = self.settings.hf_token.get_secret_value() if self.settings.hf_token else None
        with _INFERENCE_LOCK:
            started = perf_counter()
            supports_bf16 = True
            # Conservative for automatic sharding: every visible GPU must support bf16.
            for device in range(torch.cuda.device_count()):
                with torch.cuda.device(device):
                    try:
                        supported = torch.cuda.is_bf16_supported(including_emulation=False)
                    except TypeError:  # Compatibility with older supported Torch signatures.
                        supported = torch.cuda.is_bf16_supported()
                    supports_bf16 = supported and supports_bf16
            self.compute_dtype = torch.bfloat16 if supports_bf16 else torch.float16
            cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=self.compute_dtype,
            )
            self.tok = AutoTokenizer.from_pretrained(self.model_id, token=token)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                quantization_config=cfg,
                device_map="auto",
                token=token,
            )
            self.model.eval()
            self.cuda_devices = _cuda_devices(self.model)
            _synchronize(self.cuda_devices)
            self.model_load_latency_ms = (perf_counter() - started) * 1000
            logger.info(
                "llm_model_loaded model=%s dtype=%s load_ms=%.3f",
                self.model_id,
                self.compute_dtype,
                self.model_load_latency_ms,
            )

    @torch.inference_mode()
    def generate_with_metrics(
        self,
        user_prompt: str,
        max_new_tokens: int | None = None,
    ) -> GenerationResult:
        with _INFERENCE_LOCK:
            _synchronize(self.cuda_devices)
            baseline = {f"cuda:{i}": torch.cuda.memory_allocated(i) for i in self.cuda_devices}
            for device in self.cuda_devices:
                torch.cuda.reset_peak_memory_stats(device)
            started = perf_counter()
            text = self.tok.apply_chat_template(
                [{"role": "user", "content": user_prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = self.tok(
                text, return_tensors="pt", add_special_tokens=False, truncation=False
            ).to(self.model.device)
            budget = max_new_tokens if max_new_tokens is not None else self.settings.max_new_tokens
            context_limit = getattr(self.model.config, "max_position_embeddings", None)
            if not isinstance(context_limit, int) or context_limit < 1:
                raise GenerationContractError("Cannot determine model context window")
            tokenizer_limit = getattr(self.tok, "model_max_length", None)
            if isinstance(tokenizer_limit, int) and tokenizer_limit > 0:
                context_limit = min(context_limit, tokenizer_limit)
            prompt_tokens = inputs["input_ids"].shape[-1]
            margin = self.settings.generation_context_margin_tokens
            if budget < 1 or prompt_tokens + budget + margin > context_limit:
                raise GenerationContractError(
                    "Prompt plus generation budget and safety margin exceeds model context"
                )
            sampling = self.settings.temperature > 0
            sampling_options = (
                {"temperature": self.settings.temperature, "top_p": self.settings.top_p}
                if sampling
                else {}
            )
            # Restore the caller's CPU and used-GPU RNG state after the request.
            with torch.random.fork_rng(devices=self.cuda_devices):
                torch.random.default_generator.manual_seed(self.settings.generation_seed)
                for device in self.cuda_devices:
                    with torch.cuda.device(device):
                        torch.cuda.manual_seed(self.settings.generation_seed)
                out = self.model.generate(
                    **inputs,
                    max_new_tokens=budget,
                    do_sample=sampling,
                    **sampling_options,
                    pad_token_id=self.tok.eos_token_id,
                    return_dict_in_generate=False,
                )
            new_tokens = out[0][prompt_tokens:]
            answer = self.tok.decode(new_tokens, skip_special_tokens=True)
            _synchronize(self.cuda_devices)
            latency_ms = (perf_counter() - started) * 1000
            metrics = GenerationMetrics(
                latency_ms=latency_ms,
                model_load_latency_ms=self.model_load_latency_ms,
                prompt_tokens=prompt_tokens,
                generated_tokens=len(new_tokens),
                max_new_tokens=budget,
                context_window_tokens=context_limit,
                context_margin_tokens=margin,
                seed=self.settings.generation_seed,
                temperature=self.settings.temperature,
                do_sample=sampling,
                compute_dtype=str(self.compute_dtype).removeprefix("torch."),
                vram_baseline_allocated_bytes=baseline or None,
                vram_peak_allocated_bytes={
                    f"cuda:{i}": torch.cuda.max_memory_allocated(i) for i in self.cuda_devices
                }
                or None,
                vram_peak_reserved_bytes={
                    f"cuda:{i}": torch.cuda.max_memory_reserved(i) for i in self.cuda_devices
                }
                or None,
            )
            logger.info("llm_generation_completed %s", metrics.model_dump())
            return GenerationResult(answer, metrics)
