"""Configuração central do projeto, validada via pydantic-settings.

Precedência: argumentos explícitos > ambiente > arquivo `.env` > defaults.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from partner_copilot.generation.contracts import DEFAULT_PARSER_VERSION, DEFAULT_PROMPT_VERSION

MULTILINGUAL_MINILM_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
MISTRAL_INSTRUCT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"


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
    data_gold_dir: Path = Path("data/gold")
    data_eval_dir: Path = Path("data/eval/human-v2")
    data_external_dir: Path = Path("data/external")
    annotation_guide_path: Path = Path("docs/annotation-guide.md")
    chroma_path: Path = Path("data/chroma")
    chroma_collection: str = Field(
        default="reviews", description="Prefixo do nome automático da collection por modelo."
    )

    # --- Modelos ---------------------------------------------------------
    embedding_model: str = MULTILINGUAL_MINILM_MODEL
    embedding_batch_size: int = Field(default=32, ge=1, le=4096)
    embedding_device: str = "cpu"
    embedding_prefix_mode: Literal["auto", "none", "e5"] = "auto"
    llm_model_id: str = MISTRAL_INSTRUCT_MODEL

    ingestion_chunk_max_tokens: int | None = Field(default=None, ge=8)
    ingestion_chunk_overlap_tokens: int = Field(default=16, ge=0)
    ingestion_max_review_chars: int = Field(default=50000, ge=1)

    # --- Retrieval -------------------------------------------------------
    retrieval_k: int = Field(default=8, ge=1, le=50)
    retrieval_min_score: float = Field(default=0.25, ge=0.0, le=1.0)

    context_k: int = Field(default=5, ge=1, le=50)
    prompt_version: str = DEFAULT_PROMPT_VERSION
    parser_version: Literal["parser-v1", "parser-v2"] = DEFAULT_PARSER_VERSION

    # --- Geração ---------------------------------------------------------
    max_new_tokens: int = Field(default=400, ge=16, le=2048)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    generation_seed: int = Field(default=42, ge=0, le=4294967295)
    generation_context_margin_tokens: int = Field(default=256, ge=0)

    @field_validator("embedding_model", "embedding_device", "llm_model_id", "prompt_version")
    @classmethod
    def _non_blank_embedding_setting(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model names and embedding device must not be blank")
        return value.strip()

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

    @property
    def raw_reviews_path(self) -> Path:
        return self.data_raw_dir / "reviews.jsonl"

    @property
    def external_reviews_dir(self) -> Path:
        return self.data_external_dir / "b2w_reviews01"

    @property
    def gold_exposure_path(self) -> Path:
        return self.data_gold_dir / "prior_exposure.json"

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
