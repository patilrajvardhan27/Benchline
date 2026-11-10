package dev.benchline.pricing.pricing;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Publishes outbox rows to Kafka in insert order. A row is marked published
 * only after the broker acknowledges it, so a crash can repeat a message but
 * never lose one. Consumers deduplicate by event id.
 */
@Component
class OutboxRelay {

    private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);
    private static final Duration SEND_TIMEOUT = Duration.ofSeconds(10);

    private final JdbcClient jdbc;
    private final KafkaTemplate<String, String> kafka;
    private final TransactionTemplate tx;
    private final int batchSize;

    OutboxRelay(
            JdbcClient jdbc,
            KafkaTemplate<String, String> kafka,
            TransactionTemplate tx,
            @Value("${benchline.outbox.batch-size:200}") int batchSize) {
        this.jdbc = jdbc;
        this.kafka = kafka;
        this.tx = tx;
        this.batchSize = batchSize;
    }

    @Scheduled(
            initialDelayString = "${benchline.outbox.initial-delay-ms:0}",
            fixedDelayString = "${benchline.outbox.poll-ms:500}")
    void drain() {
        try {
            int sent;
            do {
                Integer result = tx.execute(status -> publishBatch());
                sent = result == null ? 0 : result;
            } while (sent == batchSize);
        } catch (RuntimeException e) {
            // Broker down or slow: leave rows unpublished and try again next tick.
            log.warn("Outbox relay will retry: {}", e.getMessage());
        }
    }

    /** Publishes one locked batch. Returns how many rows were sent. */
    int publishBatch() {
        List<OutboxRow> rows = jdbc.sql("""
                SELECT id, aggregate_id, type, payload::text AS payload
                  FROM pricing.outbox_event
                 WHERE published_at IS NULL
                 ORDER BY seq
                 LIMIT :limit
                   FOR UPDATE SKIP LOCKED
                """)
                .param("limit", batchSize)
                .query((rs, n) -> new OutboxRow(
                        rs.getObject("id", java.util.UUID.class),
                        rs.getString("aggregate_id"),
                        rs.getString("type"),
                        rs.getString("payload")))
                .list();

        for (OutboxRow row : rows) {
            send(row);
            jdbc.sql("UPDATE pricing.outbox_event SET published_at = now() WHERE id = :id")
                    .param("id", row.id())
                    .update();
        }
        return rows.size();
    }

    private void send(OutboxRow row) {
        try {
            kafka.send(row.type(), row.aggregateId(), row.payload()).get(SEND_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while publishing " + row.id(), e);
        } catch (ExecutionException | TimeoutException e) {
            throw new IllegalStateException("Kafka did not acknowledge event " + row.id(), e);
        }
    }

    private record OutboxRow(java.util.UUID id, String aggregateId, String type, String payload) {}
}
