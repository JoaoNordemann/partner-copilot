"""Process-scoped lazy model loading; one immutable generation configuration per process."""

from threading import Lock

from partner_copilot.config import Settings, get_settings
from partner_copilot.generation.contracts import GenerationContractError, MeasuredLLM

_MODEL_LOCK = Lock()
_instance: MeasuredLLM | None = None
_configuration: tuple[object, ...] | None = None


def get_llm(settings: Settings | None = None) -> MeasuredLLM:
    global _instance, _configuration
    config = settings if settings is not None else get_settings()
    # SecretStr keeps the token masked even if this key is inspected in a debugger.
    key = (
        config.llm_model_id,
        config.hf_token,
        config.max_new_tokens,
        config.temperature,
        config.top_p,
        config.generation_seed,
        config.generation_context_margin_tokens,
    )
    with _MODEL_LOCK:
        if _instance is not None:
            if key != _configuration:
                raise GenerationContractError(
                    "A model is already loaded with different settings; restart the process"
                )
            return _instance
        from partner_copilot.generation.llm import Mistral4bit

        instance = Mistral4bit(settings=config)
        _instance, _configuration = instance, key
        return instance
