import re
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from partner_copilot.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_derived_paths_follow_configured_roots(monkeypatch):
    monkeypatch.setenv("DATA_RAW_DIR", "custom/raw")
    monkeypatch.setenv("DATA_GOLD_DIR", "custom/gold")
    monkeypatch.setenv("DATA_EXTERNAL_DIR", "custom/external")
    settings = Settings()
    assert settings.raw_reviews_path == Path("custom/raw/reviews.jsonl")
    assert settings.gold_exposure_path == Path("custom/gold/prior_exposure.json")
    assert settings.external_reviews_dir == Path("custom/external/b2w_reviews01")
    assert Settings(data_raw_dir=Path("override")).raw_reviews_path == Path(
        "override/reviews.jsonl"
    )


def test_example_documents_all_settings_and_is_valid():
    example = ROOT / ".env.example"
    keys = re.findall(r"^\s*(?:#\s*)?([A-Z_]+)=", example.read_text(encoding="utf-8-sig"), re.M)
    assert set(keys) == {name.upper() for name in Settings.model_fields}
    settings = Settings(_env_file=example)
    assert settings.hf_token is None
    assert settings.data_eval_dir == Path("data/eval/human-v2")


def test_blank_llm_model_is_rejected():
    with pytest.raises(ValidationError):
        Settings(llm_model_id=" ")


def test_generator_uses_env_root_and_cli_override(tmp_path, monkeypatch):
    import sys

    configured = tmp_path / "configured"
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("DATA_RAW_DIR", str(configured))
    command = [
        sys.executable,
        str(ROOT / "scripts/generate_synthetic_data.py"),
        "--n",
        "3",
        "--seed",
        "42",
        "--end-date",
        "2026-11-01",
        "--validate",
    ]
    subprocess.run(command, check=True, capture_output=True)
    assert len((configured / "reviews.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    subprocess.run([*command, "--out-dir", str(explicit)], check=True, capture_output=True)
    assert (explicit / "reviews.jsonl").read_bytes() == (configured / "reviews.jsonl").read_bytes()


@pytest.mark.parametrize("temperature", [0.0, 0.7])
def test_mistral_consumes_settings_without_loading_models(monkeypatch, temperature):
    from contextlib import nullcontext
    from unittest.mock import MagicMock

    from partner_copilot.generation import llm

    tokenizer_loader = MagicMock()
    model_loader = MagicMock()
    monkeypatch.setattr(llm.AutoTokenizer, "from_pretrained", tokenizer_loader)
    monkeypatch.setattr(llm.AutoModelForCausalLM, "from_pretrained", model_loader)
    monkeypatch.setattr(llm, "BitsAndBytesConfig", MagicMock())
    monkeypatch.setattr(llm.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(llm.torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(llm.torch.cuda, "device", lambda _: nullcontext())
    monkeypatch.setattr(llm.torch.cuda, "is_bf16_supported", lambda: False)
    settings = Settings(
        llm_model_id="custom/model",
        hf_token="test-token",
        temperature=temperature,
        top_p=0.8,
        max_new_tokens=64,
        generation_context_margin_tokens=8,
    )
    model_loader.return_value.config.max_position_embeddings = 128
    engine = llm.Mistral4bit(settings=settings)
    tokenizer_loader.assert_called_once_with("custom/model", token="test-token")
    assert model_loader.call_args.args == ("custom/model",)
    inputs = MagicMock()
    inputs.to.return_value = {"input_ids": llm.torch.tensor([[1, 2]])}
    tokenizer_loader.return_value.return_value = inputs
    model_loader.return_value.generate.return_value = llm.torch.tensor([[1, 2, 3]])
    engine.generate("Pergunta")
    tokenizer_loader.return_value.apply_chat_template.assert_called_once_with(
        [{"role": "user", "content": "Pergunta"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    kwargs = model_loader.return_value.generate.call_args.kwargs
    assert kwargs["max_new_tokens"] == 64
    assert kwargs["do_sample"] == (temperature > 0)
    if temperature:
        assert kwargs["temperature"] == temperature
        assert kwargs["top_p"] == 0.8
    else:
        assert "temperature" not in kwargs
        assert "top_p" not in kwargs
    engine.generate("Pergunta", max_new_tokens=32)
    assert model_loader.return_value.generate.call_args.kwargs["max_new_tokens"] == 32

    from partner_copilot.generation.contracts import GenerationContractError

    model_loader.return_value.generate.reset_mock()
    model_loader.return_value.config.max_position_embeddings = 33
    with pytest.raises(GenerationContractError, match="context"):
        engine.generate("Pergunta", max_new_tokens=32)
    model_loader.return_value.generate.assert_not_called()
