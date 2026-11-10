-- Repeatable: re-applied whenever this file changes.
CREATE OR REPLACE VIEW benchmark.v_latest_snapshot AS
SELECT DISTINCT ON (group_id)
       group_id, as_of_week, p10, p25, p50, p75, p90, n_obs, method, updated_at
  FROM benchmark.benchmark_snapshot
 ORDER BY group_id, as_of_week DESC;

-- Savings = what a facility paid above the group's p25, times quantity.
CREATE OR REPLACE VIEW benchmark.v_savings_opportunity AS
SELECT pl.facility_id,
       pl.id                                   AS purchase_line_id,
       pl.item_id,
       i.group_id,
       i.description,
       pl.unit_price                           AS paid_unit_price,
       s.p25                                   AS benchmark_p25,
       s.p50                                   AS benchmark_p50,
       s.as_of_week,
       pl.qty,
       (pl.unit_price - s.p25) * pl.qty        AS savings_amount,
       pl.source
  FROM member.purchase_line pl
  JOIN catalog.item i            ON i.id = pl.item_id
  JOIN benchmark.v_latest_snapshot s ON s.group_id = i.group_id
 WHERE pl.unit_price > s.p25;
