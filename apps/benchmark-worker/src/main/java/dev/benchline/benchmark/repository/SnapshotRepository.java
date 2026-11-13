package dev.benchline.benchmark.repository;

import dev.benchline.benchmark.domain.BenchmarkWeek;
import dev.benchline.benchmark.domain.Percentiles;
import java.math.BigDecimal;
import java.util.List;
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
     * Each item's latest market price as of the week end, then exact percentiles in Java. A rate stays in
     * force until it changes, so the window only drops items with no change for a year.
     */
    public Optional<Percentiles> compute(String groupId, BenchmarkWeek week, int windowWeeks) {
        List<BigDecimal> prices = jdbc.sql("""
                SELECT DISTINCT ON (pp.item_id) pp.unit_price
                  FROM pricing.price_point pp
                  JOIN catalog.item i         ON i.id = pp.item_id
                  JOIN pricing.price_source s ON s.code = pp.source
                 WHERE i.group_id = :groupId
                   AND s.kind = 'MARKET'
                   AND pp.effective_date <= :weekEnd
                   AND pp.effective_date >  :windowStart
                 ORDER BY pp.item_id, pp.effective_date DESC
                """)
                .param("groupId", groupId)
                .param("weekEnd", week.end())
                .param("windowStart", week.end().minusWeeks(windowWeeks))
                .query(BigDecimal.class)
                .list();
        return Percentiles.of(prices);
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
