"""Public HTTP contracts; importing these never imports a model runtime."""

from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from partner_copilot.generation.output_v3 import GroundedOutput


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_backend: Literal["real", "fake", "replay"]
    api_request_timeout_s: float = Field(default=60, gt=0, le=3600)
    api_max_pending: int = Field(default=8, ge=1, le=128)
    api_embedding_cache: Path = Path("work/hf-cache/sentence-transformers")
    api_allow_model_download: bool = False
    api_collection: str | None = None
    api_fake_response_path: Path | None = None
    api_replay_catalog: Path = Path("work/replay-catalog.json")
    api_prompt_version: Literal["partner-copilot-v3"] = "partner-copilot-v3"
    api_parser_version: Literal["parser-v3"] = "parser-v3"


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date | None = None
    end_date: date | None = None
    aspect: (
        Literal["sabor", "tempo_entrega", "temperatura", "embalagem", "preco", "atendimento"] | None
    ) = None
    item: str | None = Field(default=None, min_length=1, max_length=200, strict=True)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def iso_dates(cls, value):
        import re

        if (
            value is not None
            and not isinstance(value, date)
            and (
                not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
            )
        ):
            raise ValueError("Use an ISO calendar date")
        return value

    @field_validator("item", mode="before")
    @classmethod
    def trim_item(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Inverted date window")
        return self


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    restaurant_id: str = Field(
        min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", strict=True
    )
    question: str = Field(min_length=1, max_length=2000, strict=True)
    filters: Filters | None = None
    k: int = Field(default=8, ge=1, le=12, strict=True)

    @field_validator("restaurant_id", "question", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    def filter_values(self) -> dict:
        return self.filters.model_dump(mode="json", exclude_none=True) if self.filters else {}


class Timings(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    embedding_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    search_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    embedding_search_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    generation_ms: float | None = Field(default=0, ge=0, allow_inf_nan=False)
    validation_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    replay_lookup_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    queue_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    total_ms: float = Field(default=0, ge=0, allow_inf_nan=False)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    backend: Literal["real", "fake", "replay"]
    is_replay: bool
    is_simulation: bool
    mode_label: str
    prompt_version: str = "partner-copilot-v3"
    parser_version: str = "parser-v3"
    backend_called: bool
    llm_called: bool
    context_origin: Literal["current_request", "recorded_eval_snapshot"]
    retrieved_documents: int = Field(ge=0)
    context_documents: int = Field(ge=0)
    timings_ms: Timings
    source_run: dict[str, Any] | None = None


class AskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["api-v1"] = "api-v1"
    result: GroundedOutput
    answer: str
    sources: list[str]
    abstained: bool
    abstention_reason: Literal["retriever_empty", "llm_insufficient_evidence"] | None
    metadata: Metadata

    @model_validator(mode="after")
    def consistent(self):
        if self.abstained != self.result.abstem:
            raise ValueError("Abstention flags differ")
        expected = list(
            dict.fromkeys(s.review_id for c in self.result.afirmacoes for s in c.fontes)
        )
        if expected != self.sources:
            raise ValueError("Sources must match structured claims")
        if self.abstained != (self.abstention_reason is not None):
            raise ValueError("Abstention reason inconsistent")
        return self


MESSAGES = {
    "invalid_request": "Entrada inválida.",
    "generation_contract_failed": "Não foi possível validar uma resposta.",
    "model_unavailable": "O modelo está indisponível.",
    "retrieval_unavailable": "A consulta às avaliações está indisponível.",
    "replay_unavailable": "O catálogo de demonstração não está pronto.",
    "replay_not_found": "A pergunta/configuração não está disponível na demonstração gravada.",
    "replay_snapshot_mismatch": "A gravação não corresponde à configuração ou ao snapshot.",
    "backend_timeout": "O tempo limite da requisição foi excedido.",
    "resource_busy": "A capacidade de requisições pendentes foi atingida.",
    "restaurant_not_found": "Restaurante não disponível no menu.",
    "http_error": "Rota ou método não disponível.",
    "internal_error": "Não foi possível concluir a requisição.",
}


class APIError(Exception):
    def __init__(self, status: int, code: str, details: dict | None = None):
        self.status, self.code, self.details = status, code, details or {}
        super().__init__(code)
