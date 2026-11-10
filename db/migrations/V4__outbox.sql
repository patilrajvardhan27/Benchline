-- Written in the same transaction as the price point, drained by the relay.
-- seq preserves insert order inside one transaction, where created_at ties.
CREATE TABLE pricing.outbox_event (
    seq          bigint GENERATED ALWAYS AS IDENTITY,
    id           uuid PRIMARY KEY,
    aggregate_id text        NOT NULL,
    type         text        NOT NULL,
    payload      jsonb       NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);

CREATE INDEX outbox_unpublished_idx ON pricing.outbox_event (seq)
    WHERE published_at IS NULL;
