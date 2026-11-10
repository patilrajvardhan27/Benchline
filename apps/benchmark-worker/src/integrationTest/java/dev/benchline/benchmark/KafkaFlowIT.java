package dev.benchline.benchmark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.benchline.benchmark.support.PriceData;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.testsupport.PostgresTestBase;
import java.time.Duration;
import java.util.Map;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;
import org.springframework.test.context.TestPropertySource;

/** The consumer end to end: a message on the topic becomes a snapshot, a bad one becomes a DLQ record. */
@SpringBootTest(classes = BenchmarkWorkerApplication.class)
@EmbeddedKafka(partitions = 3, topics = {PricePointRecorded.TOPIC, PricePointRecorded.TOPIC + ".dlq"})
@TestPropertySource(properties = "spring.kafka.bootstrap-servers=${spring.embedded.kafka.brokers}")
class KafkaFlowIT extends PostgresTestBase {

    @Autowired KafkaTemplate<String, String> kafka;
    @Autowired JdbcClient jdbc;
    @Autowired ObjectMapper mapper;
    @Autowired EmbeddedKafkaBroker broker;

    @BeforeEach
    void seed() {
        PriceData data = new PriceData(jdbc);
        for (int i = 1; i <= 3; i++) {
            data.price(i, "0." + i, "2026-10-28");
        }
    }

    @Test
    void messageOnTheTopicBecomesASnapshot() throws Exception {
        String json = mapper.writeValueAsString(PriceData.event("2026-11-03"));

        kafka.send(PricePointRecorded.TOPIC, PriceData.GROUP, json).get();

        await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
                assertThat(jdbc.sql("SELECT count(*) FROM benchmark.benchmark_snapshot").query(Long.class).single())
                        .isEqualTo(1));
    }

    @Test
    void unreadableMessageMovesToTheDeadLetterTopic() throws Exception {
        kafka.send(PricePointRecorded.TOPIC, "bad-key", "{ this is not an event").get();

        Map<String, Object> props = KafkaTestUtils.consumerProps("dlq-" + System.nanoTime(), "true", broker);
        props.put("auto.offset.reset", "earliest");
        try (Consumer<String, String> consumer = new DefaultKafkaConsumerFactory<>(
                props, new StringDeserializer(), new StringDeserializer()).createConsumer()) {
            broker.consumeFromAnEmbeddedTopic(consumer, PricePointRecorded.TOPIC + ".dlq");
            var record = KafkaTestUtils.getSingleRecord(consumer, PricePointRecorded.TOPIC + ".dlq",
                    Duration.ofSeconds(20));
            assertThat(record.value()).isEqualTo("{ this is not an event");
        }
        assertThat(jdbc.sql("SELECT count(*) FROM benchmark.benchmark_snapshot").query(Long.class).single()).isZero();
    }
}
