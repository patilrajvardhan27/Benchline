CREATE TABLE insights.price_anomaly (
    id             uuid PRIMARY KEY,
    price_point_id uuid          NOT NULL REFERENCES pricing.price_point (id),
    group_id       text          NOT NULL REFERENCES catalog.item_group (id),
    score          numeric(10,3) NOT NULL,
    method         text          NOT NULL,
    status         text          NOT NULL DEFAULT 'OPEN'
                   CHECK (status IN ('OPEN', 'CONFIRMED', 'DISMISSED')),
    detected_at    timestamptz   NOT NULL DEFAULT now(),
    reviewed_by    text,
    reviewed_at    timestamptz,
    CONSTRAINT anomaly_once_per_method UNIQUE (price_point_id, method)
);
