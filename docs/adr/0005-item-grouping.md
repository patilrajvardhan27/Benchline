# 0005. Grouping products by normalized description

Status: accepted. Optionally replaced by a normalized group map, see [0010](0010-item-normalization.md).

## Context
NADAC rows carry an NDC, a description, a price and dates. They have no ingredient,
strength or dosage form columns, so a clinical grouping cannot be built from NADAC alone.

## Decision
Products that share a normalized description (trimmed, single spaces, upper case)
form one group, for example `ATORVASTATIN CALCIUM 20 MG TAB`. The group id is a slug
of that text.

## Consequences
Groups are accurate for what NADAC states, and cheap to compute. They are not proof
of therapeutic equivalence, and the UI says so. A later change can enrich groups from
the openFDA NDC directory and Orange Book codes without changing the API.
