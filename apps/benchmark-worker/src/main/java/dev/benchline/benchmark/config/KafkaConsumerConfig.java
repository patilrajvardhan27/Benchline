package dev.benchline.benchmark.config;

import dev.benchline.benchmark.consumer.MalformedEventException;
import dev.benchline.common.events.PricePointRecorded;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.TopicPartition;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.FixedBackOff;

/**
 * Transient failures (database blip) retry three times, then the record moves
 * to "<topic>.dlq" so one bad message cannot block the partition. Unreadable
 * messages skip the retries.
 */
@Configuration(proxyBeanMethods = false)
class KafkaConsumerConfig {

    private static final String DLQ_SUFFIX = ".dlq";

    @Bean
    DefaultErrorHandler errorHandler(KafkaTemplate<Object, Object> template) {
        // Partition -1 lets the producer pick, since the DLQ has one partition and the source has three.
        DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(
                template, (record, ex) -> new TopicPartition(record.topic() + DLQ_SUFFIX, -1));
        DefaultErrorHandler handler = new DefaultErrorHandler(recoverer, new FixedBackOff(500L, 3L));
        handler.addNotRetryableExceptions(MalformedEventException.class);
        return handler;
    }

    @Bean
    NewTopic priceRecordedTopic() {
        return TopicBuilder.name(PricePointRecorded.TOPIC).partitions(3).replicas(1).build();
    }

    @Bean
    NewTopic priceRecordedDlqTopic() {
        return TopicBuilder.name(PricePointRecorded.TOPIC + DLQ_SUFFIX).partitions(1).replicas(1).build();
    }
}
