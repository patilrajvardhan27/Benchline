"""Per-user run limits and a daily spend cap. In memory: fine for one replica, which is what runs."""

from __future__ import annotations

import datetime as dt
import threading
import time
from collections import defaultdict, deque
from typing import Any

from app.agent.llm import AgentModel, Turn

HOUR = 3600.0


class RunLimiter:
    """At most `per_hour` runs per user, and one at a time."""

    def __init__(self, per_hour: int, clock: Any = time.monotonic) -> None:
        self._per_hour = per_hour
        self._clock = clock
        self._starts: dict[str, deque[float]] = defaultdict(deque)
        self._running: set[str] = set()
        self._lock = threading.Lock()

    def acquire(self, user: str) -> int | None:
        """None when the run may start, otherwise seconds to wait."""
        now = self._clock()
        with self._lock:
            starts = self._starts[user]
            while starts and now - starts[0] >= HOUR:
                starts.popleft()
            if user in self._running:
                return 5
            if len(starts) >= self._per_hour:
                return int(HOUR - (now - starts[0])) + 1
            starts.append(now)
            self._running.add(user)
            return None

    def release(self, user: str) -> None:
        with self._lock:
            self._running.discard(user)


class BudgetExceeded(Exception):
    pass


class DailyBudget:
    def __init__(self, limit_usd: float, today: Any = lambda: dt.datetime.now(dt.UTC).date()) -> None:
        self._limit = limit_usd
        self._today = today
        self._day = today()
        self._spent = 0.0
        self._lock = threading.Lock()

    @property
    def exhausted(self) -> bool:
        with self._lock:
            self._roll()
            return self._spent >= self._limit

    def add(self, usd: float) -> None:
        with self._lock:
            self._roll()
            self._spent += usd

    def _roll(self) -> None:
        if self._today() != self._day:
            self._day, self._spent = self._today(), 0.0


class BudgetedModel:
    """Checks the cap before every model call, so one long run cannot overspend by much."""

    def __init__(self, model: AgentModel, budget: DailyBudget) -> None:
        self._model = model
        self._budget = budget

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Turn:
        if self._budget.exhausted:
            raise BudgetExceeded("daily model budget used")
        turn = await self._model.complete(messages, tools)
        self._budget.add(turn.cost_usd)
        return turn
