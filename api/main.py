"""FastAPI app: ``POST /chat`` (gate-first SSE) and ``GET /health``.

Run: ``uvicorn api.main:app --reload``  (see docs/api-contract.md)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from gatekeeper import MODELS, gate, load_settings
from gatekeeper.config import Settings
from gatekeeper.schema import FACULTY, GateDecision

from .answerer import Answerer, Turn, get_answerer, tokenize
from .ratelimit import RateLimiter
from .reqlog import log_request, setup_logging
from .sse import SSE_HEADERS, sse

log = logging.getLogger(__name__)

DEFAULT_ORIGINS = "http://localhost:3000"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    scope: list[str] | None = None  # program ids: AIT | DSBA | BIT | IT
    history: list[Turn] = Field(default_factory=list, max_length=50)


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _meta(decision: GateDecision) -> dict:
    return {
        "category": decision.category,
        "language": decision.language,
        "faculty": FACULTY,
        "programs": decision.programs,
        "question_kind": decision.question_kind,
        "decided_by": decision.decided_by,
        "model_used": decision.model_used,
    }


def create_app(
    *,
    answerer: Answerer | None = None,
    allowed_origins: list[str] | None = None,
    rate_limit_per_minute: int | None = None,
    gate_settings: Settings | None = None,
    log_content: bool | None = None,
    trust_proxy: bool | None = None,
    answer_event_timeout_s: float | None = None,
) -> FastAPI:
    """Build the app; every knob falls back to an environment variable."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass

    setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
    answerer = answerer or get_answerer()
    origins = allowed_origins if allowed_origins is not None else [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()
    ]
    per_minute = rate_limit_per_minute if rate_limit_per_minute is not None else int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    settings = gate_settings or load_settings()
    log_content = _env_bool("LOG_CONTENT") if log_content is None else log_content
    trust_proxy = _env_bool("TRUST_PROXY") if trust_proxy is None else trust_proxy
    event_timeout = answer_event_timeout_s if answer_event_timeout_s is not None else float(os.environ.get("ANSWER_EVENT_TIMEOUT_S", "60"))
    limiter = RateLimiter(per_minute)

    app = FastAPI(title="KMITL IT curriculum chat", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.answerer = answerer
    app.state.gate_settings = settings

    def client_ip(request: Request) -> str:
        if trust_proxy:
            fwd = request.headers.get("x-forwarded-for")
            if fwd:
                return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "answerer": answerer.name, "models": MODELS}

    @app.post("/chat")
    async def chat(req: ChatRequest, request: Request):
        ip = client_ip(request)
        wait = limiter.check(ip)
        if wait is not None:
            log_request(status="rate_limited", client_ip=ip)
            return JSONResponse(
                status_code=429,
                content={"code": "rate_limited", "message": "Too many requests; please slow down."},
                headers={"Retry-After": str(max(1, int(wait) + 1))},
            )
        return StreamingResponse(
            _chat_stream(request, req, ip),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    async def _chat_stream(request: Request, req: ChatRequest, ip: str) -> AsyncIterator[bytes]:
        started = time.perf_counter()
        status = "ok"
        decision: GateDecision | None = None
        model_used: str | None = None
        gate_ms: int | None = None
        answer_it: AsyncIterator | None = None
        scope = [s.strip().upper() for s in req.scope] if req.scope else None
        try:
            # 1. gate (has its own retry + fallback; the wait_for is a hard ceiling)
            try:
                decision = await asyncio.wait_for(
                    gate(req.message, scope_filter=scope, settings=settings),
                    timeout=settings.timeout_s * settings.max_attempts + 5,
                )
            except Exception:  # any gate failure must become an SSE error, never hang the stream
                log.exception("gate failed")
                status = "error:gate_failed"
                yield sse("error", {"code": "gate_failed", "message": "Could not classify the request."})
                return
            gate_ms = decision.latency_ms
            model_used = decision.model_used
            yield sse("meta", _meta(decision))

            # 2a. not in scope: stream the fixed reply, no citations
            if decision.category != "in_scope":
                for tok in tokenize(decision.direct_reply or ""):
                    yield sse("token", {"text": tok})
                yield sse("done", {"latency_ms": int((time.perf_counter() - started) * 1000), "model_used": model_used})
                return

            # 2b. in scope: hand off to the answerer
            answer_it = answerer.answer(req.message, decision, scope, req.history).__aiter__()
            citations_sent = False
            try:
                while True:
                    if await request.is_disconnected():
                        status = "disconnected"
                        return
                    try:
                        ev = await asyncio.wait_for(answer_it.__anext__(), timeout=event_timeout)
                    except StopAsyncIteration:
                        break
                    if ev.type == "token":
                        yield sse("token", {"text": ev.text or ""})
                    elif ev.type == "citations":
                        citations_sent = True
                        yield sse("citations", {"citations": [c.model_dump() for c in (ev.citations or [])]})
                    elif ev.type == "done":
                        model_used = ev.model_used or model_used
            except TimeoutError:
                status = "error:upstream_timeout"
                yield sse("error", {"code": "upstream_timeout", "message": "The answer engine did not respond in time."})
                return
            except Exception:  # map any answerer failure to an error event
                log.exception("answerer failed")
                status = "error:answerer_failed"
                yield sse("error", {"code": "answerer_failed", "message": "The answer engine failed."})
                return
            if not citations_sent:
                yield sse("citations", {"citations": []})
            yield sse("done", {"latency_ms": int((time.perf_counter() - started) * 1000), "model_used": model_used})
        except (asyncio.CancelledError, GeneratorExit):
            status = "disconnected"
            raise
        finally:
            if answer_it is not None and hasattr(answer_it, "aclose"):
                try:
                    await answer_it.aclose()  # cancels the upstream ThaiLLM stream
                except Exception:  # best-effort cleanup; the response is already finished
                    log.debug("answerer aclose() raised", exc_info=True)
            log_request(
                status=status,
                category=decision.category if decision else None,
                decided_by=decision.decided_by if decision else None,
                programs=decision.programs if decision else None,
                model_used=model_used,
                gate_ms=gate_ms,
                total_ms=int((time.perf_counter() - started) * 1000),
                answerer=answerer.name,
                client_ip=ip,
                conversation_id=req.conversation_id,
                message=req.message if log_content else None,
            )

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8000")), reload=True)
