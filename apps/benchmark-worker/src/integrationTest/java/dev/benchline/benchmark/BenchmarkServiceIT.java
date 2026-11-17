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
import java.util.List;
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
        assertThat(handle(event("2026-11-03"))).isTrue();

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

        assertThat(handle(event)).isTrue();
        Instant firstWrite = updatedAt();
        assertThat(handle(event)).isFalse();

        assertThat(count("benchmark.processed_event")).isEqualTo(1);
        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(1);
        assertThat(updatedAt()).isEqualTo(firstWrite);
    }

    @Test
    void eventOrderDoesNotChangeTheResult() {
        handle(event("2026-11-05"));
        handle(event("2026-11-03")); // older event arriving late
        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(1);
        assertThat(jdbc.sql("SELECT p50 FROM benchmark.benchmark_snapshot").query(BigDecimal.class).single())
                .isEqualByComparingTo("0.30");
    }

    @Test
    void laterPriceChangeMovesTheNextWeeksBenchmark() {
        handle(event("2026-11-03"));
        data.price(6, "0.9", "2026-11-10");
        handle(event("2026-11-12"));

        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(2);
        BigDecimal p50 = jdbc.sql("SELECT p50 FROM benchmark.benchmark_snapshot WHERE as_of_week = '2026-11-09'")
                .query(BigDecimal.class).single();
        assertThat(p50).isEqualByComparingTo("0.35"); // median of 0.1 0.2 0.3 0.4 0.5 0.9
    }

    @Test
    void pricesOlderThanTheWindowAreIgnored() {
        data.price(7, "99", "2024-01-02"); // more than 52 weeks before the week end
        handle(event("2026-11-03"));
        assertThat(jdbc.sql("SELECT n_obs FROM benchmark.benchmark_snapshot").query(Integer.class).single())
                .isEqualTo(5);
    }

    @Test
    void aBatchGivesTheSameSnapshotsAsHandlingEventsOneByOne() {
        data.price(6, "0.9", "2026-11-10");
        List<EventEnvelope<PricePointRecorded>> events = List.of(
                event("2026-11-03"), event("2026-11-04"), event("2026-11-12"), event("2026-11-03"), event("2026-11-13"));

        events.forEach(this::handle);
        List<String> oneByOne = snapshots();
        jdbc.sql("TRUNCATE benchmark.processed_event, benchmark.benchmark_snapshot").update();

        service.handleBatch(events);
        assertThat(snapshots()).isEqualTo(oneByOne).hasSize(2);
    }

    @Test
    void aBatchClaimsEveryEventButWritesEachGroupAndWeekOnce() {
        List<EventEnvelope<PricePointRecorded>> events = List.of(
                event("2026-11-03"), event("2026-11-04"), event("2026-11-05"), event("2026-11-06"), event("2026-11-07"));
        List<EventEnvelope<PricePointRecorded>> withRepeat = new java.util.ArrayList<>(events);
        withRepeat.add(events.get(0)); // the same event id twice in one poll

        assertThat(service.handleBatch(withRepeat)).hasSize(5);
        assertThat(count("benchmark.processed_event")).isEqualTo(5);
        assertThat(count("benchmark.benchmark_snapshot")).isEqualTo(1);
    }

    @Test
    void aRedeliveredBatchChangesNothing() {
        List<EventEnvelope<PricePointRecorded>> events = List.of(event("2026-11-03"), event("2026-11-04"));
        service.handleBatch(events);
        Instant firstWrite = updatedAt();

        assertThat(service.handleBatch(events)).isEmpty();
        assertThat(count("benchmark.processed_event")).isEqualTo(2);
        assertThat(updatedAt()).isEqualTo(firstWrite);
    }

    /** True if the event was new and changed a snapshot. */
    private boolean handle(EventEnvelope<PricePointRecorded> event) {
        return !service.handleBatch(List.of(event)).isEmpty();
    }

    private List<String> snapshots() {
        return jdbc.sql("""
                SELECT concat_ws('|', group_id, as_of_week, p10, p25, p50, p75, p90, n_obs)
                  FROM benchmark.benchmark_snapshot ORDER BY as_of_week""").query(String.class).list();
    }

    private Instant updatedAt() {
        return jdbc.sql("SELECT updated_at FROM benchmark.benchmark_snapshot").query(java.sql.Timestamp.class)
                .single().toInstant();
    }

    private long count(String table) {
        return jdbc.sql("SELECT count(*) FROM " + table).query(Long.class).single();
    }
}
