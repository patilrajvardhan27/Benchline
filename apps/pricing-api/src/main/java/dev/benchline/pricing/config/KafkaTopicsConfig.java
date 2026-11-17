package dev.benchline.pricing.config;

import dev.benchline.common.events.PricePointRecorded;
import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/** Partitions let groups spread out; the key keeps each group on one partition. Can be raised, never lowered. */
@Configuration(proxyBeanMethods = false)
class KafkaTopicsConfig {

    @Bean
    NewTopic priceRecordedTopic(@Value("${benchline.kafka.partitions:3}") int partitions) {
        return TopicBuilder.name(PricePointRecorded.TOPIC).partitions(partitions).replicas(1).build();
    }
}
