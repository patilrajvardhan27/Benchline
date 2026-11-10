package dev.benchline.pricing.system;

import java.time.LocalDate;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class OverviewQueries {

    private final JdbcClient jdbc;

    OverviewQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Overview load() {
        return jdbc.sql("""
                SELECT (SELECT count(*) FROM catalog.item)                       AS items,
                       (SELECT count(*) FROM catalog.item_group)                 AS groups,
                       (SELECT count(*) FROM pricing.price_point)                AS price_points,
                       (SELECT max(as_of_date) FROM pricing.price_point)         AS latest,
                       (SELECT count(*) FROM insights.price_anomaly WHERE status = 'OPEN') AS open_anomalies
                """)
                .query((rs, n) -> {
                    java.sql.Date latest = rs.getDate("latest");
                    LocalDate asOf = latest == null ? null : latest.toLocalDate();
                    return new Overview(
                            rs.getLong("items"), rs.getLong("groups"), rs.getLong("price_points"), asOf,
                            rs.getLong("open_anomalies"));
                })
                .single();
    }
}
