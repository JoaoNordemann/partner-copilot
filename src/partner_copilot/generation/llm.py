# generation/llm.py
import os
from typing import Protocol

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class LLM(Protocol):
    def generate(self, user_prompt: str, max_new_tokens: int = 400) -> str: ...


class Mistral4bit:
    def __init__(self, model_id="mistralai/Mistral-7B-Instruct-v0.2"):
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        self.tok = AutoTokenizer.from_pretrained(model_id, token=os.getenv("HF_TOKEN"))
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, quantization_config=cfg, device_map="auto", token=os.getenv("HF_TOKEN")
        )

    @torch.inference_mode()
    def generate(self, user_prompt, max_new_tokens=400):
        text = self.tok.apply_chat_template(
            [{"role": "user", "content": user_prompt}], tokenize=False, add_generation_prompt=True
        )
        inputs = self.tok(text, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        out = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
            pad_token_id=self.tok.eos_token_id,
        )
        return self.tok.decode(out[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
