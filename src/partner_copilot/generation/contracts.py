"""Lightweight generation protocol shared without importing a model framework."""

from typing import Protocol

DEFAULT_PROMPT_VERSION = "partner-copilot-v1"
ABSTENTION_MARKER = "[[SEM_EVIDENCIA]]"
ABSTENTION_MESSAGE = "Não há evidência suficiente nas avaliações fornecidas."


class GenerationContractError(ValueError):
    """Model output or input cannot satisfy the generation contract."""


class LLM(Protocol):
    def generate(self, user_prompt: str, max_new_tokens: int | None = None) -> str: ...
