import argparse
from pathlib import Path

import pytest

from benchline_pipelines.normalize.cli import describe, preflight, run_normalize_command, start
from benchline_pipelines.normalize.llm import LlmSettings


def test_the_banner_says_whether_calls_go_through_a_gateway() -> None:
    direct = LlmSettings(model="openai/gpt-4o-mini")
    via = LlmSettings(model="openai/benchline-normalizer", api_base="http://localhost:4000", api_key="sk-x")
    assert "directly at its provider" in describe(direct)
    assert "through the gateway at http://localhost:4000" in describe(via)


def test_a_missing_provider_key_is_caught_before_any_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert "OPENAI_API_KEY is not set" in (preflight(LlmSettings(model="openai/gpt-4o-mini")) or "")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder")
    assert preflight(LlmSettings(model="openai/gpt-4o-mini")) is None


def test_each_known_provider_looks_for_its_own_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert "ANTHROPIC_API_KEY" in (preflight(LlmSettings(model="anthropic/claude-haiku-5-5")) or "")


def test_a_gateway_without_a_key_is_caught() -> None:
    assert "BENCHLINE_LLM_API_KEY is empty" in (
        preflight(LlmSettings(model="openai/benchline-normalizer", api_base="http://localhost:4000")) or "")


def test_an_unknown_provider_prefix_is_not_second_guessed() -> None:
    assert preflight(LlmSettings(model="somenewprovider/model-1")) is None


def test_start_stops_the_run_and_says_how_to_fix_a_stale_environment(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as stop:
        start(LlmSettings(model="openai/gpt-4o-mini"))
    assert "unset BENCHLINE_LLM_API_BASE" in str(stop.value)
    assert "directly at its provider" in capsys.readouterr().out


def test_a_missing_silver_file_gets_a_clear_message_before_anything_else(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(command="normalize-eval", silver=tmp_path / "nope.parquet", llm=True)
    with pytest.raises(SystemExit) as stop:
        run_normalize_command(args, tmp_path)
    assert "does not exist yet" in str(stop.value) and "--data-dir data/full" in str(stop.value)
    assert capsys.readouterr().out == ""      # no banner, no openFDA download, nothing spent
