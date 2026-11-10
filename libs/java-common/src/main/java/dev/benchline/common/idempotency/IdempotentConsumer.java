package dev.benchline.common.idempotency;

import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Kafka delivers at least once. A consumer calls claim() as the first step of
 * its transaction; a false result means the event was already handled.
 */
@Component
public class IdempotentConsumer {

    private final JdbcClient jdbc;

    public IdempotentConsumer(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional(propagation = Propagation.MANDATORY)
    public boolean claim(UUID eventId) {
        int rows = jdbc.sql("""
                INSERT INTO benchmark.processed_event (event_id) VALUES (:id)
                ON CONFLICT (event_id) DO NOTHING
                """)
                .param("id", eventId)
                .update();
        return rows == 1;
    }
}
