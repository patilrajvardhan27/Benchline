"""Hero, pipeline flow and event-safety diagrams."""

from __future__ import annotations

from shapes import (EMBER, EMBER_DARK, EMBER_PALE, FONT, INK, MUTED, TEAL, TEAL_DARK, TEAL_PALE, Canvas)


def hero() -> str:
    c = Canvas(1200, 330, "Benchline", "Benchline: what should this drug cost? Real CMS prices, synthetic hospitals.", 11)
    c.text(70, 150, "bench", 150, INK, 700)
    c.text(70 + FONT.width("bench", 150, 700) + 4, 150, "line", 150, TEAL, 700)
    c.text(72, 232, "what should this drug cost?", 62, INK, 500)
    c.underline(72, 252, 560)
    c.paragraph(72, 296, "real CMS prices · pretend hospitals (synthetic) · independent portfolio project", 1000, 30, MUTED)
    # a little bar: the idea of the whole product
    c.line(790, 150, 1130, 150, "#d9d6cf", 7)
    c.rect(830, 135, 270, 30, TEAL_PALE, TEAL_DARK, 3)
    c.rect(900, 135, 120, 30, TEAL, TEAL_DARK, 3)
    c.line(1085, 100, 1085, 200, EMBER, 7)
    c.text(1085, 86, "your price", 30, EMBER_DARK, 700, "middle")
    c.text(830, 205, "p10", 28, MUTED, 500, "middle")
    c.text(960, 205, "median", 28, MUTED, 500, "middle")
    c.text(1100, 232, "p90", 28, MUTED, 500, "middle")
    return c.svg()


def how_it_works() -> str:
    c = Canvas(1200, 600, "How a price change becomes a benchmark",
               "Pipelines send changes to the pricing API, which writes them to Kafka. The worker recomputes "
               "benchmarks into PostgreSQL and the dashboard reads them. The ML service flags odd moves.", 12)
    w, h = 320, 150
    xs = [60, 440, 820]
    top, bottom = 50, 330
    c.box(xs[0], top, w, h, "1. Pipelines", "download CMS files, clean them, keep only price changes")
    c.box(xs[1], top, w, h, "2. Pricing API", "saves the price and its event together")
    c.box(xs[2], top, w, h, "3. Kafka", "one ordered stream per product group", EMBER_PALE, EMBER_DARK)
    c.box(xs[2], bottom, w, h, "4. Worker", "claims the event, recomputes p10 to p90")
    c.box(xs[1], bottom, w, h, "5. PostgreSQL", "prices, benchmarks, flagged moves")
    c.box(xs[0], bottom, w, h, "6. Dashboard", "search, history, savings, review", "#ffffff", INK)
    c.arrow(xs[0] + w + 4, top + 75, xs[1] - 8, top + 75, TEAL_DARK)
    c.arrow(xs[1] + w + 4, top + 75, xs[2] - 8, top + 75, TEAL_DARK)
    c.arrow(xs[2] + w / 2, top + h + 4, xs[2] + w / 2, bottom - 10, EMBER_DARK)
    c.arrow(xs[2] - 4, bottom + 75, xs[1] + w + 12, bottom + 75, TEAL_DARK)
    c.arrow(xs[1] - 4, bottom + 75, xs[0] + w + 12, bottom + 75, TEAL_DARK)
    c.paragraph(60, 548, "also listening to Kafka: the ML service scores every price move and flags the odd ones "
                "for a person to confirm or dismiss", 1080, 29, EMBER_DARK, 500)
    return c.svg()


def outbox() -> str:
    c = Canvas(1200, 640, "Never lose an event, never count one twice",
               "The API saves the price and an outbox row in one transaction. A relay publishes it to Kafka after "
               "the broker confirms. The worker records each event id, so a repeat does nothing.", 13)
    c.text(60, 70, "saving to a database and telling Kafka are two different systems...", 38, INK, 700)
    c.text(60, 112, "so we never do both directly. we do this:", 32, MUTED)
    y, w, h, gap = 150, 188, 190, 38
    steps = [("API", "gets a new price", "#ffffff", INK),
             ("one transaction", "price row + outbox row. both or neither", TEAL_PALE, TEAL_DARK),
             ("relay", "sends rows in order, marks them sent after Kafka says ok", EMBER_PALE, EMBER_DARK),
             ("Kafka", "key = product group, so a group stays in order", EMBER_PALE, EMBER_DARK),
             ("worker", "writes the event id and the benchmark together", TEAL_PALE, TEAL_DARK)]
    left = (1200 - (5 * w + 4 * gap)) / 2
    for n, (title, body, fill, stroke) in enumerate(steps):
        x = left + n * (w + gap)
        c.box(x, y, w, h, title, body, fill, stroke, 31 if len(title) > 8 else 34, 24)
        if n < len(steps) - 1:
            c.arrow(x + w + 3, y + h / 2, x + w + gap - 5, y + h / 2, INK)
    c.rect(60, 380, 520, 190, "#ffffff", EMBER_DARK)
    c.text(80, 428, "crash before it was sent?", 36, EMBER_DARK, 700)
    c.paragraph(80, 470, "the row is still marked unsent, so the relay sends it when it comes back. nothing lost.",
                480, 29)
    c.rect(620, 380, 520, 190, "#ffffff", TEAL_DARK)
    c.text(640, 428, "sent twice?", 36, TEAL_DARK, 700)
    c.paragraph(640, 470, "the worker has already recorded that event id, so the second copy does nothing. "
                "nothing counted twice.", 480, 29)
    c.paragraph(60, 612, "bad message that can't be read? it goes to a dead-letter topic instead of blocking the line.",
                1080, 28, MUTED)
    return c.svg()
