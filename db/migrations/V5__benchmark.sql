CREATE TABLE benchmark.benchmark_snapshot (
    group_id    text          NOT NULL REFERENCES catalog.item_group (id),
    as_of_week  date          NOT NULL,
    p10         numeric(14,5) NOT NULL,
    p25         numeric(14,5) NOT NULL,
    p50         numeric(14,5) NOT NULL,
    p75         numeric(14,5) NOT NULL,
    p90         numeric(14,5) NOT NULL,
    n_obs       integer       NOT NULL CHECK (n_obs > 0),
    method      text          NOT NULL,
    updated_at  timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, as_of_week)
);

-- Consumers insert the event id first; a conflict means it was already handled.
CREATE TABLE benchmark.processed_event (
    event_id     uuid PRIMARY KEY,
    processed_at timestamptz NOT NULL DEFAULT now()
);
