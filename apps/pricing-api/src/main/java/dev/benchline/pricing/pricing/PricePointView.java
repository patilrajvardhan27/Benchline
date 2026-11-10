package dev.benchline.pricing.pricing;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record PricePointView(
        UUID id,
        String itemId,
        String source,
        BigDecimal unitPrice,
        String pricingUnit,
        LocalDate effectiveDate,
        LocalDate asOfDate) {}
