"""The three read-only tools the agent may call: their specs, argument checks and dispatch."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.agent.events import Citation

MAX_ROWS = 10


class DrugArgs(BaseModel):
    drug: str = Field(min_length=2, max_length=80, description="Drug name, strength or both")


class AnomalyArgs(BaseModel):
    drug: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=5, ge=1, le=MAX_ROWS)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    summary: str  # one line for the trace
    data: dict[str, Any] = field(default_factory=dict)  # what the model sees
    citations: list[Citation] = field(default_factory=list)

    def for_model(self) -> str:
        return json.dumps({"ok": self.ok, "summary": self.summary, **self.data}, default=str)


class AgentTools(Protocol):
    def get_benchmark(self, drug: str) -> ToolResult: ...
    def list_anomalies(self, drug: str | None, limit: int) -> ToolResult: ...
    def find_equivalents(self, drug: str) -> ToolResult: ...


def _spec(name: str, description: str, model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}


TOOL_SPECS = [
    _spec("get_benchmark",
          "Latest weekly price benchmark (p10, p25, median, p75, p90 per unit, in USD) for a drug "
          "product group, from CMS NADAC acquisition costs.", DrugArgs),
    _spec("list_anomalies",
          "Price moves flagged as unusual by the anomaly model, newest first. Optionally for one drug.",
          AnomalyArgs),
    _spec("find_equivalents",
          "Products (NDCs) in the same group as a drug: same ingredient, strength and form, with their "
          "latest unit price, cheapest first.", DrugArgs),
]


def run_tool(tools: AgentTools, name: str, raw_arguments: str) -> ToolResult:
    """Validates arguments before anything touches data. Bad calls go back to the model as results."""
    try:
        arguments = json.loads(raw_arguments or "{}")
        if name == "get_benchmark":
            return tools.get_benchmark(DrugArgs.model_validate(arguments).drug)
        if name == "find_equivalents":
            return tools.find_equivalents(DrugArgs.model_validate(arguments).drug)
        if name == "list_anomalies":
            args = AnomalyArgs.model_validate(arguments)
            return tools.list_anomalies(args.drug, args.limit)
    except (json.JSONDecodeError, ValidationError) as error:
        return ToolResult(False, f"Invalid arguments for {name}", {"error": str(error)[:300]})
    return ToolResult(False, f"No tool named {name}", {"error": "unknown tool"})


def query_words(drug: str) -> list[str]:
    """'sertraline 50mg' -> ['SERTRALINE', '50', 'MG']: every word must appear in the group name."""
    spaced = re.sub(r"(\d)([A-Za-z])", r"\1 \2", drug.upper())
    return [w for w in re.split(r"[^A-Z0-9.]+", spaced) if w]
