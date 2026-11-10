package dev.benchline.benchmark.repository;

import dev.benchline.benchmark.domain.BenchmarkWeek;
import dev.benchline.benchmark.domain.Percentiles;
import java.time.LocalDate;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class SnapshotRepository {

    private final JdbcClient jdbc;

    public SnapshotRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * p10 to p90 over each item's latest market price as of the week end. A rate stays in
     * force until it changes, so the window only drops items with no change for a year.
     * percentile_cont returns doubles, rounded back to the column's five places.
     */
    public Optional<Percentiles> compute(String groupId, BenchmarkWeek week, int windowWeeks) {
        LocalDate windowStart = week.end().minusWeeks(windowWeeks);
        return jdbc.sql("""
                WITH latest AS (
                    SELECT DISTINCT ON (pp.item_id) pp.unit_price
                      FROM pricing.price_point pp
                      JOIN catalog.item i         ON i.id = pp.item_id
                      JOIN pricing.price_source s ON s.code = pp.source
                     WHERE i.group_id = :groupId
                       AND s.kind = 'MARKET'
                       AND pp.effective_date <= :weekEnd
                       AND pp.effective_date >  :windowStart
                     ORDER BY pp.item_id, pp.effective_date DESC)
                SELECT round(percentile_cont(0.10) WITHIN GROUP (ORDER BY unit_price)::numeric, 5) AS p10,
                       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY unit_price)::numeric, 5) AS p25,
                       round(percentile_cont(0.50) WITHIN GROUP (ORDER BY unit_price)::numeric, 5) AS p50,
                       round(percentile_cont(0.75) WITHIN GROUP (ORDER BY unit_price)::numeric, 5) AS p75,
                       round(percentile_cont(0.90) WITHIN GROUP (ORDER BY unit_price)::numeric, 5) AS p90,
                       count(*) AS n
                  FROM latest
                """)
                .param("groupId", groupId)
                .param("weekEnd", week.end())
                .param("windowStart", windowStart)
                .query((rs, row) -> {
                    int n = rs.getInt("n");
                    if (n == 0) {
                        return null;
                    }
                    return new Percentiles(
                            rs.getBigDecimal("p10"), rs.getBigDecimal("p25"), rs.getBigDecimal("p50"),
                            rs.getBigDecimal("p75"), rs.getBigDecimal("p90"), n);
                })
                .optional();
    }

    public void upsert(String groupId, BenchmarkWeek week, Percentiles p, String method) {
        jdbc.sql("""
                INSERT INTO benchmark.benchmark_snapshot
                    (group_id, as_of_week, p10, p25, p50, p75, p90, n_obs, method)
                VALUES (:groupId, :week, :p10, :p25, :p50, :p75, :p90, :n, :method)
                ON CONFLICT (group_id, as_of_week) DO UPDATE
                   SET p10 = EXCLUDED.p10, p25 = EXCLUDED.p25, p50 = EXCLUDED.p50,
                       p75 = EXCLUDED.p75, p90 = EXCLUDED.p90, n_obs = EXCLUDED.n_obs,
                       method = EXCLUDED.method, updated_at = now()
                """)
                .param("groupId", groupId)
                .param("week", week.start())
                .param("p10", p.p10())
                .param("p25", p.p25())
                .param("p50", p.p50())
                .param("p75", p.p75())
                .param("p90", p.p90())
                .param("n", p.nObs())
                .param("method", method)
                .update();
    }
}
