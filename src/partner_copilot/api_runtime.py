"""Startup-owned resources and directly timed CPU retrieval for the HTTP facade."""

import json
import logging
from time import perf_counter

from partner_copilot.api_models import APIError, APISettings, AskRequest, Timings
from partner_copilot.api_replay import ReplayCatalog
from partner_copilot.config import Settings
from partner_copilot.data_splits import validate_rag_collection_ids
from partner_copilot.generation.output import parser_identity
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.schemas import RetrievedDoc, Review

logger = logging.getLogger("partner_copilot.api")


def elapsed(start: float) -> float:
    return (perf_counter() - start) * 1000


def profile(base: Settings, api: APISettings) -> Settings:
    return Settings(
        _env_file=None,
        **{
            **base.model_dump(),
            "prompt_version": api.api_prompt_version,
            "parser_version": api.api_parser_version,
            "context_k": 8,
            "retrieval_k": 8,
            "retrieval_min_score": 0.25,
            "max_new_tokens": 512,
            "temperature": 0,
            "generation_seed": 42,
            "embedding_device": "cpu",
        },
    )


def where_for(request: AskRequest) -> dict:
    filters = [{"restaurant_id": request.restaurant_id}]
    if request.filters:
        f = request.filters
        if f.item is not None:
            filters.append({"item": f.item})
        if f.aspect is not None:
            filters.append({f"aspect_{f.aspect}": "neg"})
        if f.start_date is not None:
            filters.append({"created_at_int": {"$gte": int(f.start_date.strftime("%Y%m%d"))}})
        if f.end_date is not None:
            filters.append({"created_at_int": {"$lte": int(f.end_date.strftime("%Y%m%d"))}})
    return filters[0] if len(filters) == 1 else {"$and": filters}


class CPUIndex:
    def __init__(self, store, embedder, settings: Settings):
        self.store, self.embedder, self.settings = store, embedder, settings
        self.tokenizer_info = (
            embedder.document_tokenizer() if hasattr(embedder, "document_tokenizer") else None
        )

    def retrieve(self, request: AskRequest, timings: Timings) -> list[RetrievedDoc]:
        whole = perf_counter()
        started = perf_counter()
        if self.tokenizer_info:
            tokenizer, limit, _ = self.tokenizer_info
            length = len(tokenizer(self.embedder.query_prefix + request.question)["input_ids"])
            if length > limit:
                raise APIError(
                    422,
                    "invalid_request",
                    {
                        "fields": [
                            {"field": "question", "rule": "embedding_token_limit", "limit": limit}
                        ]
                    },
                )
        vector = self.embedder.embed_query(request.question)
        timings.embedding_ms = elapsed(started)
        started = perf_counter()
        count = self.store.count()
        if not count:
            timings.search_ms = elapsed(started)
            timings.embedding_search_ms = elapsed(whole)
            return []
        result = self.store.col.query(
            query_embeddings=[vector],
            n_results=min(request.k * 2, count),
            where=where_for(request),
            include=["documents", "metadatas", "distances"],
        )
        docs = []
        for identifier, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            review = Review.model_validate(
                {
                    **metadata,
                    "id": metadata.get("review_id", identifier),
                    "text": text,
                    "item": metadata.get("item") or None,
                    "aspects": json.loads(metadata["aspects_json"]),
                }
            )
            if 1 - distance >= self.settings.retrieval_min_score:
                docs.append(
                    RetrievedDoc(
                        review=review,
                        score=1 - distance,
                        document_id=identifier,
                        chunk_index=metadata.get("chunk_index", 0),
                        chunk_count=metadata.get("chunk_count", 1),
                    )
                )
        timings.search_ms = elapsed(started)
        timings.embedding_search_ms = elapsed(whole)
        return docs[: request.k]

    def restaurants(self) -> list[dict]:
        grouped = {}
        for offset in range(0, self.store.count(), 1000):
            records = self.store.col.get(limit=1000, offset=offset, include=["metadatas"])
            for m in records["metadatas"]:
                grouped.setdefault(m["restaurant_id"], set())
                if m.get("item"):
                    grouped[m["restaurant_id"]].add(m["item"])
        names = {}
        path = self.settings.data_raw_dir / "restaurants.json"
        if path.exists():
            names = {
                r["restaurant_id"]: r["name"] for r in json.loads(path.read_text(encoding="utf-8"))
            }
        return [
            {"restaurant_id": i, "name": names.get(i, i), "items": sorted(items)}
            for i, items in sorted(grouped.items())
        ]


class FixedLLM:
    def __init__(self, raw: str):
        self.raw = raw

    def generate(self, prompt: str) -> str:
        return self.raw


def load_embedder(settings, api):
    from sentence_transformers import SentenceTransformer

    from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder

    def load(name, device):
        return SentenceTransformer(
            name,
            device=device,
            cache_folder=str(api.api_embedding_cache),
            local_files_only=not api.api_allow_model_download,
            trust_remote_code=False,
        )

    embedder = SentenceTransformerEmbedder(settings, model_factory=load)
    embedder.document_tokenizer()
    return embedder


def load_index(settings, api, embedder):
    from partner_copilot.ingestion.chroma_store import ChromaStore

    store = ChromaStore(
        settings=settings, embedder=embedder, collection=api.api_collection, create_if_missing=False
    )
    validate_rag_collection_ids(store.review_ids(), settings.data_splits_dir)
    return CPUIndex(store, embedder, settings)


def load_backend(settings, api):
    if api.llm_backend == "fake":
        raw = (
            api.api_fake_response_path.read_text(encoding="utf-8")
            if api.api_fake_response_path
            else '{"abstem":true,"afirmacoes":[]}'
        )
        return FixedLLM(raw)
    from partner_copilot.generation.llm import Mistral4bit

    return Mistral4bit(settings=settings)


class Resources:
    def __init__(self, settings: Settings, api: APISettings):
        self.settings, self.api = settings, api
        self.index = self.llm = self.replay = None
        self.menu = []
        self.full_reviews = {}
        self.components = {
            name: {"status": "not_required"} for name in ["index", "embedder", "llm", "replay"]
        }
        self.backend_error = None
        self._started = False

    def failed(self, component: str, code: str, exc: Exception):
        self.components[component] = {
            "status": "unavailable",
            "error": code,
            "error_type": type(exc).__name__,
        }
        logger.warning(
            json.dumps(
                {
                    "event": "startup_component_unavailable",
                    "component": component,
                    "error_code": code,
                    "error_type": type(exc).__name__,
                }
            )
        )

    def start(self):
        if self._started:
            return
        self._started = True
        try:
            load_prompt_template(self.settings.prompt_version)
            parser_identity(self.settings.parser_version)
        except Exception as exc:
            self.failed("llm", "model_unavailable", exc)
            self.backend_error = APIError(503, "model_unavailable")
            return
        if self.api.llm_backend == "replay":
            try:
                self.replay = ReplayCatalog(self.api.api_replay_catalog, self.settings)
                self.menu = self.replay.restaurants()
                self.components["replay"] = {"status": "ready"}
            except Exception as exc:
                self.backend_error = (
                    exc if isinstance(exc, APIError) else APIError(503, "replay_unavailable")
                )
                self.failed("replay", self.backend_error.code, exc)
            return
        embedder = None
        try:
            embedder = load_embedder(self.settings, self.api)
            self.components["embedder"] = {"status": "ready"}
        except Exception as exc:
            self.failed("embedder", "retrieval_unavailable", exc)
        try:
            if embedder is None:
                raise APIError(503, "retrieval_unavailable")
            self.index = load_index(self.settings, self.api, embedder)
            self.full_reviews = {
                review.id: review
                for line in (self.settings.data_splits_dir / "rag.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
                for review in [Review.model_validate_json(line)]
            }
            self.menu = self.index.restaurants()
            self.components["index"] = {"status": "ready", "documents": self.index.store.count()}
        except Exception as exc:
            self.index = None
            self.menu = []
            self.failed("index", "retrieval_unavailable", exc)
        try:
            self.llm = load_backend(self.settings, self.api)
            self.components["llm"] = {"status": "ready"}
        except Exception as exc:
            self.failed("llm", "model_unavailable", exc)
            self.backend_error = APIError(503, "model_unavailable")

    def healthy(self) -> bool:
        return all(c["status"] != "unavailable" for c in self.components.values())
