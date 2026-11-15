import asyncio
import json

from app.agent.events import AgentEvent, Citation
from app.agent.llm import Turn
from app.agent.loop import pick_citations, run_agent
from tests.agent_helpers import SERTRALINE, FixedTools, PlayedModel, call


def run(model: PlayedModel, tools: FixedTools | None = None, max_steps: int = 6) -> list[AgentEvent]:
    async def collect() -> list[AgentEvent]:
        return [e async for e in run_agent("Is 0.06 fair for sertraline 50 mg?", model, tools or FixedTools(),
                                           max_steps)]
    return asyncio.run(collect())


def test_streams_thinking_tool_call_result_answer_done_in_order() -> None:
    model = PlayedModel(
        Turn("Checking the benchmark.", [call("get_benchmark", drug="sertraline 50 mg")], 0.001, 300),
        Turn("Above the median. SERTRALINE HCL 50 MG TABLET (NDC 16729021615) is cheapest.", [], 0.002, 200),
    )
    events = run(model)

    assert [e.type for e in events] == ["thinking", "tool_call", "tool_result", "answer", "done"]
    assert events[0].data == {"text": "Checking the benchmark."}
    assert events[1].data["label"] == "Benchmark for sertraline 50 mg"
    assert events[2].data["ok"] is True and events[2].data["summary"] == "median $0.03484"
    assert events[3].data["citations"] == [{"item_id": SERTRALINE.item_id, "label": SERTRALINE.label,
                                            "href": "/items/ndc-16729021615"}]
    assert events[4].data == {"steps": 2, "tokens": 500, "cost_usd": 0.003}


def test_tool_result_goes_back_to_the_model_with_the_call_id() -> None:
    model = PlayedModel(Turn("", [call("get_benchmark", drug="x y")]), Turn("Done."))
    run(model)

    second = model.seen[1]
    assert second[2]["tool_calls"][0]["id"] == "call-get_benchmark"
    assert second[3]["role"] == "tool" and second[3]["tool_call_id"] == "call-get_benchmark"
    assert json.loads(second[3]["content"])["median"] == "0.03484"


def test_a_silent_tool_call_still_gets_a_thinking_line() -> None:
    events = run(PlayedModel(Turn("", [call("get_benchmark", drug="x y")]), Turn("Done.")))
    assert events[0].data["text"] == "Looking up the data."


def test_failing_and_invalid_tools_are_reported_to_the_model_not_raised() -> None:
    tools = FixedTools()
    model = PlayedModel(
        Turn("Two lookups.", [call("find_equivalents", drug="sertraline"), call("delete_everything"),
                              call("get_benchmark", drug="x")]),
        Turn("Could not look that up."),
    )
    results = [e.data for e in run(model, tools) if e.type == "tool_result"]

    assert [r["ok"] for r in results] == [False, False, False]
    assert results[0]["summary"] == "The lookup failed"
    assert results[1]["summary"] == "No tool named delete_everything"
    assert results[2]["summary"] == "Invalid arguments for get_benchmark"   # 'x' is shorter than 2 characters
    assert tools.calls == [("find_equivalents", "sertraline")]


def test_model_failure_ends_with_a_retryable_error() -> None:
    events = run(PlayedModel(ConnectionError("provider down")))
    assert [e.type for e in events] == ["error"]
    assert events[0].data["retryable"] is True
    assert "provider down" not in str(events[0].data["message"])   # provider details stay in the log


def test_stops_after_max_steps_without_looping_forever() -> None:
    looping = [Turn("Again.", [call("get_benchmark", drug="ab")]) for _ in range(3)]
    events = run(PlayedModel(*looping), max_steps=3)
    assert events[-1].type == "error"
    assert events[-1].data == {"message": "Stopped after 3 steps without an answer. Try a narrower question.",
                               "retryable": False}


def test_empty_answer_is_an_error() -> None:
    assert run(PlayedModel(Turn("")))[0].type == "error"


def test_citations_prefer_ndc_then_description_then_everything() -> None:
    a = Citation("ndc-00000000001", "ATORVASTATIN 20 MG TAB (NDC 00000000001)")
    b = Citation("ndc-00000000002", "ATORVASTATIN 20 MG TAB (NDC 00000000002)")
    c = Citation("ndc-00000000003", "METFORMIN 500 MG TAB (NDC 00000000003)")
    seen = {x.item_id: x for x in (a, b, c)}
    assert pick_citations("NDC 00000000002 is cheapest", seen) == [b]
    assert pick_citations("atorvastatin 20 mg tab is common", seen) == [a, b]
    assert pick_citations("Prices look normal.", seen) == [a, b, c]
