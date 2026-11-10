# 0008. Static demo mode for free hosting

Status: accepted

## Context
The full system needs Kafka, PostgreSQL and three services. That is not free to run
all day. A portfolio link has to work whenever someone clicks it.

## Decision
The web app can run with `VITE_DEMO_MODE=true`. It then reads a static JSON snapshot
under `/demo`, exported from a real run by `scripts/export_demo_snapshot.py`. The
snapshot has the same shapes as the API, so the same pages and types are used. Review
actions are disabled in this mode.

## Consequences
The demo is always up on free static hosting. It is read-only and only as fresh as the
last export, and the footer says it is a snapshot.
