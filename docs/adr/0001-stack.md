# 0001. Technology stack

Status: accepted

## Context
Benchline is an event-driven price benchmarking service. It needs a typed API, a
reliable message path, a relational store with percentile functions, a browser UI,
and a way to run the same thing locally and in a cluster.

## Decision
- Java 21 and Spring Boot 3.5 for the API and the Kafka consumer.
- PostgreSQL 16 for storage. `percentile_cont` computes the benchmarks.
- Apache Kafka for events, with the transactional outbox pattern on the write side.
- Python 3.12 for data pipelines and the anomaly service (FastAPI, pandas).
- React 19, TypeScript and Vite for the web app, with TanStack Query.
- Docker images, Helm for deployment, Terraform for Azure, GitHub Actions for CI.

## Consequences
Two languages on the back end, chosen because each fits its job: JVM for the
transactional services, Python for data work. Contracts in `contracts/` keep the
services honest about their boundaries.
