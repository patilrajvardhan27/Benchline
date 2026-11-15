"""Ask Benchline: the tool-calling loop and the stream the panel shows."""

from __future__ import annotations

from shapes import EMBER_DARK, EMBER_PALE, INK, MUTED, TEAL_DARK, TEAL_PALE, Canvas


def agent() -> str:
    c = Canvas(1200, 700, "How Ask Benchline answers a question",
               "The browser posts a question to the ML service. A loop asks the model through LiteLLM, runs the "
               "read-only tools it asks for (benchmark, anomalies, equivalents), and streams every step back over "
               "Server-Sent Events. The panel shows thinking, each tool call and its result, then the answer with "
               "links to the item pages.", 22)
    c.text(60, 62, "one question in, every step streamed back", 40, INK, 700)

    c.box(40, 110, 260, 200, "the panel", "React, Zustand store, live region for screen readers", "#ffffff", INK, 34, 24)
    c.rect(360, 100, 470, 300, TEAL_PALE, TEAL_DARK)
    c.text(595, 142, "ml-service: the loop", 32, TEAL_DARK, 700, "middle")
    c.box(380, 165, 200, 110, "model", "via LiteLLM, fallback, budget", "#ffffff", TEAL_DARK, 30, 22)
    c.box(610, 165, 200, 110, "3 tools", "read-only SQL, 3s timeout", "#ffffff", TEAL_DARK, 30, 22)
    c.arrow(582, 205, 606, 205, INK)
    c.arrow(606, 240, 582, 240, INK)
    c.text(595, 318, "at most 6 steps", 26, MUTED, 500, "middle")
    c.text(595, 356, "token checked, rate limited", 26, MUTED, 500, "middle")
    c.box(890, 110, 270, 200, "Postgres", "benchmarks, price flags, products", "#ffffff", INK, 34, 24)
    c.arrow(812, 220, 886, 220, INK)

    c.arrow(302, 150, 356, 150, INK)
    c.text(330, 136, "POST", 22, MUTED, 700, "middle")
    c.arrow(356, 290, 302, 290, EMBER_DARK)
    c.text(330, 320, "SSE", 22, EMBER_DARK, 700, "middle")

    c.rect(40, 440, 1120, 220, EMBER_PALE, EMBER_DARK)
    c.text(64, 482, "what the stream carries, in order", 30, EMBER_DARK, 700)
    events = [("thinking", "\"I'll check the benchmark\""), ("tool_call", "Benchmark for sertraline"),
              ("tool_result", "median $0.03484, 46 products"), ("answer", "with sources linked to items"),
              ("done", "steps and tokens")]
    for n, (name, note) in enumerate(events):
        x = 64 + n * 220
        c.text(x, 532, name, 28, INK, 700)
        c.paragraph(x, 568, note, 200, 22, MUTED, 500)
        if n < len(events) - 1:
            c.arrow(x + 180, 524, x + 212, 524, EMBER_DARK, 3)
    c.text(64, 640, "no done = a dropped stream: the panel says so and offers Retry", 24, EMBER_DARK, 700)
    return c.svg()
