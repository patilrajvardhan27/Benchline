package dev.benchline.common.flags;

import dev.openfeature.contrib.providers.flagd.FlagdOptions;
import dev.openfeature.contrib.providers.flagd.FlagdProvider;
import dev.openfeature.sdk.Client;
import dev.openfeature.sdk.OpenFeatureAPI;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Registers flagd as the OpenFeature provider. If flagd is unreachable the SDK
 * returns each flag's default, so an outage turns features off rather than
 * breaking requests.
 */
@Configuration(proxyBeanMethods = false)
public class FlagConfiguration {

    @Bean
    @ConditionalOnMissingBean(FeatureFlags.class)
    FeatureFlags featureFlags(
            @Value("${benchline.flags.host:localhost}") String host,
            @Value("${benchline.flags.port:8013}") int port) {
        FlagdOptions options = FlagdOptions.builder().host(host).port(port).build();
        OpenFeatureAPI api = OpenFeatureAPI.getInstance();
        api.setProvider(new FlagdProvider(options));
        Client client = api.getClient("benchline");
        return new OpenFeatureFlags(client);
    }
}
