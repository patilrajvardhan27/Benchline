CREATE INDEX price_point_item_source_date_idx
    ON pricing.price_point (item_id, source, effective_date DESC);

-- Append-mostly by date, so a BRIN stays tiny and still helps range scans.
CREATE INDEX price_point_effective_date_brin
    ON pricing.price_point USING brin (effective_date);

CREATE INDEX price_anomaly_status_idx
    ON insights.price_anomaly (status, detected_at DESC);

CREATE INDEX purchase_line_facility_idx ON member.purchase_line (facility_id);
