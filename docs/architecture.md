# Architecture

```
pipelines (Python)   bronze: raw NADAC files, never edited, in MinIO (S3 API) with a SHA-256 each
        |            silver: typed, NDC-11, validated, first publication of each rate
        |            gold:   POST /api/v1/price-points:batch, one publication week at a time
        v
pricing-api (Spring Boot) --- one transaction ---> pricing.price_point + pricing.outbox_event
        |  outbox relay (in insert order, after broker ack)
        v
Kafka  pricing.price-point-recorded.v1   key = itemGroupId, 3 partitions   (.dlq for bad messages)
        |                         |                          :  reads offsets only
        v                         v                          v
benchmark-worker            ml-service                 lag-monitor (Go)
 claim event id              robust z-score on          committed vs end offset
 recompute p10..p90          log price change           per group and partition
 benchmark.benchmark_snapshot insights.price_anomaly    /lag JSON, /metrics
        \                         /
         +---- PostgreSQL 16 ----+
                    ^
web (React) --REST--> pricing-api      flagd (OpenFeature) --> pricing-api
            --SSE---> ml-service /api/v1/agent/runs  (agent: model via LiteLLM + 3 read-only tools)
```

Contracts are in `contracts/openapi` (split by path and schema) and `contracts/events`. TypeScript
types for the web app are generated from the OpenAPI file; the Java controllers are written by hand
and checked by tests against the same behaviour.

The optional item-normalization step (openFDA lookup, rules, then an LLM through LiteLLM) sits between
the silver and gold layers and is described in [item-normalization.md](item-normalization.md).

## Where things live

| Path | What |
|---|---|
| `apps/pricing-api` | REST API, write path, outbox relay |
| `apps/benchmark-worker` | Kafka consumer that computes benchmarks |
| `apps/lag-monitor` | Go service: how far each consumer group is behind, as JSON and Prometheus metrics |
| `libs/java-common` | Problem+json errors, event envelope, outbox, paging, money, flags, idempotency |
| `libs/test-support` | Shared PostgreSQL base class for integration tests |
| `ml-service` | FastAPI app: the anomaly consumer, and the Ask Benchline agent (`app/agent`) |
| `pipelines` | Download (to MinIO or a folder), clean and replay NADAC data |
| `warehouse` | Loader and dbt models for DuckDB and Snowflake |
| `web` | React and TypeScript app |
| `db/migrations` | Flyway SQL, the single source of schema |
| `deploy` | Dockerfiles, Helm chart, Terraform, flag and collector config |

## Observability

The OpenTelemetry Java agent is baked into the Spring images and switched on with
`JAVA_TOOL_OPTIONS=-javaagent:/otel/agent.jar`. The worker records a `benchline.benchmark.lag`
timer, from event creation to stored benchmark. The Go `lag-monitor` reports how many events each
consumer group has not processed yet (`benchline_consumer_lag_total`), so a stalled worker shows up
as a rising number. Compose profile `observability` adds a collector and Grafana.

The agent panel's design, event contract and failure handling: [design/agent-panel.md](design/agent-panel.md).
