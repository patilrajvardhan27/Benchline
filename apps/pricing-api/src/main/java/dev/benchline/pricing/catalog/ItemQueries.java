package dev.benchline.pricing.catalog;

import dev.benchline.common.paging.PageMeta;
import dev.benchline.common.paging.PageParams;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Read model for the catalog. All user input is bound as a parameter. */
@Repository
public class ItemQueries {

    private static final String SELECT_ITEM = """
            SELECT i.id, i.ndc11, i.description, i.group_id, g.name AS group_name, i.otc,
                   lp.unit_price AS latest_price, lp.effective_date AS latest_effective_date
              FROM catalog.item i
              JOIN catalog.item_group g ON g.id = i.group_id
              LEFT JOIN LATERAL (
                   SELECT pp.unit_price, pp.effective_date
                     FROM pricing.price_point pp
                    WHERE pp.item_id = i.id AND pp.source = 'NADAC'
                    ORDER BY pp.effective_date DESC
                    LIMIT 1) lp ON true
            """;

    private final JdbcClient jdbc;

    public ItemQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public ItemPage search(String query, String groupId, PageParams params) {
        StringBuilder where = new StringBuilder(" WHERE 1 = 1");
        if (query != null && !query.isBlank()) {
            where.append(" AND (i.description ILIKE :pattern ESCAPE '\\' OR i.ndc11 LIKE :prefix ESCAPE '\\')");
        }
        if (groupId != null && !groupId.isBlank()) {
            where.append(" AND i.group_id = :groupId");
        }
        String filter = where.toString();

        long total = bind(jdbc.sql("SELECT count(*) FROM catalog.item i" + filter), query, groupId)
                .query(Long.class).single();

        List<ItemView> rows = bind(
                        jdbc.sql(SELECT_ITEM + filter + " ORDER BY i.description, i.ndc11 LIMIT :size OFFSET :offset"),
                        query, groupId)
                .param("size", params.size())
                .param("offset", params.offset())
                .query(ItemQueries::mapItem)
                .list();
        return new ItemPage(rows, PageMeta.of(params.page(), params.size(), total));
    }

    public Optional<ItemView> findById(String itemId) {
        return jdbc.sql(SELECT_ITEM + " WHERE i.id = :id")
                .param("id", itemId)
                .query(ItemQueries::mapItem)
                .optional();
    }

    public List<Equivalent> equivalents(String itemId) {
        return jdbc.sql("""
                WITH me AS (
                    SELECT i.group_id, lp.unit_price
                      FROM catalog.item i
                      JOIN LATERAL (SELECT unit_price FROM pricing.price_point
                                     WHERE item_id = i.id AND source = 'NADAC'
                                     ORDER BY effective_date DESC LIMIT 1) lp ON true
                     WHERE i.id = :id)
                SELECT o.id AS item_id, o.ndc11, lp.unit_price AS latest_price,
                       me.unit_price - lp.unit_price AS savings_per_unit
                  FROM me
                  JOIN catalog.item o ON o.group_id = me.group_id AND o.id <> :id
                  JOIN LATERAL (SELECT unit_price FROM pricing.price_point
                                 WHERE item_id = o.id AND source = 'NADAC'
                                 ORDER BY effective_date DESC LIMIT 1) lp ON true
                 WHERE lp.unit_price < me.unit_price
                 ORDER BY lp.unit_price, o.ndc11
                 LIMIT 20
                """)
                .param("id", itemId)
                .query((rs, n) -> new Equivalent(
                        rs.getString("item_id"),
                        rs.getString("ndc11"),
                        rs.getBigDecimal("latest_price"),
                        rs.getBigDecimal("savings_per_unit")))
                .list();
    }

    private static JdbcClient.StatementSpec bind(JdbcClient.StatementSpec spec, String query, String groupId) {
        if (query != null && !query.isBlank()) {
            String escaped = escapeLike(query.trim());
            spec = spec.param("pattern", "%" + escaped + "%").param("prefix", escaped + "%");
        }
        if (groupId != null && !groupId.isBlank()) {
            spec = spec.param("groupId", groupId);
        }
        return spec;
    }

    /** Stops % and _ typed by a user from acting as wildcards. */
    static String escapeLike(String raw) {
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private static ItemView mapItem(java.sql.ResultSet rs, int n) throws java.sql.SQLException {
        java.sql.Date date = rs.getDate("latest_effective_date");
        return new ItemView(
                rs.getString("id"),
                rs.getString("ndc11"),
                rs.getString("description"),
                rs.getString("group_id"),
                rs.getString("group_name"),
                rs.getBoolean("otc"),
                rs.getBigDecimal("latest_price"),
                date == null ? null : date.toLocalDate());
    }
}
