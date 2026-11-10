# Contributing

## Working agreements

- Change the contract first. Edit `contracts/openapi` or `contracts/events`, then the code.
  Generated files (`web/src/shared/api/generated`) are never edited by hand.
- Source files stay under 250 lines (`node scripts/check-file-length.mjs`). Split by responsibility
  when a file passes about 200.
- Money is `BigDecimal`, `numeric(14,5)` or a decimal string. Never a float.
- Tests ship with the code. Anything touching PostgreSQL or Kafka gets an integration test.
  Every new page gets a browser test with an axe scan.
- Never edit an applied migration. Add a new one.
- Comments explain why, not what.
- Use Conventional Commits: `feat(pricing): ...`, `fix(benchmark): ...`, `docs(adr): ...`.

## Running tests

```bash
./gradlew test                       # fast Java tests
./gradlew integrationTest            # needs Docker (Testcontainers)
(cd pipelines && uv run pytest)
(cd ml-service && uv run pytest)
(cd web && pnpm test && pnpm e2e)
```

### Integration tests without Docker

Start any throwaway PostgreSQL 16 and point the tests at it. The suite migrates the schema itself
and truncates tables between tests, so never use a database you care about.

```bash
export TEST_DATABASE_URL=jdbc:postgresql://127.0.0.1:5432/benchline_test
export TEST_DATABASE_USER=postgres TEST_DATABASE_PASSWORD=...
./gradlew integrationTest
TEST_DATABASE_DSN=postgresql://postgres@127.0.0.1:5432/benchline_test uv run --project ml-service pytest
```

Kafka is embedded in the JVM for these tests, so no broker is needed.

### Browser tests with a different Chromium

If Playwright cannot find its pinned browser, set `PLAYWRIGHT_CHROMIUM_PATH` to an installed
Chromium, or run `pnpm exec playwright install chromium`.
