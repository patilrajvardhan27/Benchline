package dev.benchline.pricing.member;

import dev.benchline.common.paging.PageParams;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class MemberQueries {

    private final JdbcClient jdbc;

    public MemberQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<Facility> facilities() {
        return jdbc.sql("SELECT id, name, bed_band, region, is_synthetic FROM member.facility ORDER BY name")
                .query(MemberQueries::mapFacility)
                .list();
    }

    public Optional<Facility> facility(String id) {
        return jdbc.sql("SELECT id, name, bed_band, region, is_synthetic FROM member.facility WHERE id = :id")
                .param("id", id)
                .query(MemberQueries::mapFacility)
                .optional();
    }

    public List<Opportunity> opportunities(String facilityId, PageParams page) {
        return jdbc.sql("""
                SELECT purchase_line_id, item_id, group_id, description, paid_unit_price, benchmark_p25,
                       benchmark_p50, qty, savings_amount, source
                  FROM benchmark.v_savings_opportunity
                 WHERE facility_id = :facilityId
                 ORDER BY savings_amount DESC, purchase_line_id
                 LIMIT :size OFFSET :offset
                """)
                .param("facilityId", facilityId)
                .param("size", page.size())
                .param("offset", page.offset())
                .query((rs, n) -> new Opportunity(
                        rs.getLong("purchase_line_id"),
                        rs.getString("item_id"),
                        rs.getString("group_id"),
                        rs.getString("description"),
                        rs.getBigDecimal("paid_unit_price"),
                        rs.getBigDecimal("benchmark_p25"),
                        rs.getBigDecimal("benchmark_p50"),
                        rs.getInt("qty"),
                        rs.getBigDecimal("savings_amount"),
                        rs.getString("source")))
                .list();
    }

    /** Returns {lineCount, totalSavings} across all pages. */
    public Totals totals(String facilityId) {
        return jdbc.sql("""
                SELECT count(*) AS n, coalesce(sum(savings_amount), 0) AS total
                  FROM benchmark.v_savings_opportunity WHERE facility_id = :facilityId
                """)
                .param("facilityId", facilityId)
                .query((rs, n) -> new Totals(rs.getLong("n"), rs.getBigDecimal("total")))
                .single();
    }

    public record Totals(long lines, BigDecimal savings) {}

    private static Facility mapFacility(java.sql.ResultSet rs, int n) throws java.sql.SQLException {
        return new Facility(
                rs.getString("id"),
                rs.getString("name"),
                rs.getString("bed_band"),
                rs.getString("region"),
                rs.getBoolean("is_synthetic"));
    }
}
