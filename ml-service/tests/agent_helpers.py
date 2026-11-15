"""Stand-ins shared by the agent tests: a model that plays fixed turns and tools that return fixed results."""

import json
from typing import Any

from app.agent.events import Citation
from app.agent.llm import ToolCall, Turn
from app.agent.tools import ToolResult

SERTRALINE = Citation("ndc-16729021615", "SERTRALINE HCL 50 MG TABLET (NDC 16729021615)")


def call(name: str, **args: Any) -> ToolCall:
    return ToolCall(f"call-{name}", name, json.dumps(args))


class PlayedModel:
    def __init__(self, *turns: Turn | Exception) -> None:
        self.turns = list(turns)
        self.seen: list[list[dict[str, Any]]] = []

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Turn:
        self.seen.append([dict(m) for m in messages])
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


class FixedTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def get_benchmark(self, drug: str) -> ToolResult:
        self.calls.append(("get_benchmark", drug))
        return ToolResult(True, "median $0.03484", {"median": "0.03484"}, [SERTRALINE])

    def list_anomalies(self, drug: str | None, limit: int) -> ToolResult:
        self.calls.append(("list_anomalies", (drug, limit)))
        return ToolResult(True, "0 flagged price moves", {"anomalies": []})

    def find_equivalents(self, drug: str) -> ToolResult:
        self.calls.append(("find_equivalents", drug))
        raise RuntimeError("connection reset")
