-- Everything in this schema is generated. The checks make it impossible to
-- store a row that claims to be real.
CREATE TABLE member.facility (
    id           text PRIMARY KEY,
    name         text    NOT NULL,
    bed_band     text    NOT NULL,
    region       text    NOT NULL,
    is_synthetic boolean NOT NULL DEFAULT true CHECK (is_synthetic)
);

CREATE TABLE member.purchase_line (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    facility_id  text          NOT NULL REFERENCES member.facility (id),
    item_id      text          NOT NULL REFERENCES catalog.item (id),
    unit_price   numeric(14,5) NOT NULL CHECK (unit_price > 0),
    qty          integer       NOT NULL CHECK (qty > 0),
    purchased_on date          NOT NULL,
    source       text          NOT NULL DEFAULT 'SYNTHETIC_DEMO'
                 REFERENCES pricing.price_source (code) CHECK (source = 'SYNTHETIC_DEMO')
);
