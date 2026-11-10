# /// script
# requires-python = ">=3.12"
# dependencies = ["fonttools>=4.50"]
# ///
"""Writes the hand-lettered README art to docs/images/art. Run: uv run docs/art/build.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scenes_a import hero, how_it_works, outbox  # noqa: E402
from scenes_b import benchmark, funnel, git_push, normalizer, run_locally, tests  # noqa: E402
from shapes import EMBER_DARK, INK, TEAL_DARK, Canvas  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "images" / "art"

BANNERS = {
    "h-look": "what it looks like",
    "h-how": "how it works",
    "h-llm": "cleaning up product names (LiteLLM)",
    "h-run": "run it on your machine",
    "h-test": "run the tests",
    "h-deploy": "where to host it for free",
    "h-honest": "be honest about the data",
    "h-layout": "what is where",
    "h-push": "push it to GitHub",
}


def banner(title: str, seed: int) -> str:
    c = Canvas(1200, 110, title, title, seed)
    c.text(40, 74, title, 66, TEAL_DARK, 700)
    c.underline(40, 92, min(len(title) * 26, 1100))
    return c.svg(border=False)


def note(name: str, text: str, color: str, seed: int, size: float = 31) -> str:
    c = Canvas(1200, 200, text, text, seed)
    end = c.paragraph(30, 48, text, 1140, size, color, 500)
    c.h = int(end - size + 30)
    return c.svg(border=False)


NOTES = {
    "n-data": ("The prices are real: weekly CMS NADAC acquisition costs. NADAC is what retail pharmacies pay on "
               "average, not what any hospital's contract says. The hospitals and their purchases are made up, "
               "generated with a fixed seed, labelled synthetic everywhere, and the database refuses a row that "
               "doesn't say so.", EMBER_DARK),
    "n-host": ("Only the static demo is free and always on. The full stack (Kafka, Postgres, three services) "
               "costs money or credits to keep running, so run it for a demo or a video and switch it off.", INK),
    "n-limits": ("Honest limits: the docker, helm and terraform files have not been run end to end, and neither has "
                 "the full live Kafka replay. Each piece is tested on its own.", EMBER_DARK),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    art = {"hero": hero(), "how-it-works": how_it_works(), "outbox": outbox(), "funnel": funnel(), "normalizer": normalizer(),
           "benchmark": benchmark(), "run-locally": run_locally(), "tests": tests(), "git-push": git_push()}
    for seed, (name, title) in enumerate(BANNERS.items(), 100):
        art[name] = banner(title, seed)
    for seed, (name, (text, color)) in enumerate(NOTES.items(), 200):
        art[name] = note(name, text, color, seed)
    for name, svg in art.items():
        (OUT / f"{name}.svg").write_text(svg)
    print(f"wrote {len(art)} files to {OUT}")


if __name__ == "__main__":
    main()
