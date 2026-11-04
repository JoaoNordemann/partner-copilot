import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from partner_copilot.config import Settings, get_settings
from partner_copilot.generation.contracts import LLM as LLM
from partner_copilot.generation.contracts import GenerationContractError


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
        inputs = self.tok(text, return_tensors="pt", add_special_tokens=False, truncation=False).to(
            self.model.device
        )
        budget = max_new_tokens if max_new_tokens is not None else self.settings.max_new_tokens
        context_limit = getattr(self.model.config, "max_position_embeddings", None)
        if not isinstance(context_limit, int) or context_limit < 1:
            raise GenerationContractError("Cannot determine model context window")
        tokenizer_limit = getattr(self.tok, "model_max_length", None)
        if isinstance(tokenizer_limit, int) and tokenizer_limit > 0:
            context_limit = min(context_limit, tokenizer_limit)
        if budget < 1 or inputs["input_ids"].shape[-1] + budget > context_limit:
            raise GenerationContractError("Prompt plus generation budget exceeds model context")
        sampling = self.settings.temperature > 0
        sampling_options = (
            {"temperature": self.settings.temperature, "top_p": self.settings.top_p}
            if sampling
            else {}
        )
        out = self.model.generate(
            **inputs,
            max_new_tokens=budget,
            do_sample=sampling,
            **sampling_options,
            pad_token_id=self.tok.eos_token_id,
        )
        return self.tok.decode(out[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
