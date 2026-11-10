package dev.benchline.benchmark;

import static dev.benchline.benchmark.support.PriceData.GROUP;
import static dev.benchline.benchmark.support.PriceData.event;
import static org.assertj.core.api.Assertions.assertThat;

import dev.benchline.benchmark.domain.BenchmarkService;
import dev.benchline.benchmark.support.PriceData;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.testsupport.PostgresTestBase;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.TestPropertySource;

@SpringBootTest(classes = BenchmarkWorkerApplication.class)
@EmbeddedKafka(partitions = 3)
@TestPropertySource(properties = {
    "spring.kafka.bootstrap-servers=${spring.embedded.kafka.brokers}",
    "spring.kafka.listener.auto-startup=false" // these tests call the service directly
})
class BenchmarkServiceIT extends PostgresTestBase {

    @Autowired BenchmarkService service;
    @Autowired JdbcClient jdbc;
    PriceData data;

    @BeforeEach
    void seed() {
        data = new PriceData(jdbc);
        // Five items priced 0.1 to 0.5. Hand-computed linear-interpolation percentiles:
        // p10 = 0.14, p25 = 0.20, p50 = 0.30, p75 = 0.40, p90 = 0.46
        for (int i = 1; i <= 5; i++) {
            data.price(i, "0." + i, "2026-10-28");
        }
    }

    @Test
    void percentilesMatchHandComputedValues() {
        assertThat(service.handle(event("2026-11-03"))).isTrue();

        Map<String, Object> row = jdbc.sql("SELECT * FROM benchmark.benchmark_snapshot WHERE group_id = :g")
                .param("g", GROUP).query().singleRow();
        assertThat((BigDecimal) row.get("p10")).isEqualByComparingTo("0.14");
        assertThat((BigDecimal) row.get("p25")).isEqualByComparingTo("0.20");
        assertThat((BigDecimal) row.get("p50")).isEqualByComparingTo("0.30");
        assertThat((BigDecimal) row.get("p75")).isEqualByComparingTo("0.40");
        assertThat((BigDecimal) row.get("p90")).isEqualByComparingTo("0.46");
        assertThat(row.get("n_obs")).isEqualTo(5);
        assertThat(row.get("as_of_week").toString()).isEqualTo("2026-11-02");
    }

    @Test
    void replayingTheSameEventWritesOnce() {
        EventEnvelope<PricePointRecorded> event = event("2026-11-03");

        assertThat(service.handle(event)).isTrue();
        Instant firstWrite = updatedAt();
        assertThat(service.handle(event)).isFalse();

        assertThat(count("benchmark.processed_event")).isEqualTo(1);
        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(1);
        assertThat(updatedAt()).isEqualTo(firstWrite);
    }

    @Test
    void eventOrderDoesNotChangeTheResult() {
        service.handle(event("2026-11-05"));
        service.handle(event("2026-11-03")); // older event arriving late
        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(1);
        assertThat(jdbc.sql("SELECT p50 FROM benchmark.benchmark_snapshot").query(BigDecimal.class).single())
                .isEqualByComparingTo("0.30");
    }

    @Test
    void laterPriceChangeMovesTheNextWeeksBenchmark() {
        service.handle(event("2026-11-03"));
        data.price(6, "0.9", "2026-11-10");
        service.handle(event("2026-11-12"));

        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(2);
        BigDecimal p50 = jdbc.sql("SELECT p50 FROM benchmark.benchmark_snapshot WHERE as_of_week = '2026-11-09'")
                .query(BigDecimal.class).single();
        assertThat(p50).isEqualByComparingTo("0.35"); // median of 0.1 0.2 0.3 0.4 0.5 0.9
    }

    @Test
    void pricesOlderThanTheWindowAreIgnored() {
        data.price(7, "99", "2024-01-02"); // more than 52 weeks before the week end
        service.handle(event("2026-11-03"));
        assertThat(jdbc.sql("SELECT n_obs FROM benchmark.benchmark_snapshot").query(Integer.class).single())
                .isEqualTo(5);
    }

    private Instant updatedAt() {
        return jdbc.sql("SELECT updated_at FROM benchmark.benchmark_snapshot").query(java.sql.Timestamp.class)
                .single().toInstant();
    }

    private long count(String table) {
        return jdbc.sql("SELECT count(*) FROM " + table).query(Long.class).single();
    }
}
