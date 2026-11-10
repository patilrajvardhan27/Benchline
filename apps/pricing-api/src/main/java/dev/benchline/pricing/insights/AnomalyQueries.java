package dev.benchline.pricing.insights;

import dev.benchline.common.paging.PageParams;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class AnomalyQueries {

    private static final String SELECT = """
            SELECT a.id, a.price_point_id, a.group_id, g.name AS group_name, pp.item_id, pp.unit_price,
                   prev.unit_price AS previous_unit_price, pp.effective_date, a.score, a.method,
                   a.status, a.detected_at
              FROM insights.price_anomaly a
              JOIN catalog.item_group g ON g.id = a.group_id
              JOIN pricing.price_point pp ON pp.id = a.price_point_id
              LEFT JOIN LATERAL (
                   SELECT p2.unit_price FROM pricing.price_point p2
                    WHERE p2.item_id = pp.item_id AND p2.source = pp.source
                      AND p2.effective_date < pp.effective_date
                    ORDER BY p2.effective_date DESC LIMIT 1) prev ON true
            """;

    private final JdbcClient jdbc;

    public AnomalyQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public AnomalyPage list(AnomalyStatus status, PageParams page) {
        String filter = status == null ? "" : " WHERE a.status = :status";
        JdbcClient.StatementSpec count = jdbc.sql("SELECT count(*) FROM insights.price_anomaly a" + filter);
        JdbcClient.StatementSpec rows = jdbc.sql(
                SELECT + filter + " ORDER BY abs(a.score) DESC, a.id LIMIT :size OFFSET :offset");
        if (status != null) {
            count = count.param("status", status.name());
            rows = rows.param("status", status.name());
        }
        long total = count.query(Long.class).single();
        List<AnomalyView> content = rows.param("size", page.size())
                .param("offset", page.offset())
                .query(AnomalyQueries::map)
                .list();
        return new AnomalyPage(content, dev.benchline.common.paging.PageMeta.of(page.page(), page.size(), total));
    }

    public Optional<AnomalyView> find(UUID id) {
        return jdbc.sql(SELECT + " WHERE a.id = :id").param("id", id).query(AnomalyQueries::map).optional();
    }

    /** Returns false when no anomaly has that id. */
    public boolean review(UUID id, AnomalyStatus status, String reviewer) {
        return jdbc.sql("""
                UPDATE insights.price_anomaly
                   SET status = :status, reviewed_by = :reviewer, reviewed_at = now()
                 WHERE id = :id
                """)
                .param("status", status.name())
                .param("reviewer", reviewer)
                .param("id", id)
                .update() == 1;
    }

    private static AnomalyView map(java.sql.ResultSet rs, int n) throws java.sql.SQLException {
        return new AnomalyView(
                rs.getObject("id", UUID.class),
                rs.getObject("price_point_id", UUID.class),
                rs.getString("group_id"),
                rs.getString("group_name"),
                rs.getString("item_id"),
                rs.getBigDecimal("unit_price"),
                rs.getBigDecimal("previous_unit_price"),
                rs.getDate("effective_date").toLocalDate(),
                rs.getDouble("score"),
                rs.getString("method"),
                AnomalyStatus.valueOf(rs.getString("status")),
                rs.getTimestamp("detected_at").toInstant());
    }
}
