"""The model behind the agent, called through LiteLLM with the same settings as the item normalizer.

BENCHLINE_LLM_MODEL picks the model; BENCHLINE_LLM_FALLBACK_MODEL adds a fallback; BENCHLINE_LLM_API_BASE
and BENCHLINE_LLM_API_KEY route through a LiteLLM gateway with a budget-capped virtual key.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)
ALIAS = "agent"
FALLBACK_ALIAS = "agent-fallback"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, exactly as the model wrote it


@dataclass(frozen=True)
class Turn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    cost_usd: float = 0.0
    tokens: int = 0


class AgentModel(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Turn: ...


@dataclass(frozen=True)
class AgentLlmSettings:
    model: str
    fallback_model: str = ""
    api_base: str = ""
    api_key: str = ""
    timeout: float = 30.0
    retries: int = 1
    max_tokens: int = 700
    extra: dict[str, Any] = field(default_factory=dict)  # passed to every call, used by tests

    @classmethod
    def from_env(cls) -> AgentLlmSettings | None:
        model = os.environ.get("BENCHLINE_LLM_MODEL", "")
        if not model:
            return None
        return cls(model=model,
                   fallback_model=os.environ.get("BENCHLINE_LLM_FALLBACK_MODEL", ""),
                   api_base=os.environ.get("BENCHLINE_LLM_API_BASE", ""),
                   api_key=os.environ.get("BENCHLINE_LLM_API_KEY", ""),
                   timeout=float(os.environ.get("BENCHLINE_LLM_TIMEOUT", "30")))


class LiteLlmModel:
    def __init__(self, settings: AgentLlmSettings) -> None:
        self.settings = settings
        self._router: Any = None

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Turn:
        if self._router is None:
            self._router = self._build_router()
        response = await self._router.acompletion(
            model=ALIAS, messages=messages, tools=tools, tool_choice="auto",
            max_tokens=self.settings.max_tokens, **self.settings.extra)
        message = response.choices[0].message
        calls = [ToolCall(c.id, c.function.name, c.function.arguments or "{}")
                 for c in (getattr(message, "tool_calls", None) or [])]
        cost = float((getattr(response, "_hidden_params", None) or {}).get("response_cost") or 0.0)
        tokens = int(getattr(getattr(response, "usage", None), "total_tokens", 0) or 0)
        return Turn((message.content or "").strip(), calls, cost, tokens)

    def _build_router(self) -> Any:
        import litellm  # large; only imported once the agent is used
        from litellm.router import Router

        litellm.suppress_debug_info = True
        for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
            logging.getLogger(name).setLevel(logging.WARNING)
        s = self.settings
        gateway = {"api_base": s.api_base, "api_key": s.api_key} if s.api_base else {}
        deployments = [{"model_name": ALIAS, "litellm_params": {"model": s.model, **gateway}}]
        fallbacks: list[dict[str, list[str]]] = []
        if s.fallback_model:
            deployments.append({"model_name": FALLBACK_ALIAS,
                                "litellm_params": {"model": s.fallback_model, **gateway}})
            fallbacks = [{ALIAS: [FALLBACK_ALIAS]}]
        return Router(model_list=deployments, num_retries=s.retries, timeout=s.timeout,
                      fallbacks=fallbacks, disable_cooldowns=not s.fallback_model)
