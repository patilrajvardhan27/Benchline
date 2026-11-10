"""Command line for the normalize and normalize-eval commands."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from benchline_pipelines.normalize.cache import JsonlCache
from benchline_pipelines.normalize.evaluate import cached_cases, hard_cases, score_llm, score_rules
from benchline_pipelines.normalize.llm import LlmNormalizer, LlmSettings
from benchline_pipelines.normalize.openfda import ensure_download, load_index
from benchline_pipelines.normalize.pipeline import run


def add_normalize_commands(sub: Any) -> None:
    norm = sub.add_parser("normalize", help="group products by ingredient, strength and form")
    norm.add_argument("--silver", type=Path, help="silver parquet; default data/silver/nadac.parquet")
    norm.add_argument("--llm", action="store_true", help="use the model in BENCHLINE_LLM_MODEL for unresolved items")
    norm.add_argument("--max-llm", type=int, help="most distinct descriptions to send to the model")
    norm.add_argument("--offline", action="store_true", help="use cached model answers only; call nothing")
    norm.add_argument("--refresh-fda", action="store_true", help="download the openFDA file again")
    probe = sub.add_parser("normalize-probe", help="send a few descriptions to the model, show what comes back")
    probe.add_argument("descriptions", nargs="+")
    probe.add_argument("--fresh", action="store_true", help="ignore and do not write the answer cache")
    ev = sub.add_parser("normalize-eval", help="measure the rules (and optionally the model) against openFDA")
    ev.add_argument("--silver", type=Path)
    ev.add_argument("--llm", action="store_true")
    ev.add_argument("--offline", action="store_true", help="score cached model answers only; needs no key")
    ev.add_argument("--export", type=Path, help="write one row per case (answer, truth, verdict) to this CSV")
    ev.add_argument("--sample", type=int, default=200, help="hard cases to ask the model about")


PROVIDER_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def describe(settings: LlmSettings) -> str:
    """One line saying where the calls will go, so a stale environment cannot hide."""
    if settings.api_base:
        return f"model {settings.model} through the gateway at {settings.api_base}"
    return f"model {settings.model} directly at its provider"


def preflight(settings: LlmSettings) -> str | None:
    """A problem to fix before spending anything, or None. Only checks what can be checked without a call."""
    if settings.api_base:
        return None if settings.api_key else "BENCHLINE_LLM_API_BASE is set but BENCHLINE_LLM_API_KEY is empty"
    variable = PROVIDER_KEYS.get(settings.model.split("/")[0])
    if variable and not os.environ.get(variable):
        return f"{variable} is not set (the model is {settings.model}, called directly)"
    return None


def start(settings: LlmSettings) -> None:
    print(describe(settings))
    problem = preflight(settings)
    if problem:
        raise SystemExit(f"Stopping before any call: {problem}. If you meant to call the provider directly, "
                         "run `unset BENCHLINE_LLM_API_BASE BENCHLINE_LLM_API_KEY` first.")


def _llm(enabled: bool, cache: Path, offline: bool = False) -> LlmNormalizer | None:
    if not enabled:
        return None
    settings = LlmSettings.from_env()
    if settings is None:
        raise SystemExit("Set BENCHLINE_LLM_MODEL (and the provider key) to use --llm. See docs/item-normalization.md")
    if offline:
        settings = replace(settings, offline=True)
        print(f"{settings.model}: offline, cached answers only")
    else:
        start(settings)
    return LlmNormalizer(settings, JsonlCache(cache))


def run_normalize_command(args: argparse.Namespace, data: Path) -> None:
    if args.command == "normalize-probe":
        probe(args, data)
        return
    silver = args.silver or data / "silver" / "nadac.parquet"
    if not silver.exists():
        raise SystemExit(
            f"{silver} does not exist yet. For the full dataset, build it first:\n"
            "  mkdir -p data/full && ln -s ../bronze data/full/bronze\n"
            "  uv run --project pipelines python -m benchline_pipelines --data-dir data/full silver")
    index = load_index(ensure_download(data / "external" / "openfda", getattr(args, "refresh_fda", False)))
    llm = _llm(args.llm or args.offline, data / "cache" / "llm.jsonl", args.offline)

    if args.command == "normalize":
        report = run(silver, index, silver.parent, llm, args.max_llm)
        print(json.dumps({"ndcs": report.ndcs, "by_method": report.by_method, "needs_review": report.needs_review,
                          "groups_before": report.groups_before, "groups_after": report.groups_after,
                          "llm": report.llm}, indent=2))
        return

    rows = pd.read_parquet(silver, columns=["ndc11", "description"]).drop_duplicates("ndc11")
    rules = score_rules(rows, index)
    print(f"rules: recognised {rules.resolved}/{rules.ndcs} ({rules.resolved / rules.ndcs:.1%}), "
          f"ingredient correct {rules.ingredient_correct / max(rules.resolved, 1):.2%}")
    print(f"rules: form agrees with openFDA on {rules.form_correct}/{rules.form_compared} "
          f"({rules.form_correct / max(rules.form_compared, 1):.1%}); brand NDCs {rules.brand_ndcs}, "
          f"rules correctly abstained on {rules.brand_abstained}")
    if llm is not None:
        cases = cached_cases(rows, index, llm) if args.offline else hard_cases(rows, index, args.sample)
        def progress(done: int, total: int) -> None:
            if done % 25 == 0 or done == total:
                print(f"  asked {done}/{total}, ${llm.stats.cost_usd:.4f} so far", flush=True)

        out = score_llm(cases, index, llm, progress)
        n = max(out.answered, 1)
        print(f"model: answered {out.answered}/{out.sampled} (declined {llm.stats.declined}, "
              f"errors {llm.stats.failures}, not cached {llm.stats.skipped_offline})")
        print(f"  match with openFDA: exact {out.ingredient_correct / n:.1%}, "
              f"same drug ignoring salt names {out.lenient_correct / n:.1%}")
        brand_rate = out.knowledge_lenient_correct / max(out.knowledge_answered, 1)
        print(f"  named in the description: {out.grounded}; from model knowledge (brands): "
              f"{out.knowledge_answered}, of which same drug {brand_rate:.1%}; "
              f"flagged for review {out.flagged_for_review}")
        print(f"  tokens {llm.stats.tokens}, cost ${llm.stats.cost_usd:.4f}, cached {llm.stats.cached}, "
              f"skipped after repeated failures {llm.stats.skipped_circuit}")
        for message in llm.stats.errors:
            print("  error as received:", message)
        for w in out.wrong_examples[:12]:
            print("  WRONG:", w)
        if args.export:
            pd.DataFrame(out.records).to_csv(args.export, index=False)
            print(f"wrote {len(out.records)} rows to {args.export}")


def probe(args: argparse.Namespace, data: Path) -> None:
    """Call the model on the given descriptions and print every answer or error as it is."""
    settings = LlmSettings.from_env()
    if settings is None:
        raise SystemExit("Set BENCHLINE_LLM_MODEL (and the provider key) first. See docs/item-normalization.md")
    start(settings)
    cache = JsonlCache(None if args.fresh else data / "cache" / "llm.jsonl")
    llm = LlmNormalizer(settings, cache)
    for number, description in enumerate(args.descriptions, 1):
        result = llm.normalize(description)
        if result is None:
            state = "skipped (too many failures in a row)" if llm.stats.skipped_circuit else "FAILED"
            print(f"{number:>2}. {description!r}: {state}")
        else:
            flag = "needs review: " + result.reason if result.needs_review else "ok"
            print(f"{number:>2}. {description!r}: {result.ingredient} | brand={result.is_brand} | "
                  f"{result.strength} | {result.form} | cost ${result.cost_usd:.6f} | "
                  f"{'cached' if result.cached else 'live'} | {flag}")
    s = llm.stats
    print(f"\ncalls {s.calls}, cached {s.cached}, failed {s.failures}, skipped after repeated failures "
          f"{s.skipped_circuit}, tokens {s.tokens}, cost ${s.cost_usd:.6f}")
    for message in s.errors:
        print("  error as received:", message)
