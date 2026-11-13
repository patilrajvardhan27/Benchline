package dev.benchline.pricing.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * devJwtSecret enables HS256 validation for local work. Production leaves it
 * empty and validates tokens from the OIDC issuer instead.
 */
@ConfigurationProperties(prefix = "benchline.security")
public record SecurityProperties(String devJwtSecret, boolean requireHttps, List<String> corsAllowedOrigins) {

    public SecurityProperties {
        corsAllowedOrigins = corsAllowedOrigins == null ? List.of() : List.copyOf(corsAllowedOrigins);
    }
}
