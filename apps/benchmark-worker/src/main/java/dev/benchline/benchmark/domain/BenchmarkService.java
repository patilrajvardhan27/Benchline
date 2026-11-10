package dev.benchline.benchmark.domain;

import dev.benchline.benchmark.repository.SnapshotRepository;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.common.idempotency.IdempotentConsumer;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Recomputes a group's benchmark when one of its prices changes. Claiming the
 * event id and writing the snapshot share one transaction, so a redelivered
 * event either already finished or rolls back with nothing half-written.
 */
@Service
public class BenchmarkService {

    private static final Logger log = LoggerFactory.getLogger(BenchmarkService.class);

    private final IdempotentConsumer idempotency;
    private final SnapshotRepository snapshots;
    private final int windowWeeks;
    private final Timer lag;

    public BenchmarkService(
            IdempotentConsumer idempotency,
            SnapshotRepository snapshots,
            MeterRegistry meters,
            @Value("${benchline.benchmark.window-weeks:52}") int windowWeeks) {
        this.idempotency = idempotency;
        this.snapshots = snapshots;
        this.windowWeeks = windowWeeks;
        this.lag = Timer.builder("benchline.benchmark.lag")
                .description("Time from the price event being created to its benchmark being stored")
                .publishPercentileHistogram()
                .register(meters);
    }

    /** Returns true if the event changed a snapshot, false if it was a duplicate or had no data. */
    @Transactional
    public boolean handle(EventEnvelope<PricePointRecorded> event) {
        if (!idempotency.claim(event.id())) {
            log.debug("Skipping duplicate event {}", event.id());
            return false;
        }
        PricePointRecorded price = event.data();
        BenchmarkWeek week = BenchmarkWeek.containing(price.asOfDate());
        Optional<Percentiles> result = snapshots.compute(price.itemGroupId(), week, windowWeeks);
        if (result.isEmpty()) {
            return false;
        }
        snapshots.upsert(price.itemGroupId(), week, result.get(), method());
        lag.record(Duration.between(event.time(), Instant.now()));
        return true;
    }

    String method() {
        return "percentile_cont/latest-per-item/" + windowWeeks + "w";
    }
}
