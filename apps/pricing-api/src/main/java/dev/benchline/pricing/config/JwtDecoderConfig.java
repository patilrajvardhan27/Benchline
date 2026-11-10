package dev.benchline.pricing.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

/**
 * Local-only decoder. When no dev secret is set, Spring Boot builds the decoder
 * from spring.security.oauth2.resourceserver.jwt.issuer-uri, and the app fails
 * to start if that is missing too, so there is no silently open mode.
 */
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(SecurityProperties.class)
public class JwtDecoderConfig {

    private static final int MIN_SECRET_BYTES = 32;

    @Bean
    @org.springframework.boot.autoconfigure.condition.ConditionalOnProperty(
            prefix = "benchline.security", name = "dev-jwt-secret")
    JwtDecoder devJwtDecoder(SecurityProperties props) {
        byte[] bytes = props.devJwtSecret().getBytes(StandardCharsets.UTF_8);
        if (bytes.length < MIN_SECRET_BYTES) {
            throw new IllegalStateException("benchline.security.dev-jwt-secret must be at least 32 bytes");
        }
        SecretKey key = new SecretKeySpec(bytes, "HmacSHA256");
        return NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
    }
}
