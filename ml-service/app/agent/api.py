"""POST /api/v1/agent/runs: one question in, a stream of Server-Sent Events out."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from app.agent.auth import AuthError, Principal, authenticate
from app.agent.events import KEEP_ALIVE, AgentEvent, encode
from app.agent.limits import BudgetedModel, DailyBudget, RunLimiter
from app.agent.llm import AgentModel
from app.agent.loop import run_agent
from app.agent.tools import AgentTools
from app.core.config import get_settings

KEEP_ALIVE_SECONDS = 15.0
router = APIRouter(prefix="/api/v1/agent")


@dataclass
class AgentService:
    model: AgentModel | None
    tools: AgentTools
    limiter: RunLimiter
    budget: DailyBudget


class RunRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def problem(status: int, title: str, detail: str, headers: dict[str, str] | None = None) -> Response:
    return JSONResponse(status_code=status, media_type="application/problem+json", headers=headers,
                        content={"type": "about:blank", "title": title, "status": status,
                                 "detail": detail})


@router.post("/runs", response_model=None)
async def create_run(body: RunRequest, request: Request) -> Response:
    try:
        principal = authenticate(request.headers.get("authorization"), get_settings())
    except AuthError as error:
        title = {401: "Unauthorized", 403: "Forbidden"}.get(error.status, "Service Unavailable")
        return problem(error.status, title, error.detail)
    service: AgentService | None = getattr(request.app.state, "agent", None)
    if service is None or service.model is None:
        return problem(503, "Service Unavailable", "The assistant is not set up on this server.")
    if service.budget.exhausted:
        return problem(503, "Service Unavailable", "The assistant has used today's budget. "
                                                   "Try again tomorrow.")
    wait = service.limiter.acquire(principal.subject)
    if wait is not None:
        return problem(429, "Too Many Requests", f"Too many questions. Try again in {wait} seconds.",
                       {"Retry-After": str(wait)})
    return StreamingResponse(
        stream_run(body.question.strip(), service, principal),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


async def stream_run(question: str, service: AgentService, principal: Principal) -> AsyncIterator[str]:
    assert service.model is not None
    model = BudgetedModel(service.model, service.budget)
    events = run_agent(question, model, service.tools)
    pending: asyncio.Future[AgentEvent] | None = None
    try:
        yield encode(AgentEvent("run", {"run_id": str(uuid.uuid4())}), 0)
        n = 1
        while True:
            if pending is None:
                pending = asyncio.ensure_future(anext(events))
            done, _ = await asyncio.wait({pending}, timeout=KEEP_ALIVE_SECONDS)
            if not done:
                yield KEEP_ALIVE  # a slow model call must not look like a dead connection
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                return
            pending = None
            yield encode(event, n)
            n += 1
    finally:
        # Runs on a client disconnect too: the model call in flight is cancelled, nothing more is spent.
        # Shielded, because awaiting inside a cancelled scope would raise again before cleanup finished.
        service.limiter.release(principal.subject)
        with anyio.CancelScope(shield=True):
            if pending is not None:
                pending.cancel()
                with contextlib.suppress(BaseException):
                    await pending
            await events.aclose()
