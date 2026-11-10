package dev.benchline.pricing.pricing;

import static dev.benchline.pricing.support.Fixtures.DESCRIPTION;
import static dev.benchline.pricing.support.Fixtures.grouped;
import static dev.benchline.pricing.support.Fixtures.nadac;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.pricing.PricingApiApplication;
import dev.benchline.testsupport.PostgresTestBase;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;
import org.springframework.test.context.TestPropertySource;

@SpringBootTest(classes = PricingApiApplication.class)
@EmbeddedKafka(partitions = 3, topics = PricePointRecorded.TOPIC)
@TestPropertySource(properties = {
    "spring.kafka.bootstrap-servers=${spring.embedded.kafka.brokers}",
    "benchline.security.dev-jwt-secret=0123456789abcdef0123456789abcdef",
    "benchline.outbox.initial-delay-ms=3600000", // the tests call the relay themselves
    "benchline.outbox.poll-ms=3600000"
})
class PriceIngestIT extends PostgresTestBase {

    @Autowired PriceIngestService ingest;
    @Autowired OutboxRelay relay;
    @Autowired JdbcClient jdbc;
    @Autowired ObjectMapper mapper;
    @Autowired EmbeddedKafkaBroker broker;

    @Test
    void storesPricePointItemGroupAndOneOutboxEvent() {
        IngestReceipt receipt = ingest.ingest(List.of(nadac("00093715698", "0.03121", "2026-10-29")));

        assertThat(receipt).isEqualTo(new IngestReceipt(1, 0));
        assertThat(count("pricing.price_point")).isEqualTo(1);
        assertThat(count("catalog.item")).isEqualTo(1);
        assertThat(count("catalog.item_group")).isEqualTo(1);
        assertThat(jdbc.sql("SELECT aggregate_id FROM pricing.outbox_event").query(String.class).single())
                .isEqualTo("grp-atorvastatin-calcium-20-mg-tab");
    }

    @Test
    void sameItemSourceAndDateIsStoredOnce() {
        PricePointInput row = nadac("00093715698", "0.03121", "2026-10-29");
        ingest.ingest(List.of(row));
        IngestReceipt second = ingest.ingest(List.of(row));

        assertThat(second).isEqualTo(new IngestReceipt(0, 1));
        assertThat(count("pricing.price_point")).isEqualTo(1);
        assertThat(count("pricing.outbox_event")).isEqualTo(1);
    }

    @Test
    void eventCarriesThePreviousPrice() throws Exception {
        ingest.ingest(List.of(nadac("00093715698", "0.03307", "2026-10-22")));
        ingest.ingest(List.of(nadac("00093715698", "0.03121", "2026-10-29")));

        List<String> payloads = jdbc.sql("SELECT payload::text FROM pricing.outbox_event ORDER BY seq")
                .query(String.class).list();
        JsonNode first = mapper.readTree(payloads.get(0)).get("data");
        JsonNode second = mapper.readTree(payloads.get(1)).get("data");
        assertThat(first.has("previousUnitPrice")).isFalse();
        assertThat(new BigDecimal(second.get("previousUnitPrice").asText())).isEqualByComparingTo("0.03307");
        assertThat(second.get("unitPrice").asText()).isEqualTo("0.03121");
    }

    @Test
    void aFailedBatchStoresNothing() {
        PricePointInput good = nadac("00093715698", "0.03121", "2026-10-29");
        PricePointInput forbidden = new PricePointInput(
                "00093715699", DESCRIPTION, false, PriceSource.SYNTHETIC_DEMO, new BigDecimal("1"), "EA",
                good.effectiveDate(), good.asOfDate(), null);

        assertThatThrownBy(() -> ingest.ingest(List.of(good, forbidden)))
                .hasMessageContaining("SYNTHETIC_DEMO");
        assertThat(count("pricing.price_point")).isZero();
        assertThat(count("pricing.outbox_event")).isZero();
    }

    @Test
    void relayPublishesInOrderAndMarksRowsPublished() throws Exception {
        ingest.ingest(List.of(
                nadac("00093715698", "0.03307", "2026-10-22"),
                nadac("00093715698", "0.03121", "2026-10-29")));

        relay.drain();

        assertThat(jdbc.sql("SELECT count(*) FROM pricing.outbox_event WHERE published_at IS NULL")
                .query(Long.class).single()).isZero();

        Map<String, Object> props = KafkaTestUtils.consumerProps("it-" + System.nanoTime(), "true", broker);
        props.put("auto.offset.reset", "earliest");
        try (Consumer<String, String> consumer = new DefaultKafkaConsumerFactory<>(
                props, new StringDeserializer(), new StringDeserializer()).createConsumer()) {
            broker.consumeFromAnEmbeddedTopic(consumer, PricePointRecorded.TOPIC);
            List<String> sentIds = jdbc.sql("SELECT id::text FROM pricing.outbox_event ORDER BY seq")
                    .query(String.class).list();
            List<ConsumerRecord<String, String>> records = new java.util.ArrayList<>();
            KafkaTestUtils.getRecords(consumer, Duration.ofSeconds(10), 2).forEach(records::add);
            // Keep only this test's events; the embedded broker is shared by the whole class.
            records.removeIf(r -> sentIds.stream().noneMatch(id -> r.value().contains(id)));

            assertThat(records).hasSize(2);
            assertThat(records).allSatisfy(r -> assertThat(r.key()).isEqualTo("grp-atorvastatin-calcium-20-mg-tab"));
            // Same key means same partition, so the broker preserves the order we sent.
            assertThat(records.get(0).value()).contains(sentIds.get(0)).contains("0.03307");
            assertThat(records.get(1).value()).contains(sentIds.get(1)).contains("0.03121");
        }
    }

    @Test
    void productsSharingANormalizedNameAreBenchmarkedTogether() {
        ingest.ingest(List.of(
                grouped("00000000001", "ALLERGY 25 MG TABLET", "0.05", "2026-10-29", "DIPHENHYDRAMINE 25 MG TABLET"),
                grouped("00000000002", "ALLER-G-TIME 25 MG CAPLET", "0.04", "2026-10-29", "DIPHENHYDRAMINE 25 MG TABLET")));

        assertThat(count("catalog.item_group")).isEqualTo(1);
        assertThat(jdbc.sql("SELECT DISTINCT group_id FROM catalog.item").query(String.class).single())
                .isEqualTo("grp-diphenhydramine-25-mg-tablet");
        // the raw description is still kept on the item
        assertThat(jdbc.sql("SELECT description FROM catalog.item WHERE id = 'ndc-00000000001'")
                .query(String.class).single()).isEqualTo("ALLERGY 25 MG TABLET");
    }

    @Test
    void withoutAGroupNameTheDescriptionStillDecidesTheGroup() {
        ingest.ingest(List.of(
                grouped("00000000001", "ALLERGY 25 MG TABLET", "0.05", "2026-10-29", null),
                grouped("00000000002", "ALLER-G-TIME 25 MG CAPLET", "0.04", "2026-10-29", "  ")));
        assertThat(count("catalog.item_group")).isEqualTo(2);
    }

    @Test
    void drainingAnEmptyOutboxIsANoop() {
        relay.drain();
        assertThat(count("pricing.outbox_event")).isZero();
    }

    private long count(String table) {
        return jdbc.sql("SELECT count(*) FROM " + table).query(Long.class).single();
    }
}
