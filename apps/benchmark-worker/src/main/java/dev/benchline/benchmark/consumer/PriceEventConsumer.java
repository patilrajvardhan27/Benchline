package dev.benchline.benchmark.consumer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.benchline.benchmark.domain.BenchmarkService;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import org.springframework.kafka.annotation.KafkaListener;
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

    @KafkaListener(topics = PricePointRecorded.TOPIC, groupId = "${spring.kafka.consumer.group-id:benchmark-worker}")
    public void onPriceRecorded(String payload) {
        service.handle(parse(payload));
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
