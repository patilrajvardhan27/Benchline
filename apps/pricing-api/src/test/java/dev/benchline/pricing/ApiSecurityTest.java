package dev.benchline.pricing;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import dev.benchline.common.errors.GlobalExceptionHandler;
import dev.benchline.common.flags.FeatureFlags;
import dev.benchline.common.json.JacksonMoneyConfig;
import dev.benchline.pricing.benchmark.BenchmarkController;
import dev.benchline.pricing.catalog.ItemController;
import dev.benchline.pricing.catalog.ItemPage;
import dev.benchline.pricing.catalog.ItemQueries;
import dev.benchline.common.paging.PageMeta;
import dev.benchline.pricing.config.JwtDecoderConfig;
import dev.benchline.pricing.config.ProblemSecurityHandlers;
import dev.benchline.pricing.config.SecurityConfig;
import dev.benchline.pricing.insights.AnomalyController;
import dev.benchline.pricing.insights.AnomalyQueries;
import dev.benchline.pricing.member.MemberController;
import dev.benchline.pricing.member.MemberQueries;
import dev.benchline.pricing.pricing.IngestReceipt;
import dev.benchline.pricing.pricing.PriceController;
import dev.benchline.pricing.pricing.PriceHistoryQueries;
import dev.benchline.pricing.pricing.PriceIngestService;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/** Authorization rules, error shape and response headers. No database needed. */
@WebMvcTest(controllers = {
    ItemController.class, PriceController.class, MemberController.class, AnomalyController.class,
    BenchmarkController.class
})
@Import({SecurityConfig.class, ProblemSecurityHandlers.class, JwtDecoderConfig.class,
    GlobalExceptionHandler.class, JacksonMoneyConfig.class})
@TestPropertySource(properties = {
    "benchline.security.dev-jwt-secret=0123456789abcdef0123456789abcdef",
    "benchline.security.cors-allowed-origins=http://localhost:5173"
})
class ApiSecurityTest {

    private static final String VALID_PRICE = """
            {"ndc11":"00093715698","description":"ATORVASTATIN CALCIUM 20 MG TAB","source":"NADAC",
             "unitPrice":"0.03121","pricingUnit":"EA","effectiveDate":"2026-10-29","asOfDate":"2026-11-03"}
            """;

    @Autowired MockMvc mvc;
    @MockitoBean JwtDecoder jwtDecoder;
    @MockitoBean FeatureFlags flags;
    @MockitoBean ItemQueries items;
    @MockitoBean PriceHistoryQueries history;
    @MockitoBean PriceIngestService ingest;
    @MockitoBean MemberQueries members;
    @MockitoBean AnomalyQueries anomalies;
    @MockitoBean dev.benchline.pricing.benchmark.BenchmarkQueries benchmarks;

    private static RequestPostProcessor scope(String scope) {
        return jwt().authorities(new SimpleGrantedAuthority("SCOPE_" + scope));
    }

    @Test
    void publicCatalogReadNeedsNoToken() throws Exception {
        given(items.search(any(), any(), any())).willReturn(new ItemPage(List.of(), PageMeta.of(0, 25, 0)));
        mvc.perform(get("/api/v1/items")).andExpect(status().isOk());
    }

    @Test
    void memberDataWithoutTokenIs401ProblemJson() throws Exception {
        mvc.perform(get("/api/v1/members"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("WWW-Authenticate", "Bearer"))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void tokenWithWrongScopeIs403() throws Exception {
        mvc.perform(get("/api/v1/members").with(scope("prices:write")))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.title").value("Forbidden"));
    }

    @Test
    void tokenWithRightScopeReadsMembers() throws Exception {
        given(members.facilities()).willReturn(List.of());
        mvc.perform(get("/api/v1/members").with(scope("members:read"))).andExpect(status().isOk());
    }

    @Test
    void writeEndpointsRequireWriteScope() throws Exception {
        mvc.perform(post("/api/v1/price-points").contentType(MediaType.APPLICATION_JSON).content(VALID_PRICE))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/price-points").with(scope("members:read"))
                        .contentType(MediaType.APPLICATION_JSON).content(VALID_PRICE))
                .andExpect(status().isForbidden());
    }

    @Test
    void validWriteReturns202() throws Exception {
        given(ingest.ingest(any())).willReturn(new IngestReceipt(1, 0));
        mvc.perform(post("/api/v1/price-points").with(scope("prices:write"))
                        .contentType(MediaType.APPLICATION_JSON).content(VALID_PRICE))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.accepted").value(1));
    }

    @Test
    void invalidBodyIs400WithFieldErrorsAndNoInternals() throws Exception {
        String bad = VALID_PRICE.replace("00093715698", "123").replace("0.03121", "-1");
        mvc.perform(post("/api/v1/price-points").with(scope("prices:write"))
                        .contentType(MediaType.APPLICATION_JSON).content(bad))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[*].field").isArray())
                .andExpect(content().string(not(containsString("Exception"))))
                .andExpect(content().string(not(containsString("dev.benchline"))));
    }

    @Test
    void unexpectedErrorsNeverLeakDetails() throws Exception {
        given(members.facilities()).willThrow(new IllegalStateException("jdbc:postgresql://secret-host:5432/benchline"));
        mvc.perform(get("/api/v1/members").with(scope("members:read")))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.detail").value("Something went wrong on our side"))
                .andExpect(content().string(not(containsString("secret-host"))))
                .andExpect(content().string(not(containsString("at dev.benchline"))));
    }

    @Test
    void unknownRoutesAreDeniedNotRevealed() throws Exception {
        mvc.perform(get("/api/v1/does-not-exist")).andExpect(status().isUnauthorized());
        mvc.perform(get("/internal/debug").with(scope("insights:read"))).andExpect(status().isForbidden());
    }

    @Test
    void responsesCarrySecurityHeaders() throws Exception {
        given(items.search(any(), any(), any())).willReturn(new ItemPage(List.of(), PageMeta.of(0, 25, 0)));
        mvc.perform(get("/api/v1/items").secure(true))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"))
                .andExpect(header().string("X-Frame-Options", "DENY"))
                .andExpect(header().string("Referrer-Policy", "no-referrer"))
                .andExpect(header().string("Content-Security-Policy", containsString("default-src 'none'")))
                .andExpect(header().string("Strict-Transport-Security", containsString("max-age=31536000")));
    }

    @Test
    void anomalyQueueIsEmptyWhenFlagIsOff() throws Exception {
        given(flags.anomalyAlertsEnabled()).willReturn(false);
        mvc.perform(get("/api/v1/anomalies").with(scope("insights:read")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isEmpty());
    }

    @Test
    void reviewingWithOpenStatusIsRejected() throws Exception {
        mvc.perform(patch("/api/v1/anomalies/" + UUID.randomUUID()).with(scope("insights:write"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"status\":\"OPEN\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void reviewNeedsWriteScopeNotReadScope() throws Exception {
        mvc.perform(patch("/api/v1/anomalies/" + UUID.randomUUID()).with(scope("insights:read"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"status\":\"CONFIRMED\"}"))
                .andExpect(status().isForbidden());
        verify(anomalies, org.mockito.Mockito.never()).review(any(), any(), any());
    }
}
