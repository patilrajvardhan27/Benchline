package dev.benchline.common.events;

import java.time.Instant;
import java.util.UUID;

/** CloudEvents 1.0 structured-mode envelope. Matches contracts/events/*.json. */
public record EventEnvelope<T>(
        String specversion,
        UUID id,
        String source,
        String type,
        Instant time,
        String datacontenttype,
        T data) {

    public static <T> EventEnvelope<T> of(String source, String type, T data) {
        return new EventEnvelope<>("1.0", UUID.randomUUID(), source, type, Instant.now(), "application/json", data);
    }
}
