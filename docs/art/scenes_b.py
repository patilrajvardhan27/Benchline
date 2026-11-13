"""Data funnel, benchmark explainer, and the run, test and git cards."""

from __future__ import annotations

from shapes import (EMBER, EMBER_DARK, EMBER_PALE, INK, LINE, MUTED, TEAL, TEAL_DARK, TEAL_PALE, Canvas)


def funnel() -> str:
    c = Canvas(1200, 560, "What the pipeline did to the real CMS files",
               "2,936,994 rows read. 2,264,443 were weekly repeats and 207 were rejected, leaving 672,344 "
               "price changes. A 12-drug subset keeps 68,471 changes in 222 groups.", 14)
    c.text(60, 66, "real NADAC files, 2025 + 2026:  2,936,994 rows in", 40, INK, 700)
    left, total = 60, 1080
    repeats, kept, rejected = 2_264_443, 672_344, 207
    full = repeats + kept + rejected
    w_rep = total * repeats / full
    w_kept = total * kept / full
    c.rect(left, 130, w_rep, 70, "#ececec", MUTED)
    c.rect(left + w_rep, 130, w_kept, 70, TEAL_PALE, TEAL_DARK)
    c.rect(left + total - 4, 130, 6, 70, EMBER, EMBER_DARK, 2, 0.5)
    c.text(left + w_rep / 2, 176, "weekly repeats of a rate we already have", 32, MUTED, 500, "middle")
    c.text(left + w_rep + w_kept / 2, 176, "kept", 34, TEAL_DARK, 700, "middle")
    c.text(left + total, 108, "207 rejected: effective date later than its own publication date", 28, EMBER_DARK, 700, "end")
    c.arrow(left + total - 1, 114, left + total - 1, 126, EMBER_DARK, 3)
    c.arrow(left + w_rep / 2, 330, left + w_rep / 2, 214, MUTED)
    c.text(left + w_rep / 2, 366, "2,264,443 dropped", 38, MUTED, 700, "middle")
    c.paragraph(left + w_rep / 2 - 300, 400, "CMS publishes every rate every week. only the first time we see a rate is a real change.",
                600, 27, MUTED, 500, "middle")
    c.arrow(left + w_rep + w_kept / 2, 330, left + w_rep + w_kept / 2, 214, TEAL_DARK)
    c.text(left + w_rep + w_kept / 2, 366, "672,344 kept", 38, TEAL_DARK, 700, "middle")
    c.rect(60, 452, 1080, 78, "#ffffff", TEAL_DARK)
    c.text(600, 504, "demo subset of 12 common drugs:  68,471 changes · 222 groups · 3,435 NDCs", 38, INK, 700, "middle")
    return c.svg()


def benchmark() -> str:
    c = Canvas(1200, 600, "Reading a benchmark",
               "A bar from p10 to p90 with the median marked and a purchase price shown against it. "
               "Savings equal paid minus p25 times quantity.", 15)
    c.text(60, 62, "a group = every NDC with the same description.  the bar = what they cost:", 36, INK, 700)
    c.line(80, 210, 1120, 210, LINE, 8)
    c.rect(180, 192, 780, 36, TEAL_PALE, TEAL_DARK)
    c.rect(400, 192, 360, 36, TEAL, TEAL_DARK)
    c.line(580, 170, 580, 250, INK, 5)
    for x, label in ((180, "p10"), (400, "p25"), (580, "median"), (760, "p75"), (960, "p90")):
        c.text(x, 290, label, 32, MUTED, 700, "middle")
    c.line(1010, 150, 1010, 262, EMBER, 8)
    c.text(1010, 134, "what you paid", 34, EMBER_DARK, 700, "middle")
    c.text(60, 372, "(made-up numbers, just to show the idea)", 26, MUTED)
    c.rect(60, 400, 520, 150, "#ffffff", TEAL_DARK)
    c.text(80, 448, "savings opportunity", 36, TEAL_DARK, 700)
    c.paragraph(80, 490, "(price paid - p25) x quantity, only when you paid more than p25", 480, 30)
    c.rect(620, 400, 520, 150, "#ffffff", EMBER_DARK)
    c.text(640, 448, "odd price move", 36, EMBER_DARK, 700)
    c.paragraph(640, 490, "a change much bigger than this group's usual changes (score 3.5 or more) is flagged for review",
                480, 28)
    return c.svg()


def run_locally() -> str:
    c = Canvas(1200, 560, "Three ways to run Benchline", "Look at the demo, run the full stack with Docker, "
               "or run the tests.", 16)
    cols = [
        (40, "A. just look", TEAL_PALE, TEAL_DARK, ["no Docker needed", "uses the real-data snapshot", "install web packages", "start the dev server",
                                                     "open localhost:5173"]),
        (420, "B. full stack", EMBER_PALE, EMBER_DARK, ["needs Docker Desktop", "copy .env.example to .env", "docker compose up",
                                                         "load data with the pipelines", "open localhost:8088"]),
        (800, "C. run the tests", "#ffffff", INK, ["Java, Python, web", "browser tests with axe", "database tests need Postgres", "or just run verify.sh",
                                                    "see the next section"]),
    ]
    for x, title, fill, stroke, steps in cols:
        c.rect(x, 40, 360, 480, fill, stroke)
        c.text(x + 180, 100, title, 46, stroke, 700, "middle")
        y = 160
        for n, step in enumerate(steps, 1):
            c.circle(x + 40, y - 10, 18, "#ffffff", stroke, 3)
            c.text(x + 40, y - 1, str(n), 26, stroke, 700, "middle")
            y = c.paragraph(x + 72, y, step, 270, 29, INK) + 22
    return c.svg()


def tests() -> str:
    c = Canvas(1200, 680, "What was run and what passed", "Java 56, pipelines 123, ML service 22, scripts 7, dbt 28, "
               "web 58, browser 44. 338 tests, none failing. Zero accessibility violations.", 17)
    c.text(60, 70, "338 tests · 0 failing", 54, TEAL_DARK, 700)
    rows = [("Java: API, worker, shared code", "56", "unit, security, real Postgres, embedded Kafka"),
            ("Python: pipelines + normalizer + LiteLLM", "123", "real Router run offline with mock replies"),
            ("Python: ML service", "22", "2 of them need a database"),
            ("Python: snapshot + synthetic data", "7", "hand-computed percentiles"),
            ("dbt: warehouse models", "28", "unit tests + data tests on DuckDB"),
            ("Web: unit + component", "58", "every page scanned with axe"),
            ("Web: real browser", "44", "12 pages x desktop and phone")]
    y = 150
    for label, count, note in rows:
        c.check(60, y - 30, 34)
        c.text(120, y, label, 36, INK, 700)
        c.text(700, y, count, 40, TEAL_DARK, 700, "end")
        c.text(730, y, note, 28, MUTED)
        y += 64
    c.rect(60, 590, 1080, 70, EMBER_PALE, EMBER_DARK)
    c.text(600, 638, "WCAG 2.2 AA: zero violations, including colour contrast in a real browser", 34, EMBER_DARK, 700, "middle")
    return c.svg()


def git_push() -> str:
    c = Canvas(1200, 560, "Pushing to GitHub", "Check what will be committed, commit, create an empty GitHub repository, "
               "add it as a remote, and push.", 18)
    steps = [("check what goes in", "git status. no .env, no data folder, no AI files"),
             ("commit it", "git add everything, then git commit"),
             ("make an empty repo", "on github.com, no README, no license"),
             ("point at it", "git remote add origin ..."),
             ("push", "git push -u origin main")]
    y = 70
    for n, (title, body) in enumerate(steps, 1):
        c.circle(80, y - 12, 26, TEAL_PALE, TEAL_DARK, 4)
        c.text(80, y - 1, str(n), 36, TEAL_DARK, 700, "middle")
        c.text(130, y, title, 40, INK, 700)
        c.text(130, y + 38, body, 30, MUTED)
        y += 94
    c.rect(760, 60, 400, 150, EMBER_PALE, EMBER_DARK)
    c.paragraph(780, 106, "never commit a real .env. the .gitignore already blocks it, but look first.", 360, 32,
                EMBER_DARK, 700)
    return c.svg()


def normalizer() -> str:
    c = Canvas(1200, 640, "Working out what each product is",
               "Four layers, cheapest first: openFDA lookup resolves 28,966 NDCs, rules 4,658, a model through LiteLLM "
               "the remaining 2,432, and a person reviews anything flagged. Measured once on 162 answers: same drug 95%, brand names 96%, reproducible from a committed fixture.", 19)
    c.text(60, 66, "who works out what a product is?  cheapest first.", 40, INK, 700)
    w, h, gap, y = 250, 190, 40, 100
    steps = [("1. openFDA", "look the NDC up. free, authoritative", "28,966 NDCs", TEAL_PALE, TEAL_DARK),
             ("2. rules", "read the description. free, deterministic", "4,658 NDCs", TEAL_PALE, TEAL_DARK),
             ("3. LiteLLM", "a model, only for what is left: brands, store brands", "2,432 NDCs", EMBER_PALE, EMBER_DARK),
             ("4. a person", "checks every row the model flagged", "needs_review.csv", "#ffffff", INK)]
    for n, (title, body, count, fill, stroke) in enumerate(steps):
        x = 40 + n * (w + gap)
        c.box(x, y, w, h, title, body, fill, stroke, 36, 24)
        c.text(x + w / 2, y + h - 18, count, 30, stroke, 700, "middle")
        if n < 3:
            c.arrow(x + w + 3, y + h / 2, x + w + gap - 5, y + h / 2, INK)
    total, left, bar_y = 1120, 40, 330
    shares = [(28966, TEAL_PALE, TEAL_DARK), (4658, "#bfe0de", TEAL_DARK), (2432, EMBER_PALE, EMBER_DARK)]
    x = left
    for count, fill, stroke in shares:
        width = total * count / 36056
        c.rect(x, bar_y, width, 46, fill, stroke, 3, 1.2)
        x += width
    c.text(left, bar_y + 86, "all 36,056 NADAC NDCs: 80% / 13% / 7%", 30, MUTED)
    c.text(60, 450, "what keeps the model honest", 36, EMBER_DARK, 700)
    guards = ["answers UNKNOWN rather than guessing", "a strength not in the text is thrown away",
              "a brand's ingredient comes from memory, so it is flagged", "spend is capped, and every answer is cached"]
    for n, line in enumerate(guards):
        c.check(60, 478 + n * 36, 24, EMBER_DARK)
        c.text(100, 500 + n * 36, line, 29, INK)
    c.rect(700, 452, 440, 170, "#ffffff", TEAL_DARK)
    c.text(718, 492, "measured once, 162 answers", 31, TEAL_DARK, 700)
    c.paragraph(718, 530, "same drug 95%, exact 83%. brand names 96%, all still flagged. every answer is in the repo, re-scored by a test.",
                406, 27, INK)
    return c.svg()
