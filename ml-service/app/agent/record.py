"""Records agent runs as SSE files for the public demo and the browser tests.

    uv run python -m app.agent.record                 # scripted model, free, deterministic
    uv run python -m app.agent.record --live          # the model in BENCHLINE_LLM_MODEL, costs a few cents

Both run the server's own stream function over the demo snapshot, so a recording is byte-for-byte
what the endpoint sends. tests/test_agent_recording.py fails if the committed files drift from it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agent.api import AgentService, stream_run
from app.agent.auth import Principal
from app.agent.limits import DailyBudget, RunLimiter
from app.agent.llm import AgentLlmSettings, AgentModel, LiteLlmModel, ToolCall, Turn
from app.agent.tools_snapshot import SnapshotTools

ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = ROOT / "web" / "public" / "demo"
Results = dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Step:
    thinking: str
    calls: list[tuple[str, dict[str, Any]]]


class ScriptedModel:
    """Plays fixed steps, then writes its answer from what the tools actually returned."""

    def __init__(self, steps: list[Step], answer: Callable[[Results], str]) -> None:
        self._steps = steps
        self._answer = answer

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Turn:
        done = sum(1 for m in messages if m["role"] == "assistant")
        if done < len(self._steps):
            step = self._steps[done]
            calls = [ToolCall(f"call_{done}_{i}", name, json.dumps(args))
                     for i, (name, args) in enumerate(step.calls)]
            return Turn(step.thinking, calls)
        names = {c["id"]: c["function"]["name"] for m in messages for c in m.get("tool_calls") or []}
        results = {names[m["tool_call_id"]]: json.loads(m["content"]) for m in messages if m["role"] == "tool"}
        return Turn(self._answer(results))


def _fair_price(price: Decimal) -> Callable[[Results], str]:
    def answer(r: Results) -> str:
        b, eq, an = r["get_benchmark"], r["find_equivalents"], r["list_anomalies"]
        q = {k: Decimal(v) for k, v in b["unit_price_usd"].items()}
        where = ("below the p25" if price < q["p25"] else "between the p25 and the median" if price <= q["median"]
                 else "between the median and the p90" if price <= q["p90"] else "above the p90")
        cheapest = eq["products"][0]
        moves = (f"{len(an['anomalies'])} recent price moves in this group were flagged as unusual"
                 if an["anomalies"] else "No unusual price moves are flagged for this group")
        return (f"${price} per tablet is {where} for {b['group']}. For the week of {b['as_of_week']} the median "
                f"is ${q['median']}, the p25 ${q['p25']} and the p90 ${q['p90']}, across "
                f"{b['products_in_benchmark']} products. The cheapest equivalent is {cheapest['description']} "
                f"(NDC {cheapest['ndc11']}) at ${cheapest['latest_price']}. {moves}. These are NADAC prices, "
                "what retail pharmacies pay on average, not a hospital contract price.")
    return answer


def _odd_moves(r: Results) -> str:
    rows = r["list_anomalies"]["anomalies"]
    if not rows:
        return "No unusual price moves are flagged for this drug."
    top = max(rows, key=lambda a: a["score"])
    return (f"{len(rows)} recent price moves for {top['group']} are flagged. The largest is "
            f"{top['description']} (NDC {top['item_id'].removeprefix('ndc-')}): ${top['previous_price']} to "
            f"${top['new_price']} on {top['effective_date']} ({top['change_pct']}%), score {top['score']}. "
            f"The group's median is ${r['get_benchmark']['unit_price_usd']['median']}, so check the item page "
            "before treating the new price as the market.")


RECORDINGS: dict[str, tuple[str, Callable[[], AgentModel]]] = {
    "fair-price-sertraline": (
        "Is $0.06 per tablet a fair price for sertraline 50 mg?",
        lambda: ScriptedModel([
            Step("I'll check the benchmark for sertraline 50 mg and the equivalent products.",
                 [("get_benchmark", {"drug": "sertraline 50 mg"}), ("find_equivalents", {"drug": "sertraline 50 mg"})]),
            Step("Checking for unusual recent price moves in the same group.",
                 [("list_anomalies", {"drug": "sertraline 50 mg", "limit": 5})]),
        ], _fair_price(Decimal("0.06")))),
    "odd-moves-omeprazole": (
        "Have there been any unusual price moves for omeprazole 20 mg?",
        lambda: ScriptedModel([
            Step("I'll list the flagged price moves for omeprazole 20 mg.",
                 [("list_anomalies", {"drug": "omeprazole 20 mg", "limit": 5})]),
            Step("Getting the benchmark so the moves have context.",
                 [("get_benchmark", {"drug": "omeprazole 20 mg"})]),
        ], _odd_moves)),
}


async def record(question: str, model: AgentModel, demo_dir: Path = DEMO_DIR) -> str:
    service = AgentService(model, SnapshotTools(demo_dir), RunLimiter(1000), DailyBudget(10.0))
    chunks = [c async for c in stream_run(question, service, Principal("recorder", frozenset()))]
    body = re.sub(r'"run_id":"[^"]+"', '"run_id":"recorded"', "".join(chunks))
    return body


def header(kind: str) -> str:
    return (f": Recorded from Benchline's agent stream over the demo snapshot. Model: {kind}.\n"
            ": Re-record with: uv run python -m app.agent.record\n\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="use BENCHLINE_LLM_MODEL instead of the script")
    parser.add_argument("--out", type=Path, default=DEMO_DIR / "agent")
    args = parser.parse_args()
    settings = AgentLlmSettings.from_env() if args.live else None
    if args.live and settings is None:
        raise SystemExit("Set BENCHLINE_LLM_MODEL (and its key) to record from a real model")
    kind = settings.model if settings else "scripted"
    args.out.mkdir(parents=True, exist_ok=True)
    index = []
    for name, (question, scripted) in RECORDINGS.items():
        model = LiteLlmModel(settings) if settings else scripted()
        (args.out / f"{name}.sse").write_text(header(kind) + asyncio.run(record(question, model)))
        index.append({"id": name, "question": question, "model": kind})
        print(f"wrote {name}.sse")
    (args.out / "index.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
