# 0002. Bounded contexts and deployables

Status: accepted

## Context
Catalog, pricing, benchmarking and anomaly review change for different reasons.

## Decision
One PostgreSQL schema per context: `catalog`, `pricing`, `benchmark`, `member`,
`insights`. Services own the schemas they write:

| Service | Writes | Reads |
|---|---|---|
| pricing-api | catalog, pricing (including the outbox) | everything, for the read API |
| benchmark-worker | benchmark | pricing, catalog |
| ml-service | insights | pricing, catalog |

Cross-schema foreign keys point only toward `catalog`.

## Consequences
A service can be split onto its own database later without changing its contract.
Until then, cross-schema reads are plain SQL, which keeps the benchmark query simple.
