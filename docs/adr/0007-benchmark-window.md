# 0007. Benchmark window and weekly snapshots

Status: accepted

## Context
CMS republishes every NADAC rate each week with its original effective date. The
pipeline keeps only the first publication of each rate, so the stored data is a
stream of price changes. A rate stays in force until it changes.

## Decision
A group's benchmark for a week uses each product's latest market price as of the end
of that week, within 52 weeks. The snapshot is keyed by the Monday of that week, and
computed from the week end rather than the event date, so event arrival order does not
change the result. Percentiles use `percentile_cont` (linear interpolation) and are
rounded to five places.

## Consequences
Products with no change for a year drop out, which keeps discontinued items from
skewing a group. A very short window would drop products that simply did not change.
