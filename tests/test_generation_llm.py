"""Adapter tests use real CPU tensors and fake models/CUDA counters, never model weights."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from partner_copilot.config import Settings
from partner_copilot.generation import llm
from partner_copilot.generation.contracts import GenerationContractError


class Batch(dict):
    def to(self, device):
        return self


class Tokenizer:
    model_max_length = 64
    eos_token_id = 0

    def apply_chat_template(self, messages, **kwargs):
        assert messages == [{"role": "user", "content": "Pergunta"}]
        assert kwargs == {"tokenize": False, "add_generation_prompt": True}
        return "Template com instruções e dados"

    def __call__(self, text, **kwargs):
        assert kwargs == {"return_tensors": "pt", "add_special_tokens": False, "truncation": False}
        return Batch(input_ids=torch.tensor([[1, 2, 3]]))

    def decode(self, tokens, *, skip_special_tokens):
        assert skip_special_tokens
        return ",".join(str(i) for i in tokens.tolist())


class Model:
    device = torch.device("cpu")
    config = SimpleNamespace(max_position_embeddings=64)

    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        suffix = torch.randint(20, 100, (1, 2))
        return torch.cat([kwargs["input_ids"], suffix], dim=1)


def engine(**settings):
    # CPU-only unit double: bypass the real CUDA model loader.
    result = object.__new__(llm.Mistral4bit)
    result.settings = Settings(max_new_tokens=16, generation_context_margin_tokens=8, **settings)
    result.tok = Tokenizer()
    result.model = Model()
    result.cuda_devices = []
    result.compute_dtype = torch.float16
    result.model_load_latency_ms = 12.0
    return result


def test_seed_is_reset_per_call_and_caller_rng_is_restored():
    model = engine(temperature=0.1, generation_seed=77)
    before = torch.random.get_rng_state().clone()
    first = model.generate_with_metrics("Pergunta")
    second = model.generate_with_metrics("Pergunta")
    assert first.text == second.text
    assert torch.equal(before, torch.random.get_rng_state())
    assert first.metrics.seed == 77 and first.metrics.do_sample
    assert first.metrics.prompt_tokens == 3 and first.metrics.generated_tokens == 2
    assert first.metrics.context_margin_tokens == 8 and first.metrics.context_window_tokens == 64
    assert first.metrics.vram_peak_allocated_bytes is None
    assert first.metrics.latency_ms >= 0 and first.metrics.model_load_latency_ms == 12
    assert model.model.calls[0]["temperature"] == 0.1
    assert len(first.text.split(",")) == 2  # The three input IDs were not decoded.
    assert isinstance(model.generate("Pergunta"), str)


def test_temperature_zero_disables_sampling_and_context_margin_is_enforced():
    model = engine()
    model.generate("Pergunta")
    assert not model.model.calls[0]["do_sample"]
    assert "temperature" not in model.model.calls[0] and "top_p" not in model.model.calls[0]
    model.model.config = SimpleNamespace(max_position_embeddings=26)
    with pytest.raises(GenerationContractError, match="margin"):
        model.generate("Pergunta")  # 3 + 16 + 8 = 27.
    assert len(model.model.calls) == 1
    model.model.config = SimpleNamespace(max_position_embeddings=27)
    model.generate("Pergunta")  # Exact budget boundary fits.
    assert len(model.model.calls) == 2


def test_cuda_peak_measurement_is_per_device_and_synchronized(monkeypatch):
    model = engine()
    model.cuda_devices = [0, 1]
    fork_rng = torch.random.fork_rng
    monkeypatch.setattr(torch.random, "fork_rng", lambda devices: fork_rng(devices=[]))
    monkeypatch.setattr(torch.cuda, "device", lambda _: nullcontext())
    monkeypatch.setattr(torch.cuda, "manual_seed", Mock())
    sync, reset = Mock(), Mock()
    monkeypatch.setattr(torch.cuda, "synchronize", sync)
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", reset)
    monkeypatch.setattr(torch.cuda, "memory_allocated", lambda device: 100 + device)
    monkeypatch.setattr(torch.cuda, "max_memory_allocated", lambda device: 200 + device)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", lambda device: 300 + device)
    result = model.generate_with_metrics("Pergunta")
    assert result.metrics.vram_baseline_allocated_bytes == {"cuda:0": 100, "cuda:1": 101}
    assert result.metrics.vram_peak_allocated_bytes == {"cuda:0": 200, "cuda:1": 201}
    assert result.metrics.vram_peak_reserved_bytes == {"cuda:0": 300, "cuda:1": 301}
    assert sync.call_count == 4 and reset.call_count == 2


@pytest.mark.parametrize(
    "support,expected", [([True, True], torch.bfloat16), ([True, False], torch.float16)]
)
def test_compute_dtype_and_model_eval_are_chosen_once(monkeypatch, support, expected):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 2)
    monkeypatch.setattr(torch.cuda, "device", lambda _: nullcontext())
    monkeypatch.setattr(torch.cuda, "is_bf16_supported", Mock(side_effect=support))
    quantization = Mock()
    monkeypatch.setattr(llm, "BitsAndBytesConfig", quantization)
    tokenizer_loader, model_loader = Mock(), Mock()
    model_loader.return_value.device = torch.device("cpu")
    model_loader.return_value.hf_device_map = {"": "cpu"}
    monkeypatch.setattr(llm.AutoTokenizer, "from_pretrained", tokenizer_loader)
    monkeypatch.setattr(llm.AutoModelForCausalLM, "from_pretrained", model_loader)
    result = llm.Mistral4bit(settings=Settings())
    assert result.compute_dtype == expected
    assert quantization.call_args.kwargs["bnb_4bit_compute_dtype"] == expected
    assert quantization.call_args.kwargs["bnb_4bit_quant_type"] == "nf4"
    model_loader.return_value.eval.assert_called_once()
    model_loader.assert_called_once()


def test_missing_gpu_fails_before_loading_any_weights(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    loader = Mock()
    monkeypatch.setattr(llm.AutoModelForCausalLM, "from_pretrained", loader)
    with pytest.raises(RuntimeError, match="CUDA GPU"):
        llm.Mistral4bit()
    loader.assert_not_called()


def test_sharded_cuda_devices_are_resolved_without_counting_cpu_or_disk():
    model = SimpleNamespace(
        hf_device_map={"a": 2, "b": "cuda:1", "c": "cpu", "d": "disk"}, device="cpu"
    )
    assert llm._cuda_devices(model) == [1, 2]
