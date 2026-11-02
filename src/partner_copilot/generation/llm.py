from typing import Protocol

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from partner_copilot.config import Settings, get_settings


class LLM(Protocol):
    def generate(self, user_prompt: str, max_new_tokens: int | None = None) -> str: ...


class Mistral4bit:
    def __init__(self, model_id: str | None = None, *, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else get_settings()
        model_id = model_id if model_id is not None else self.settings.llm_model_id
        token = self.settings.hf_token.get_secret_value() if self.settings.hf_token else None
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        self.tok = AutoTokenizer.from_pretrained(model_id, token=token)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, quantization_config=cfg, device_map="auto", token=token
        )

    @torch.inference_mode()
    def generate(self, user_prompt: str, max_new_tokens: int | None = None) -> str:
        text = self.tok.apply_chat_template(
            [{"role": "user", "content": user_prompt}], tokenize=False, add_generation_prompt=True
        )
        inputs = self.tok(text, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        sampling = self.settings.temperature > 0
        sampling_options = (
            {"temperature": self.settings.temperature, "top_p": self.settings.top_p}
            if sampling
            else {}
        )
        out = self.model.generate(
            **inputs,
            max_new_tokens=(
                max_new_tokens if max_new_tokens is not None else self.settings.max_new_tokens
            ),
            do_sample=sampling,
            **sampling_options,
            pad_token_id=self.tok.eos_token_id,
        )
        return self.tok.decode(out[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
