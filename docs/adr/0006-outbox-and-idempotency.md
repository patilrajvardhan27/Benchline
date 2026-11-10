# 0006. Transactional outbox and idempotent consumers

Status: accepted

## Context
Writing a price to the database and sending an event to Kafka are two systems. Doing
both directly can lose an event (crash between them) or send one for a rolled-back row.

## Decision
The API inserts the price and an `outbox_event` row in one transaction. A relay
publishes rows in insert order (`seq`) and marks them published only after Kafka
acknowledges. Delivery is therefore at least once. The consumer inserts the event id
into `processed_event` in the same transaction as its own write, so a repeat has no effect.

Events are keyed by product group, so one group's changes stay ordered on one partition.
Unreadable messages go to `<topic>.dlq` without retries; other failures retry three times first.

## Consequences
No lost or phantom events, at the cost of a small delay (the relay polls) and one extra table.
The worker does not publish its own events: that would bring the dual-write problem back
without a second outbox, and nothing consumes them yet.
