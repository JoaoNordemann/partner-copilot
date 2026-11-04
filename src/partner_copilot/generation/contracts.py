"""Lightweight generation protocol shared without importing a model framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt

DEFAULT_PROMPT_VERSION = "partner-copilot-v1"
ABSTENTION_MARKER = "[[SEM_EVIDENCIA]]"
ABSTENTION_MESSAGE = "Não há evidência suficiente nas avaliações fornecidas."


class GenerationContractError(ValueError):
    """Model output or input cannot satisfy the generation contract."""


class LLM(Protocol):
    def generate(self, user_prompt: str, max_new_tokens: int | None = None) -> str: ...


class GenerationMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    model_load_latency_ms: float = Field(ge=0, allow_inf_nan=False)
    prompt_tokens: int = Field(ge=1)
    generated_tokens: int = Field(ge=0)
    max_new_tokens: int = Field(ge=1)
    context_window_tokens: int = Field(ge=1)
    context_margin_tokens: int = Field(ge=0)
    seed: int = Field(ge=0)
    temperature: float = Field(ge=0, allow_inf_nan=False)
    do_sample: bool
    compute_dtype: Literal["bfloat16", "float16"]
    vram_baseline_allocated_bytes: dict[str, NonNegativeInt] | None
    vram_peak_allocated_bytes: dict[str, NonNegativeInt] | None
    vram_peak_reserved_bytes: dict[str, NonNegativeInt] | None


@dataclass(frozen=True)
class GenerationResult:
    text: str
    metrics: GenerationMetrics


class MeasuredLLM(ABC):
    """Explicit capability: no mutable last_metrics and no model-framework dependency."""

    def generate(self, user_prompt: str, max_new_tokens: int | None = None) -> str:
        return self.generate_with_metrics(user_prompt, max_new_tokens).text

    @abstractmethod
    def generate_with_metrics(
        self,
        user_prompt: str,
        max_new_tokens: int | None = None,
    ) -> GenerationResult: ...
