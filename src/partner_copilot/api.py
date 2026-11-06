"""FastAPI facade with startup-owned resources, bounded work and honest execution modes."""

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from partner_copilot.api_models import (
    MESSAGES,
    APIError,
    APISettings,
    AskRequest,
    AskResponse,
    Metadata,
    Timings,
)
from partner_copilot.api_runtime import Resources, elapsed, profile
from partner_copilot.config import Settings
from partner_copilot.generation.contracts import GenerationContractError, InvalidCitationError
from partner_copilot.generation.output import parse_generation
from partner_copilot.generation.output_v3 import QuoteMismatchError, decode_output
from partner_copilot.generation.prompts import build_prompt

logger = logging.getLogger("partner_copilot.api")
LABELS = {
    "real": "Inferência ao vivo",
    "fake": "SIMULAÇÃO — resposta fixa de teste",
    "replay": "REPLAY — resposta gravada no Kaggle; não gerada agora",
}


class AskService:
    def __init__(self, resources: Resources):
        self.resources = resources
        self.semaphore = asyncio.Semaphore(1)
        self.tasks = set()

    async def close(self):
        if self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)

    async def ask(self, request: AskRequest, request_id: str, timings: Timings) -> AskResponse:
        if len(self.tasks) >= self.resources.api.api_max_pending:
            raise APIError(429, "resource_busy")
        operation_started = perf_counter()
        expired = threading.Event()
        task = asyncio.create_task(self.run(request, request_id, timings, expired))
        self.tasks.add(task)

        def done(finished):
            self.tasks.discard(finished)
            error = finished.exception() if not finished.cancelled() else None
            if expired.is_set():
                logger.info(
                    json.dumps(
                        {
                            "event": "discarded_completion",
                            "request_id": request_id,
                            "restaurant_id": request.restaurant_id,
                            "prompt_version": self.resources.settings.prompt_version,
                            "backend": self.resources.api.llm_backend,
                            "error_type": type(error).__name__ if error else None,
                        }
                    )
                )

        task.add_done_callback(done)
        try:
            return await asyncio.wait_for(
                asyncio.shield(task), self.resources.api.api_request_timeout_s
            )
        except asyncio.TimeoutError as exc:
            expired.set()
            raise APIError(504, "backend_timeout") from exc
        except asyncio.CancelledError:
            expired.set()
            raise
        finally:
            timings.total_ms = elapsed(operation_started)

    async def run(self, request, request_id, timings, expired):
        start = perf_counter()
        resources = self.resources
        backend = resources.api.llm_backend
        source = None
        reason = None
        called = False
        if backend == "replay":
            if resources.backend_error:
                raise resources.backend_error
            begin = perf_counter()
            entry = resources.replay.lookup(request)
            timings.replay_lookup_ms = elapsed(begin)
            timings.generation_ms = None
            raw, context = entry["raw"], entry["docs"]
            retrieved_count = entry["retrieved_count"]
            reason, source = entry["reason"], entry["source_run"]
            called = True
        else:
            if resources.index is None:
                raise APIError(503, "retrieval_unavailable")
            try:
                docs = await asyncio.to_thread(resources.index.retrieve, request, timings)
            except APIError:
                raise
            except Exception as exc:
                raise APIError(503, "retrieval_unavailable") from exc
            if expired.is_set():
                raise APIError(504, "backend_timeout")
            retrieved_count = len(docs)
            context = docs[: min(request.k, 8)]
            if not docs:
                raw = '{"abstem":true,"afirmacoes":[]}'
                reason = "retriever_empty"
            else:
                if resources.backend_error:
                    raise resources.backend_error
                if resources.llm is None:
                    raise APIError(503, "model_unavailable")
                begin = perf_counter()
                timings.generation_ms = None
                # Timeout shields this task: its semaphore is held until the worker really exits.
                async with self.semaphore:
                    timings.queue_ms = elapsed(begin)
                    if expired.is_set():
                        raise APIError(504, "backend_timeout")
                    try:
                        prompt = build_prompt(
                            request.question,
                            context,
                            prompt_version=resources.settings.prompt_version,
                        )
                        raw = await asyncio.to_thread(resources.llm.generate, prompt)
                    except GenerationContractError as exc:
                        raise APIError(
                            502, "generation_contract_failed", {"reason": "invalid_schema"}
                        ) from exc
                    except Exception as exc:
                        raise APIError(503, "model_unavailable") from exc
                timings.generation_ms = elapsed(begin)
                called = True
        if expired.is_set():
            raise APIError(504, "backend_timeout")
        validation = perf_counter()
        try:
            parsed = parse_generation(raw, context, parser_version="parser-v3")
            value = decode_output(raw).value
        except GenerationContractError as exc:
            reason_code = (
                "invalid_source_id"
                if isinstance(exc, InvalidCitationError)
                else "quote_mismatch"
                if isinstance(exc, QuoteMismatchError)
                else "invalid_schema"
            )
            raise APIError(502, "generation_contract_failed", {"reason": reason_code}) from exc
        if parsed.abstained and reason is None:
            reason = "llm_insufficient_evidence"
        result = AskResponse(
            result=value,
            answer=parsed.answer,
            sources=parsed.sources,
            abstained=parsed.abstained,
            abstention_reason=reason,
            metadata=Metadata(
                request_id=request_id,
                backend=backend,
                is_replay=backend == "replay",
                is_simulation=backend == "fake",
                mode_label=LABELS[backend],
                backend_called=called,
                llm_called=called and backend == "real",
                context_origin="recorded_eval_snapshot"
                if backend == "replay"
                else "current_request",
                retrieved_documents=retrieved_count,
                context_documents=len(context),
                timings_ms=timings,
                source_run=source,
            ),
        )
        timings.validation_ms = elapsed(validation)
        timings.total_ms = elapsed(start)
        return result


def create_app(api_settings: APISettings | None = None, *, resources_factory=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        api = api_settings if api_settings is not None else APISettings()
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        factory = resources_factory or Resources
        resources = factory(profile(Settings(), api), api)
        await asyncio.to_thread(resources.start)
        app.state.service = AskService(resources)
        yield
        await app.state.service.close()

    app = FastAPI(title="PartnerCopilot", version="1.0", lifespan=lifespan)

    def backend():
        service = getattr(app.state, "service", None)
        return service.resources.api.llm_backend if service else None

    def error_response(request, status, code, details=None):
        request.state.error_code = code
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": MESSAGES.get(code, "Não foi possível concluir a requisição."),
                    "details": details or {},
                },
                "request_id": request.state.request_id,
                "backend": backend(),
            },
        )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.request_id = str(uuid4())
        request.state.restaurant_id = None
        request.state.error_code = None
        request.state.error_type = None
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            request.state.error_type = type(exc).__name__
            response = error_response(request, 500, "internal_error")
        response.headers["X-Request-ID"] = request.state.request_id
        timing = getattr(request.state, "timings", None)
        logger.info(
            json.dumps(
                {
                    "event": "request_completed",
                    "request_id": request.state.request_id,
                    "restaurant_id": request.state.restaurant_id,
                    "backend": backend(),
                    "prompt_version": "partner-copilot-v3",
                    "status_code": response.status_code,
                    "latency_ms": elapsed(started),
                    "timings_ms": timing.model_dump() if timing else None,
                    "error_code": request.state.error_code,
                    "error_type": request.state.error_type,
                },
                ensure_ascii=False,
            )
        )
        return response

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        request.state.error_type = (
            type(exc.__cause__).__name__ if exc.__cause__ else type(exc).__name__
        )
        return error_response(request, exc.status, exc.code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def input_error(request: Request, exc: RequestValidationError):
        request.state.error_type = "RequestValidationError"
        allowed = {
            "body",
            "question",
            "restaurant_id",
            "filters",
            "k",
            "start_date",
            "end_date",
            "aspect",
            "item",
        }
        details = {
            "fields": [
                {
                    "field": ".".join(
                        str(p) if p in allowed else "unknown_field" for p in e["loc"]
                    ),
                    "rule": e["type"],
                }
                for e in exc.errors()
            ]
        }
        return error_response(request, 422, "invalid_request", details)

    @app.exception_handler(HTTPException)
    async def route_error(request: Request, exc: HTTPException):
        return error_response(request, exc.status_code, "http_error")

    @app.get("/health")
    @app.get("/v1/health", include_in_schema=False)
    async def health(request: Request):
        service = app.state.service
        r = service.resources
        return JSONResponse(
            status_code=200 if r.healthy() else 503,
            content={
                "status": "ok" if r.healthy() else "degraded",
                "backend": backend(),
                "mode_label": LABELS[backend()],
                "components": r.components,
                "active_requests": len(service.tasks),
                "request_id": request.state.request_id,
            },
        )

    @app.post("/ask", response_model=AskResponse)
    @app.post("/v1/ask", response_model=AskResponse, include_in_schema=False)
    async def ask(body: AskRequest, request: Request):
        request.state.restaurant_id = body.restaurant_id
        request.state.timings = Timings()
        return await app.state.service.ask(body, request.state.request_id, request.state.timings)

    def menu():
        r = app.state.service.resources
        if backend() == "replay" and r.backend_error:
            raise r.backend_error
        if backend() != "replay" and r.index is None:
            raise APIError(503, "retrieval_unavailable")
        return r.menu

    @app.get("/restaurants")
    @app.get("/v1/restaurants", include_in_schema=False)
    async def restaurants():
        return {"backend": backend(), "mode_label": LABELS[backend()], "restaurants": menu()}

    @app.get("/restaurants/{restaurant_id}/items")
    @app.get("/v1/restaurants/{restaurant_id}/items", include_in_schema=False)
    async def items(restaurant_id: str):
        match = next((r for r in menu() if r["restaurant_id"] == restaurant_id), None)
        if match is None:
            raise APIError(404, "restaurant_not_found")
        return {
            "restaurant_id": restaurant_id,
            "items": match["items"],
            "backend": backend(),
            "mode_label": LABELS[backend()],
        }

    return app


app = create_app()
