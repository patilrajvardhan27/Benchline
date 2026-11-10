package dev.benchline.pricing.pricing;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDate;

public record PricePointInput(
        @NotNull @Pattern(regexp = "^[0-9]{11}$", message = "must be 11 digits") String ndc11,
        @NotBlank @Size(max = 300) String description,
        Boolean otc,
        @NotNull PriceSource source,
        @NotNull @DecimalMin(value = "0", inclusive = false) @Digits(integer = 9, fraction = 5) BigDecimal unitPrice,
        @NotBlank @Size(max = 8) String pricingUnit,
        @NotNull LocalDate effectiveDate,
        @NotNull LocalDate asOfDate,
        @Size(min = 1, max = 300) String groupName) {

    /** The text that decides the group: the normalized name when the pipeline sent one, else the description. */
    public String groupLabel() {
        return groupName == null || groupName.isBlank() ? description : groupName;
    }

    public boolean isOtc() {
        return Boolean.TRUE.equals(otc);
    }
}
