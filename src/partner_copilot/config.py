"""Configuração central do projeto, validada via pydantic-settings.

Valores vêm (em ordem de precedência) de: variáveis de ambiente > arquivo `.env` > defaults.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Segredos --------------------------------------------------------
    hf_token: SecretStr | None = Field(default=None, description="Token do Hugging Face Hub.")

    # --- Dados -----------------------------------------------------------
    data_raw_dir: Path = Path("data/raw")
    data_splits_dir: Path = Path("data/splits")
    chroma_path: Path = Path("data/chroma")
    chroma_collection: str = "reviews"

    # --- Modelos ---------------------------------------------------------
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    llm_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"

    # --- Retrieval -------------------------------------------------------
    retrieval_k: int = Field(default=8, ge=1, le=50)
    retrieval_min_score: float = Field(default=0.25, ge=0.0, le=1.0)

    # --- Geração ---------------------------------------------------------
    max_new_tokens: int = Field(default=400, ge=16, le=2048)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)

    @field_validator("hf_token", mode="before")
    @classmethod
    def _empty_token_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("chroma_collection")
    @classmethod
    def _valid_collection_name(cls, v: str) -> str:
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,61}[A-Za-z0-9]", v)
            or ".." in v
            or re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", v)
        ):
            raise ValueError("Invalid Chroma collection name (3-63 ASCII characters).")
        return v

    def require_hf_token(self) -> str:
        """Retorna o token ou falha com mensagem clara (modelos gated, push para o Hub)."""
        if self.hf_token is None:
            raise RuntimeError("HF_TOKEN não definido. Configure no ambiente ou no arquivo .env.")
        return self.hf_token.get_secret_value()

    def export_hf_env(self) -> None:
        """Exporta HF_TOKEN para os.environ, pois transformers/huggingface_hub o leem de lá.

        O pydantic-settings lê o `.env` sem poluir `os.environ`, então chame isto uma vez
        na inicialização (API, scripts) antes de carregar modelos.
        """
        if self.hf_token is not None:
            os.environ.setdefault("HF_TOKEN", self.hf_token.get_secret_value())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
