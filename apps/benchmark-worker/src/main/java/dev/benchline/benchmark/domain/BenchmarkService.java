package dev.benchline.benchmark.domain;

import dev.benchline.benchmark.repository.SnapshotRepository;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.common.idempotency.IdempotentConsumer;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
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

    /**
     * Stores a whole poll's worth of events in one transaction: one commit, so one log flush, instead of one
     * per event. Each (group, week) benchmark is computed once however many events point at it, which gives
     * the same rows as handling the events one by one, because a snapshot depends only on the stored prices.
     * Returns the events that were new and changed a snapshot.
     */
    @Transactional
    public List<EventEnvelope<PricePointRecorded>> handleBatch(List<EventEnvelope<PricePointRecorded>> events) {
        List<EventEnvelope<PricePointRecorded>> fresh = events.stream().filter(this::claimed).toList();
        Set<Target> stored = new HashSet<>();
        for (Target target : fresh.stream().map(Target::of).collect(Collectors.toCollection(LinkedHashSet::new))) {
            Optional<Percentiles> result = snapshots.compute(target.groupId(), target.week(), windowWeeks);
            if (result.isPresent()) {
                snapshots.upsert(target.groupId(), target.week(), result.get(), method());
                stored.add(target);
            }
        }
        List<EventEnvelope<PricePointRecorded>> changed = fresh.stream().filter(e -> stored.contains(Target.of(e))).toList();
        Instant now = Instant.now();
        changed.forEach(e -> lag.record(Duration.between(e.time(), now)));
        return changed;
    }

    private boolean claimed(EventEnvelope<PricePointRecorded> event) {
        boolean isNew = idempotency.claim(event.id());
        if (!isNew) {
            log.debug("Skipping duplicate event {}", event.id());
        }
        return isNew;
    }

    private record Target(String groupId, BenchmarkWeek week) {
        static Target of(EventEnvelope<PricePointRecorded> event) {
            return new Target(event.data().itemGroupId(), BenchmarkWeek.containing(event.data().asOfDate()));
        }
    }

    String method() {
        return "percentile_cont/latest-per-item/" + windowWeeks + "w";
    }
}
