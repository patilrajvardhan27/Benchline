#!/usr/bin/env bash
# Fresh local stack for a load test, in its own compose project so a normal `docker compose up` is untouched.
#   scripts/loadtest/stack.sh up 12            # new empty stack, 12 partitions, no workers yet
#   scripts/loadtest/stack.sh workers 4 3      # start 4 worker replicas with 3 consumer threads each
#   scripts/loadtest/stack.sh down
# Needs POSTGRES_PASSWORD and DEV_JWT_SECRET in the environment (from .env).
set -euo pipefail
cd "$(dirname "$0")/../.."

export MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-loadtest-only}
export LAG_INTERVAL=${LAG_INTERVAL:-1s}
dc() { docker compose -p "${LOAD_PROJECT:-benchline-load}" "$@"; }

case "${1:-}" in
  up)
    export KAFKA_PARTITIONS=${2:-3}
    dc down -v >/dev/null 2>&1 || true
    dc up -d postgres migrate kafka flagd pricing-api lag-monitor >/dev/null
    for _ in $(seq 1 90); do curl -sf http://127.0.0.1:8080/actuator/health/readiness >/dev/null && break; sleep 2; done
    curl -sf http://127.0.0.1:8080/actuator/health/readiness >/dev/null || { echo "API did not become ready" >&2; exit 1; }
    ;;
  workers)
    export KAFKA_PARTITIONS=${KAFKA_PARTITIONS:-3} WORKER_CONCURRENCY=${3:-3}
    dc up -d --scale benchmark-worker="${2:-1}" benchmark-worker >/dev/null
    ;;
  down) dc down -v ;;
  *) sed -n 2,7p "$0"; exit 2 ;;
esac
