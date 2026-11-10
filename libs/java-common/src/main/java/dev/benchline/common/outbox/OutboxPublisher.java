package dev.benchline.common.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.benchline.common.events.EventEnvelope;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Writes an event row inside the caller's transaction. A relay publishes it to
 * Kafka later, so the database write and the message can never disagree.
 */
@Component
public class OutboxPublisher {

    private final JdbcClient jdbc;
    private final ObjectMapper mapper;

    public OutboxPublisher(JdbcClient jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    @Transactional(propagation = Propagation.MANDATORY)
    public void enqueue(String aggregateId, EventEnvelope<?> event) {
        jdbc.sql("""
                INSERT INTO pricing.outbox_event (id, aggregate_id, type, payload)
                VALUES (:id, :aggregateId, :type, CAST(:payload AS jsonb))
                """)
                .param("id", event.id())
                .param("aggregateId", aggregateId)
                .param("type", event.type())
                .param("payload", toJson(event))
                .update();
    }

    private String toJson(EventEnvelope<?> event) {
        try {
            return mapper.writeValueAsString(event);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Event " + event.id() + " could not be serialized", e);
        }
    }
}
