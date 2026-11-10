"""FastAPI app: health endpoints, plus the anomaly consumer in the background."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.anomaly.worker import AnomalyWorker
from app.core.config import get_settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    worker = AnomalyWorker(settings)
    if settings.consumer_enabled:
        worker.start()
    try:
        yield
    finally:
        worker.stop()


app = FastAPI(
    title="Benchline ML service",
    lifespan=lifespan,
    docs_url=None,  # no interactive docs on a service that is not public
    redoc_url=None,
    openapi_url=None,
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
