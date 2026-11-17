#!/usr/bin/env bash
# Consumer scaling. One backlog per partition count, drained again for each replica count.
#   scripts/loadtest/scaling.sh 3:1,4 12:1,2,4         # partitions:replicas,replicas,...
# Needs POSTGRES_PASSWORD and DEV_JWT_SECRET in the environment. Results go to docs/perf/.
set -euo pipefail
cd "$(dirname "$0")/../.."

SINCE=${SINCE:-2025-09-01}
THREADS=${THREADS:-3}                       # consumer threads per replica
PREFIX=${PREFIX:-}
run() { uv run --quiet --project pipelines --with "psycopg[binary]" python "$@"; }

for spec in "$@"; do
  partitions=${spec%%:*}; replica_list=${spec##*:}
  export KAFKA_PARTITIONS=$partitions
  echo "== ${partitions} partitions: loading the backlog"
  scripts/loadtest/stack.sh up "$partitions" >/dev/null 2>&1
  load=$(run scripts/loadtest/measure.py --silver data/loadtest/silver/nadac.parquet --since "$SINCE" \
    --concurrency "${CONCURRENCY:-4}" --load-only --label "${PREFIX}load-p${partitions}" --out docs/perf | tail -n +1)
  events=$(echo "$load" | python3 -c 'import json,sys; print(json.load(sys.stdin)["events"])')
  echo "$load" | grep -E '"(events|ingest_eps|publish_eps|publish_lag_after_ingest_s)"'
  IFS=, read -ra replicas <<< "$replica_list"
  for r in "${replicas[@]}"; do
    run scripts/loadtest/drain.py --replicas "$r" --threads "$THREADS" --events "$events" --label "${PREFIX}p${partitions}-w${r}" \
      | sed 's/^/  /'
  done
done
