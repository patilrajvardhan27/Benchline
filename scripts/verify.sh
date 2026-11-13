#!/usr/bin/env bash
# Runs every check the CI pipeline runs. Integration tests need Docker, or
# TEST_DATABASE_URL pointing at a throwaway PostgreSQL (see CONTRIBUTING.md).
set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n== %s\n' "$1"; }

step "File length limit"
node scripts/check-file-length.mjs

step "Contracts"
npx --yes @redocly/cli@latest lint contracts/openapi/openapi.yaml
diff -q deploy/flagd/flags.flagd.json deploy/helm/benchline/files/flags.flagd.json

step "Java: unit and integration tests"
./gradlew --no-daemon test integrationTest

step "Python: pipelines"
(cd pipelines && uv run ruff check . && uv run mypy benchline_pipelines tests && uv run pytest -q)

step "Python: ml-service"
(cd ml-service && uv run ruff check . && uv run mypy app tests && uv run pytest -q)

step "Scripts: snapshot builder and synthetic data"
uv run --with pytest --with pandas --with pyarrow --with numpy pytest scripts/tests -q

step "Warehouse: dbt on DuckDB"
(cd warehouse && uv run python load_gold.py && uv run dbt build --project-dir dbt --profiles-dir dbt)

step "Web: types, lint, unit tests, build"
(cd web && pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build && pnpm check:bundle)

if [[ "${SKIP_E2E:-}" != "1" ]]; then
  step "Web: browser tests with accessibility scans"
  (cd web && pnpm exec playwright install chromium && pnpm exec playwright test)
fi

printf '\nAll checks passed.\n'
