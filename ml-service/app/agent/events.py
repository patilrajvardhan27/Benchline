"""Events the agent streams to the browser, and their Server-Sent Events encoding."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

EventType = Literal["run", "thinking", "tool_call", "tool_result", "answer", "error", "done"]


@dataclass(frozen=True)
class Citation:
    item_id: str
    label: str

    @property
    def href(self) -> str:
        return f"/items/{self.item_id}"


@dataclass(frozen=True)
class AgentEvent:
    type: EventType
    data: dict[str, object] = field(default_factory=dict)


def citations_json(citations: list[Citation]) -> list[dict[str, str]]:
    return [{**asdict(c), "href": c.href} for c in citations]


def encode(event: AgentEvent, event_id: int) -> str:
    """One SSE message. JSON never contains a raw newline, so one data line is enough."""
    payload = json.dumps(event.data, separators=(",", ":"), ensure_ascii=False)
    return f"id: {event_id}\nevent: {event.type}\ndata: {payload}\n\n"


KEEP_ALIVE = ": keep-alive\n\n"
