# Runs the Flyway migrations. Used by docker compose and by the Helm pre-install job.
FROM flyway/flyway:13.12.1-alpine
COPY db/migrations /flyway/sql
ENTRYPOINT ["flyway", "-connectRetries=30", "-locations=filesystem:/flyway/sql", "migrate"]
