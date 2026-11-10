package dev.benchline.common.events;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

/** Payload of pricing.price-point-recorded.v1. */
public record PricePointRecorded(
        UUID pricePointId,
        String itemId,
        String itemGroupId,
        String source,
        BigDecimal unitPrice,
        String pricingUnit,
        BigDecimal previousUnitPrice,
        LocalDate effectiveDate,
        LocalDate asOfDate) {

    public static final String TYPE = "pricing.price-point-recorded.v1";
    public static final String TOPIC = TYPE;
    public static final String SOURCE = "benchline/pricing-api";
}
