package dev.benchline.pricing.config;

import static org.springframework.http.HttpMethod.GET;
import static org.springframework.http.HttpMethod.PATCH;
import static org.springframework.http.HttpMethod.POST;

import java.time.Duration;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy;
import org.springframework.security.web.servlet.util.matcher.PathPatternRequestMatcher;
import org.springframework.security.web.util.matcher.NegatedRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

/**
 * Deny by default. Public reads are listed explicitly because they expose only
 * public CMS data; everything else needs a token with the matching scope.
 * The API is stateless (bearer tokens, no cookies), so there is no session to
 * fixate and CSRF protection has nothing to protect.
 */
@Configuration(proxyBeanMethods = false)
@EnableWebSecurity
public class SecurityConfig {

    private static final long HSTS_SECONDS = Duration.ofDays(365).toSeconds();

    @Bean
    SecurityFilterChain apiChain(HttpSecurity http, ProblemSecurityHandlers problems, SecurityProperties props)
            throws Exception {
        http.csrf(csrf -> csrf.disable())
                .cors(Customizer.withDefaults())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .headers(h -> h
                        .httpStrictTransportSecurity(hsts -> hsts
                                .includeSubDomains(true).preload(true).maxAgeInSeconds(HSTS_SECONDS))
                        .contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'none'; frame-ancestors 'none'"))
                        .frameOptions(f -> f.deny())
                        .referrerPolicy(r -> r.policy(ReferrerPolicy.NO_REFERRER))
                        .permissionsPolicyHeader(p -> p.policy("geolocation=(), camera=(), microphone=()")))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health/**").permitAll()
                        .requestMatchers(GET, "/api/v1/overview", "/api/v1/config").permitAll()
                        .requestMatchers(GET, "/api/v1/items", "/api/v1/items/**").permitAll()
                        .requestMatchers(GET, "/api/v1/benchmarks/**").permitAll()
                        .requestMatchers(POST, "/api/v1/price-points", "/api/v1/price-points:batch")
                        .hasAuthority("SCOPE_prices:write")
                        .requestMatchers(GET, "/api/v1/members", "/api/v1/members/**")
                        .hasAuthority("SCOPE_members:read")
                        .requestMatchers(GET, "/api/v1/anomalies").hasAuthority("SCOPE_insights:read")
                        .requestMatchers(PATCH, "/api/v1/anomalies/*").hasAuthority("SCOPE_insights:write")
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o
                        .jwt(Customizer.withDefaults())
                        .authenticationEntryPoint(problems)
                        .accessDeniedHandler(problems))
                .exceptionHandling(e -> e.authenticationEntryPoint(problems).accessDeniedHandler(problems));

        if (props.requireHttps()) {
            // Probes hit the pod over plain HTTP; everything else must arrive over TLS.
            RequestMatcher notProbe =
                    new NegatedRequestMatcher(PathPatternRequestMatcher.withDefaults().matcher("/actuator/health/**"));
            http.redirectToHttps(https -> https.requestMatchers(notProbe));
        }
        return http.build();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource(SecurityProperties props) {
        CorsConfiguration cors = new CorsConfiguration();
        cors.setAllowedOrigins(props.corsAllowedOrigins());
        cors.setAllowedMethods(List.of("GET", "POST", "PATCH", "OPTIONS"));
        cors.setAllowedHeaders(List.of(HttpHeaders.AUTHORIZATION, HttpHeaders.CONTENT_TYPE));
        cors.setAllowCredentials(false);
        cors.setMaxAge(Duration.ofHours(1));
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", cors);
        return source;
    }
}
