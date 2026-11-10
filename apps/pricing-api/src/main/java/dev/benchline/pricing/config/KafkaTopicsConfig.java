package dev.benchline.pricing.config;

import dev.benchline.common.events.PricePointRecorded;
import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/** Three partitions so groups spread out; the key keeps each group on one partition. */
@Configuration(proxyBeanMethods = false)
class KafkaTopicsConfig {

    @Bean
    NewTopic priceRecordedTopic() {
        return TopicBuilder.name(PricePointRecorded.TOPIC).partitions(3).replicas(1).build();
    }
}
