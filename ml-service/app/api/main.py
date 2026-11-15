"""FastAPI app: health endpoints, the Ask Benchline agent, and the anomaly consumer."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.agent.api import router as agent_router
from app.agent.setup import build_agent_service
from app.anomaly.worker import AnomalyWorker
from app.core.config import get_settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    worker = AnomalyWorker(settings)
    if settings.consumer_enabled:
        worker.start()
    app.state.agent, close_agent = build_agent_service(settings)
    try:
        yield
    finally:
        worker.stop()
        close_agent()


app = FastAPI(
    title="Benchline ML service",
    lifespan=lifespan,
    docs_url=None,  # no interactive docs on a service that is not public
    redoc_url=None,
    openapi_url=None,
)
app.include_router(agent_router)
# The browser calls the agent directly. Only listed origins, only the one endpoint, no cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["POST"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
    max_age=600,
)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Full detail goes to the log; callers only get a generic problem document.
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": "Internal Server Error", "status": 500},
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:
        log.warning("database not ready: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ready"}
