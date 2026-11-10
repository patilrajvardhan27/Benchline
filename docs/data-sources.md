# Data sources

| Source | Used for | License / terms | Retrieved |
|---|---|---|---|
| CMS NADAC, data.medicaid.gov (2025 and 2026 yearly files) | Weekly drug acquisition cost, the benchmark input | U.S. government public data | by `benchline_pipelines fetch` |
| IBM Plex fonts | Interface typefaces | SIL Open Font License 1.1 | npm package, served from this site |
| Caveat font | Handwriting in the README art, embedded in the SVGs | SIL Open Font License 1.1 (`docs/art/fonts/OFL.txt`) | npm package `@fontsource/caveat` |

## Honesty rules

- NADAC is what retail pharmacies pay on average. It is not a hospital's contract price.
- No public dataset gives an individual hospital's purchase prices. Facilities and purchase lines
  are synthetic: generated with a fixed seed, stored with `source = 'SYNTHETIC_DEMO'`, and labelled
  in the UI. The database constraints reject any member row that does not say so.
- Groups come from matching descriptions (ADR 0005) and are not checked for therapeutic equivalence.

## What the pipeline did on the real files

Run on the 2025 and 2026 files downloaded on 2026-11-09:

- 2,936,994 rows read.
- 207 rows rejected: effective date later than the publication date.
- 2,264,443 rows were weekly repeats of an already-seen rate and were dropped.
- 672,344 rate changes kept. A 12-drug subset keeps 68,471 changes in 222 groups and 3,435 NDCs.

## Planned, not built

VA Federal Supply Schedule prices, openFDA drug shortages and Orange Book therapeutic
equivalence codes, and hospital price transparency files. The `price_source` table already has
rows for FSS, BIG4 and NC.
