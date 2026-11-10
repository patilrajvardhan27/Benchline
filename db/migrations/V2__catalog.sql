-- A group is a set of NDCs sold under the same normalized product description,
-- for example "ATORVASTATIN CALCIUM 20 MG TAB". See docs/adr/0005-item-grouping.md.
CREATE TABLE catalog.item_group (
    id          text PRIMARY KEY,
    name        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE catalog.item (
    id          text PRIMARY KEY,
    ndc11       char(11)    NOT NULL UNIQUE,
    description text        NOT NULL,
    group_id    text        NOT NULL REFERENCES catalog.item_group (id),
    otc         boolean     NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT item_ndc11_format CHECK (ndc11 ~ '^[0-9]{11}$'),
    CONSTRAINT item_id_matches_ndc CHECK (id = 'ndc-' || ndc11)
);

CREATE INDEX item_group_idx ON catalog.item (group_id);
