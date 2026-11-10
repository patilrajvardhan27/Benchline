# 0003. Database migrations run as a separate step

Status: accepted

## Context
Both Spring services use the same database. If each ran Flyway on startup, two
instances could race, and a rolling deploy could run a migration against pods that
still expect the old schema.

## Decision
Migrations live once in `db/migrations` and run in a dedicated step: a one-shot
`migrate` container in Docker Compose, and a Helm `pre-install,pre-upgrade` Job on
Kubernetes. The services set `spring.flyway.enabled=false`. Integration tests apply
the same files through Flyway on the test classpath.

Applied versioned migrations are never edited. Changes go in a new file.

## Consequences
One owner for the schema and no startup races. The cost is that a service cannot
bootstrap its own database in isolation, which the Compose file and Helm chart handle.
