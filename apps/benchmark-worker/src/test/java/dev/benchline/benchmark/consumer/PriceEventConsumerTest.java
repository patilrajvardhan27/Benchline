package dev.benchline.benchmark.consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import dev.benchline.benchmark.domain.BenchmarkService;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.listener.BatchListenerFailedException;

class PriceEventConsumerTest {

    private final ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    private final BenchmarkService service = mock(BenchmarkService.class);
    private final PriceEventConsumer consumer = new PriceEventConsumer(mapper, service);

    private static final String VALID = """
            {"specversion":"1.0","id":"8f6b1c1e-6a0e-4d7e-9a43-2f1d2c7f0b11","source":"benchline/pricing-api",
             "type":"pricing.price-point-recorded.v1","time":"2026-11-03T14:05:00Z",
             "datacontenttype":"application/json",
             "data":{"pricePointId":"0b0a4b9e-2f5d-4a70-9d57-0d9c8f6f3a10","itemId":"ndc-00093715698",
                     "itemGroupId":"grp-atorvastatin-20mg","source":"NADAC","unitPrice":"0.03121",
                     "pricingUnit":"EA","previousUnitPrice":"0.03307",
                     "effectiveDate":"2026-10-29","asOfDate":"2026-11-03"}}
            """;

    @Test
    void parsesTheContractExample() {
        EventEnvelope<PricePointRecorded> event = consumer.parse(VALID);
        assertThat(event.data().unitPrice()).isEqualByComparingTo("0.03121");
        assertThat(event.data().itemGroupId()).isEqualTo("grp-atorvastatin-20mg");
    }

    @Test
    void invalidJsonIsMalformed() {
        assertThatThrownBy(() -> consumer.parse("not json")).isInstanceOf(MalformedEventException.class);
    }

    @Test
    void missingRequiredFieldIsMalformed() {
        String withoutGroup = VALID.replace("\"itemGroupId\":\"grp-atorvastatin-20mg\",", "");
        assertThatThrownBy(() -> consumer.parse(withoutGroup)).isInstanceOf(MalformedEventException.class);
    }

    @Test
    void aWholePollIsStoredInOneCall() {
        consumer.onPriceRecorded(List.of(VALID, VALID.replace("8f6b1c1e", "9a6b1c1e")));
        verify(service, times(1)).handleBatch(argThat(events -> events.size() == 2));
    }

    @Test
    void anUnreadableRecordStoresTheOnesBeforeItThenFailsAtItsIndex() {
        assertThatThrownBy(() -> consumer.onPriceRecorded(List.of(VALID, "not json", VALID)))
                .isInstanceOfSatisfying(BatchListenerFailedException.class, e -> assertThat(e.getIndex()).isEqualTo(1))
                .hasCauseInstanceOf(MalformedEventException.class);
        verify(service, times(1)).handleBatch(argThat(events -> events.size() == 1));
    }

    @Test
    void anUnreadableFirstRecordStoresNothing() {
        assertThatThrownBy(() -> consumer.onPriceRecorded(List.of("not json", VALID)))
                .isInstanceOf(BatchListenerFailedException.class);
        verify(service, never()).handleBatch(any());
    }
}
