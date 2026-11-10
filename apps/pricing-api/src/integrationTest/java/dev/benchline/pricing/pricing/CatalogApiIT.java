package dev.benchline.pricing.pricing;

import static dev.benchline.pricing.support.Fixtures.nadac;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import dev.benchline.pricing.PricingApiApplication;
import dev.benchline.testsupport.PostgresTestBase;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

/** The read API against a real database, including the price columns and equivalents. */
@SpringBootTest(classes = PricingApiApplication.class)
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "benchline.security.dev-jwt-secret=0123456789abcdef0123456789abcdef",
    "benchline.outbox.poll-ms=3600000",
    "spring.kafka.bootstrap-servers=localhost:1" // never contacted, the relay is idle
})
class CatalogApiIT extends PostgresTestBase {

    @Autowired MockMvc mvc;
    @Autowired PriceIngestService ingest;

    @BeforeEach
    void seed() {
        ingest.ingest(List.of(
                nadac("00000000001", "0.30000", "2026-10-01"),
                nadac("00000000001", "0.25000", "2026-10-29"),
                nadac("00000000002", "0.10000", "2026-10-29")));
    }

    @Test
    void searchFindsByDescriptionAndShowsLatestPrice() throws Exception {
        mvc.perform(get("/api/v1/items").param("query", "atorva"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(2)))
                .andExpect(jsonPath("$.page.totalElements").value(2))
                .andExpect(jsonPath("$.content[?(@.id=='ndc-00000000001')].latestPrice").value("0.25000"));
    }

    @Test
    void wildcardCharactersInTheQueryAreLiteral() throws Exception {
        mvc.perform(get("/api/v1/items").param("query", "%"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(0)));
    }

    @Test
    void priceHistoryIsOldestFirst() throws Exception {
        mvc.perform(get("/api/v1/items/ndc-00000000001/prices"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].unitPrice").value("0.30000"))
                .andExpect(jsonPath("$[1].unitPrice").value("0.25000"));
    }

    @Test
    void equivalentsListCheaperNdcsInTheSameGroup() throws Exception {
        mvc.perform(get("/api/v1/items/ndc-00000000001/equivalents"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].itemId").value("ndc-00000000002"))
                .andExpect(jsonPath("$[0].savingsPerUnit").value("0.15000"));
    }

    @Test
    void unknownItemIsAProblemJson404() throws Exception {
        mvc.perform(get("/api/v1/items/ndc-99999999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void badSourceFilterIs400() throws Exception {
        mvc.perform(get("/api/v1/items/ndc-00000000001/prices").param("source", "NOPE"))
                .andExpect(status().isBadRequest());
    }
}
