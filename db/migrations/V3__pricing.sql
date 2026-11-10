CREATE TABLE pricing.price_source (
    code text PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('MARKET', 'CONTRACT', 'SYNTHETIC'))
);

INSERT INTO pricing.price_source (code, name, kind) VALUES
    ('NADAC',          'CMS National Average Drug Acquisition Cost', 'MARKET'),
    ('FSS',            'VA Federal Supply Schedule',                 'CONTRACT'),
    ('BIG4',           'VA Big Four agencies price',                 'CONTRACT'),
    ('NC',             'VA National Contract price',                 'CONTRACT'),
    ('SYNTHETIC_DEMO', 'Generated demo data, not a real price',      'SYNTHETIC');

CREATE TABLE pricing.price_point (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id        text          NOT NULL REFERENCES catalog.item (id),
    source         text          NOT NULL REFERENCES pricing.price_source (code),
    unit_price     numeric(14,5) NOT NULL CHECK (unit_price > 0),
    pricing_unit   text          NOT NULL,
    effective_date date          NOT NULL,
    as_of_date     date          NOT NULL,
    ingested_at    timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT price_point_natural_key UNIQUE (item_id, source, effective_date)
);
