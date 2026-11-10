package dev.benchline.pricing.pricing;

import dev.benchline.common.errors.ApiException;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class PriceHistoryQueries {

    private static final int MAX_ROWS = 2000;

    private final JdbcClient jdbc;

    public PriceHistoryQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Oldest first, so the chart can plot the list as returned. */
    public List<PricePointView> forItem(String itemId, String source, LocalDate from, LocalDate to) {
        StringBuilder sql = new StringBuilder("""
                SELECT id, item_id, source, unit_price, pricing_unit, effective_date, as_of_date
                  FROM pricing.price_point WHERE item_id = :itemId
                """);
        if (source != null && !source.isBlank()) {
            sql.append(" AND source = :source");
        }
        if (from != null) {
            sql.append(" AND effective_date >= :from");
        }
        if (to != null) {
            sql.append(" AND effective_date <= :to");
        }
        sql.append(" ORDER BY effective_date LIMIT ").append(MAX_ROWS);

        JdbcClient.StatementSpec spec = jdbc.sql(sql.toString()).param("itemId", itemId);
        if (source != null && !source.isBlank()) {
            spec = spec.param("source", parseSource(source).name());
        }
        if (from != null) {
            spec = spec.param("from", from);
        }
        if (to != null) {
            spec = spec.param("to", to);
        }
        return spec.query((rs, n) -> new PricePointView(
                        rs.getObject("id", UUID.class),
                        rs.getString("item_id"),
                        rs.getString("source"),
                        rs.getBigDecimal("unit_price"),
                        rs.getString("pricing_unit"),
                        rs.getDate("effective_date").toLocalDate(),
                        rs.getDate("as_of_date").toLocalDate()))
                .list();
    }

    private static PriceSource parseSource(String raw) {
        try {
            return PriceSource.valueOf(raw);
        } catch (IllegalArgumentException e) {
            throw ApiException.badRequest("source must be one of NADAC, FSS, BIG4, NC, SYNTHETIC_DEMO");
        }
    }
}
