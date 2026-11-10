# 0004. JdbcClient instead of an ORM

Status: accepted

## Context
The core queries are set-based SQL: `percentile_cont`, `DISTINCT ON`, lateral joins
and `INSERT ... ON CONFLICT`. An ORM would hide them or fight them.

## Decision
Use Spring's `JdbcClient` with explicit SQL and small record types. User input is
always a bound parameter. Dynamic filters add only fixed SQL fragments, never user text.

## Consequences
SQL is visible in review and can be run by hand. There is no object graph to keep
in sync with the schema, and no lazy-loading surprises. We write row mappers by hand.
