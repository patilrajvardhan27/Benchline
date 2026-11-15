"""Builds the agent's model, tools and limits from settings at startup."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from psycopg_pool import ConnectionPool

from app.agent.api import AgentService
from app.agent.limits import DailyBudget, RunLimiter
from app.agent.llm import AgentLlmSettings, LiteLlmModel
from app.agent.tools import AgentTools
from app.agent.tools_db import PostgresTools
from app.agent.tools_snapshot import SnapshotTools
from app.core.config import Settings

log = logging.getLogger(__name__)


def build_agent_service(settings: Settings) -> tuple[AgentService, Callable[[], None]]:
    llm = AgentLlmSettings.from_env()
    model = LiteLlmModel(llm) if llm else None
    if model is None:
        log.info("Ask Benchline is off: set BENCHLINE_LLM_MODEL to turn it on")
    close: Callable[[], None] = lambda: None  # noqa: E731
    tools: AgentTools
    if settings.agent_snapshot_dir:
        tools = SnapshotTools(Path(settings.agent_snapshot_dir))
    else:
        # Opened lazily, so the service starts (and stays healthy) while the database is down.
        pool = ConnectionPool(settings.database_url, min_size=0, max_size=4, open=False,
                              kwargs={"connect_timeout": 3})
        pool.open(wait=False)
        tools, close = PostgresTools(pool), pool.close
    service = AgentService(model, tools, RunLimiter(settings.agent_runs_per_hour),
                           DailyBudget(settings.agent_daily_usd))
    return service, close
