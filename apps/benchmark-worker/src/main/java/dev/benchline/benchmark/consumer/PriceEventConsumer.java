package dev.benchline.benchmark.consumer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.benchline.benchmark.domain.BenchmarkService;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import java.util.ArrayList;
import java.util.List;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.listener.BatchListenerFailedException;
import org.springframework.stereotype.Component;

@Component
public class PriceEventConsumer {

    private static final TypeReference<EventEnvelope<PricePointRecorded>> TYPE = new TypeReference<>() {};

    private final ObjectMapper mapper;
    private final BenchmarkService service;

    public PriceEventConsumer(ObjectMapper mapper, BenchmarkService service) {
        this.mapper = mapper;
        this.service = service;
    }

    @KafkaListener(topics = PricePointRecorded.TOPIC, batch = "true",
            groupId = "${spring.kafka.consumer.group-id:benchmark-worker}")
    public void onPriceRecorded(List<String> payloads) {
        List<EventEnvelope<PricePointRecorded>> events = new ArrayList<>(payloads.size());
        for (int i = 0; i < payloads.size(); i++) {
            try {
                events.add(parse(payloads.get(i)));
            } catch (MalformedEventException e) {
                // Store everything before the bad record first, so the error handler can commit past those and
                // send only the unreadable one to the dead-letter topic.
                store(events);
                throw new BatchListenerFailedException("Unreadable event", e, i);
            }
        }
        store(events);
    }

    private void store(List<EventEnvelope<PricePointRecorded>> events) {
        if (!events.isEmpty()) {
            service.handleBatch(events);
        }
    }

    EventEnvelope<PricePointRecorded> parse(String payload) {
        try {
            EventEnvelope<PricePointRecorded> event = mapper.readValue(payload, TYPE);
            if (event.id() == null || event.data() == null || event.data().itemGroupId() == null
                    || event.data().asOfDate() == null) {
                throw new MalformedEventException("Event is missing required fields", null);
            }
            return event;
        } catch (JsonProcessingException e) {
            throw new MalformedEventException("Event is not valid JSON for " + PricePointRecorded.TYPE, e);
        }
    }
}
