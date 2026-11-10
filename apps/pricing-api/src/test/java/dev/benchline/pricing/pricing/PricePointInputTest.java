package dev.benchline.pricing.pricing;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.validation.Validation;
import java.math.BigDecimal;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;

class PricePointInputTest {

    private static PricePointInput with(String groupName) {
        return new PricePointInput("00093715698", "ATORVASTATIN CALCIUM 20 MG TAB", false, PriceSource.NADAC,
                new BigDecimal("0.03"), "EA", LocalDate.parse("2026-10-29"), LocalDate.parse("2026-11-03"), groupName);
    }

    @Test
    void groupNameWinsWhenGiven() {
        assertThat(with("ATORVASTATIN 20 MG TABLET").groupLabel()).isEqualTo("ATORVASTATIN 20 MG TABLET");
    }

    @Test
    void descriptionIsUsedWhenGroupNameIsMissingOrBlank() {
        assertThat(with(null).groupLabel()).isEqualTo("ATORVASTATIN CALCIUM 20 MG TAB");
        assertThat(with("   ").groupLabel()).isEqualTo("ATORVASTATIN CALCIUM 20 MG TAB");
    }

    @Test
    void anOverlongGroupNameIsRejected() {
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            assertThat(factory.getValidator().validate(with("X".repeat(301)))).hasSize(1);
            assertThat(factory.getValidator().validate(with("X".repeat(300)))).isEmpty();
        }
    }
}
