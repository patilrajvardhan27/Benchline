"""Last-resort normalization with an LLM, called through LiteLLM.

Everything the model says is checked before it is used. It may name a drug from its own knowledge
(a brand name maps to its ingredient), but then the row is flagged for a person to review. A strength
the description does not contain is thrown away. A failed call never stops the run.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import ValidationError

from benchline_pipelines.normalize.cache import JsonlCache, cache_key
from benchline_pipelines.normalize.checks import LlmParse, interpret, parse_json
from benchline_pipelines.normalize.prompt import SYSTEM_PROMPT

log = logging.getLogger(__name__)
PROMPT_VERSION = "v1"
ALIAS = "normalizer"
FALLBACK_ALIAS = "normalizer-fallback"
@dataclass(frozen=True)
class LlmSettings:
    model: str
    fallback_model: str = ""
    api_base: str = ""            # set to a LiteLLM gateway URL to route through it
    api_key: str = ""
    timeout: float = 30.0
    retries: int = 2
    max_usd: float | None = None  # stop calling once this much has been spent in one run
    max_consecutive_failures: int = 5  # then stop calling for the rest of the run (budget, auth, outage)
    temperature: float | None = 0.0  # 0 gives repeatable answers; None sends none (some models need that)
    offline: bool = False             # answer from the cache only, never call the model
    extra: dict[str, Any] = field(default_factory=dict)  # passed to every call, used by tests

    @classmethod
    def from_env(cls) -> LlmSettings | None:
        model = os.environ.get("BENCHLINE_LLM_MODEL", "")
        if not model:
            return None
        cap = os.environ.get("BENCHLINE_LLM_MAX_USD")
        return cls(
            model=model,
            fallback_model=os.environ.get("BENCHLINE_LLM_FALLBACK_MODEL", ""),
            api_base=os.environ.get("BENCHLINE_LLM_API_BASE", ""),
            api_key=os.environ.get("BENCHLINE_LLM_API_KEY", ""),
            timeout=float(os.environ.get("BENCHLINE_LLM_TIMEOUT", "30")),
            retries=int(os.environ.get("BENCHLINE_LLM_RETRIES", "2")),
            max_usd=float(cap) if cap else None,
            max_consecutive_failures=int(os.environ.get("BENCHLINE_LLM_MAX_FAILURES", "5")),
            temperature=_temperature(os.environ.get("BENCHLINE_LLM_TEMPERATURE", "0")),
        )


@dataclass(frozen=True)
class LlmResult:
    ingredient: str
    is_brand: bool
    strength: str
    form: str
    grounded: bool        # the ingredient name appears in the description itself
    reason: str           # why a person should look at it, empty if nothing to check
    cost_usd: float
    tokens: int
    cached: bool
    model: str

    @property
    def needs_review(self) -> bool:
        return bool(self.reason)


@dataclass
class LlmStats:
    calls: int = 0
    cached: int = 0
    failures: int = 0
    skipped_budget: int = 0
    skipped_circuit: int = 0
    declined: int = 0          # the model answered UNKNOWN, as asked. Not an error.
    skipped_offline: int = 0   # not in the cache, and offline mode was on
    cost_usd: float = 0.0
    tokens: int = 0
    errors: list[str] = field(default_factory=list)   # first few distinct provider errors, as received

    @property
    def handled(self) -> int:
        """Every description that reached the model layer, whatever came back. The run cap counts these."""
        return (self.calls + self.cached + self.failures + self.skipped_budget + self.skipped_circuit
                + self.declined + self.skipped_offline)


class LlmNormalizer:
    def __init__(self, settings: LlmSettings, cache: JsonlCache,
                 completion: Callable[..., Any] | None = None) -> None:
        self.settings = settings
        self.stats = LlmStats()
        self._cache = cache
        self._completion = completion or self._router_completion
        self._router: Any = None
        self._consecutive_failures = 0
        self._send_temperature = settings.temperature is not None

    def normalize(self, description: str) -> LlmResult | None:
        key = cache_key(PROMPT_VERSION, self.settings.model, description)
        if (hit := self._cache.get(key)) is not None:
            if hit.get("declined"):
                self.stats.declined += 1
                return None
            self.stats.cached += 1
            return LlmResult(**{**hit, "cached": True, "cost_usd": 0.0})
        if self.settings.offline:
            self.stats.skipped_offline += 1
            return None
        if self._consecutive_failures >= self.settings.max_consecutive_failures:
            self.stats.skipped_circuit += 1
            return None
        cap = self.settings.max_usd
        if cap is not None and self.stats.cost_usd >= cap:
            self.stats.skipped_budget += 1
            return None
        # Provider errors and unreadable answers are kept apart: some provider errors subclass ValueError.
        try:
            response = self._completion(
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": description}])
        except Exception as error:  # network, auth, budget, rate limit: the run must go on
            self._failed(description, error, "model call failed")
            return None
        if response is None:
            self._failed(description, RuntimeError("the model client returned no response"), "model call failed")
            return None
        self._consecutive_failures = 0   # the provider answered, whatever it said
        try:
            parsed = LlmParse.model_validate(parse_json(response.choices[0].message.content))
        except (ValidationError, ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            self._failed(description, error, "unusable model answer")
            return None

        cost = float((getattr(response, "_hidden_params", None) or {}).get("response_cost") or 0.0)
        tokens = int(getattr(getattr(response, "usage", None), "total_tokens", 0) or 0)
        self.stats.calls += 1
        self.stats.cost_usd += cost
        self.stats.tokens += tokens
        checked = interpret(description, parsed)
        if checked is None:
            self.stats.declined += 1
            self._cache.put(key, {"declined": True})   # asking again would cost money and say the same
            return None
        name, strength, form, grounded, reason = checked
        result = LlmResult(name, parsed.is_brand, strength, form, grounded, reason, cost, tokens, False,
                           str(getattr(response, "model", self.settings.model)))
        self._cache.put(key, asdict(result))
        return result

    def _failed(self, description: str, error: Exception, what: str) -> None:
        """Count it, keep the first few distinct messages so a person can read them, and move on."""
        self.stats.failures += 1
        if what == "model call failed":
            self._consecutive_failures += 1
        message = f"{type(error).__name__}: {str(error)[:300]}"
        if message not in self.stats.errors and len(self.stats.errors) < 5:
            self.stats.errors.append(message)
        log.warning("%s for %r: %s", what, description, type(error).__name__)
        if self._consecutive_failures == self.settings.max_consecutive_failures:
            log.error("%d model calls failed in a row; no more calls this run", self._consecutive_failures)

    def is_cached(self, description: str) -> bool:
        return self._cache.get(cache_key(PROMPT_VERSION, self.settings.model, description)) is not None

    # --- LiteLLM -----------------------------------------------------------------
    def _router_completion(self, messages: list[dict[str, str]]) -> Any:
        if self._router is None:
            self._router = self._build_router()
        options: dict[str, Any] = {"response_format": LlmParse, **self.settings.extra}
        if self._send_temperature:
            options["temperature"] = self.settings.temperature
        try:
            return self._router.completion(model=ALIAS, messages=messages, **options)
        except Exception as error:
            # Some models accept only their default temperature: drop it once and remember.
            rejected = type(error).__name__ == "UnsupportedParamsError" and "temperature" in str(error)
            if self._send_temperature and rejected:
                log.warning("%s takes only its default temperature; sending none from now on", self.settings.model)
                self._send_temperature = False
                options.pop("temperature")
                return self._router.completion(model=ALIAS, messages=messages, **options)
            raise

    def _build_router(self) -> Any:
        import litellm  # imported here: it is large, and unused when no model is configured
        from litellm.router import Router

        # litellm.drop_params stays off: with it on, a refused call can come back as None instead of an error.
        litellm.suppress_debug_info = True
        # LiteLLM logs every call at INFO, which buries the pipeline's own output.
        for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
            logging.getLogger(name).setLevel(logging.WARNING)
        s = self.settings
        gateway = {"api_base": s.api_base, "api_key": s.api_key} if s.api_base else {}
        deployments = [{"model_name": ALIAS, "litellm_params": {"model": s.model, **gateway}}]
        fallbacks: list[dict[str, list[str]]] = []
        if s.fallback_model:
            deployments.append(
                {"model_name": FALLBACK_ALIAS, "litellm_params": {"model": s.fallback_model, **gateway}})
            fallbacks = [{ALIAS: [FALLBACK_ALIAS]}]
        # With a single deployment a cooldown only turns one failure into several misleading local ones.
        return Router(model_list=deployments, num_retries=s.retries, timeout=s.timeout,
                      fallbacks=fallbacks, disable_cooldowns=not s.fallback_model)


def _temperature(raw: str) -> float | None:
    return None if raw.strip().lower() in ("", "none") else float(raw)
