package dev.benchline.pricing.benchmark;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class BenchmarkQueries {

    private static final String SELECT = """
            SELECT s.group_id, g.name AS group_name, s.as_of_week, s.p10, s.p25, s.p50, s.p75, s.p90,
                   s.n_obs, s.method
              FROM benchmark.benchmark_snapshot s
              JOIN catalog.item_group g ON g.id = s.group_id
             WHERE s.group_id = :groupId
            """;

    private final JdbcClient jdbc;

    public BenchmarkQueries(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<BenchmarkView> latest(String groupId) {
        return jdbc.sql(SELECT + " ORDER BY s.as_of_week DESC LIMIT 1")
                .param("groupId", groupId)
                .query(BenchmarkQueries::map)
                .optional();
    }

    public List<BenchmarkView> history(String groupId) {
        return jdbc.sql(SELECT + " ORDER BY s.as_of_week")
                .param("groupId", groupId)
                .query(BenchmarkQueries::map)
                .list();
    }

    private static BenchmarkView map(ResultSet rs, int n) throws SQLException {
        return new BenchmarkView(
                rs.getString("group_id"),
                rs.getString("group_name"),
                rs.getDate("as_of_week").toLocalDate(),
                rs.getBigDecimal("p10"),
                rs.getBigDecimal("p25"),
                rs.getBigDecimal("p50"),
                rs.getBigDecimal("p75"),
                rs.getBigDecimal("p90"),
                rs.getInt("n_obs"),
                rs.getString("method"));
    }
}
