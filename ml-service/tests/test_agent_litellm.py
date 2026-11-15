"""The real LiteLLM Router, run offline with mocked replies: no key, no network, no cost."""

import asyncio
import json

from app.agent.llm import AgentLlmSettings, LiteLlmModel
from app.agent.tools import TOOL_SPECS

TOOL_CALL = {"id": "call_1", "type": "function",
             "function": {"name": "get_benchmark", "arguments": json.dumps({"drug": "sertraline 50 mg"})}}


def complete(**extra: object):  # type: ignore[no-untyped-def]
    model = LiteLlmModel(AgentLlmSettings(model="openai/gpt-4o-mini", extra=dict(extra)))
    return asyncio.run(model.complete([{"role": "user", "content": "Is 0.06 fair?"}], TOOL_SPECS))


def test_tool_calls_come_back_as_tool_calls() -> None:
    turn = complete(mock_response="Checking the benchmark.", mock_tool_calls=[TOOL_CALL])
    assert turn.content == "Checking the benchmark."
    assert [(c.id, c.name, json.loads(c.arguments)) for c in turn.tool_calls] == [
        ("call_1", "get_benchmark", {"drug": "sertraline 50 mg"})]


def test_a_plain_answer_has_no_tool_calls() -> None:
    turn = complete(mock_response="It is above the median.")
    assert turn.content == "It is above the median." and turn.tool_calls == []
    assert turn.tokens > 0


def test_gateway_settings_reach_the_deployment() -> None:
    settings = AgentLlmSettings(model="openai/benchline-agent", fallback_model="anthropic/claude-haiku-5-5",
                                api_base="http://gateway:4000", api_key="sk-virtual")
    router = LiteLlmModel(settings)._build_router()
    params = [d["litellm_params"] for d in router.registry().all()]
    assert [p["model"] for p in params] == ["openai/benchline-agent", "anthropic/claude-haiku-5-5"]
    assert all(p["api_base"] == "http://gateway:4000" for p in params)
    assert router.settings().fallbacks == [{"agent": ["agent-fallback"]}]
