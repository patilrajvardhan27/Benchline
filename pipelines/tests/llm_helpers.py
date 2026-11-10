"""Shared by the LLM tests: a stand-in for a model response and a normalizer wired to it."""

import json
from pathlib import Path
from types import SimpleNamespace

from benchline_pipelines.normalize.cache import JsonlCache
from benchline_pipelines.normalize.llm import LlmNormalizer, LlmSettings

ZYPREXA = {"ingredient": "OLANZAPINE", "is_brand": True, "strength": "15 MG", "form": "TABLET"}


def fake_response(payload: dict[str, object] | str, cost: float = 0.0001, tokens: int = 120) -> SimpleNamespace:
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                           usage=SimpleNamespace(total_tokens=tokens), _hidden_params={"response_cost": cost},
                           model="fake-model")


def normalizer(tmp_path: Path, reply, **settings) -> LlmNormalizer:  # type: ignore[no-untyped-def]
    return LlmNormalizer(LlmSettings(model="fake", **settings), JsonlCache(tmp_path / "c.jsonl"),
                         completion=lambda messages: reply(messages))
