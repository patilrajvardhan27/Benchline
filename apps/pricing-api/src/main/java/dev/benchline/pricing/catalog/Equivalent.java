package dev.benchline.pricing.catalog;

import java.math.BigDecimal;

/** Another NDC sold under the same description at a lower latest price. */
public record Equivalent(String itemId, String ndc11, BigDecimal latestPrice, BigDecimal savingsPerUnit) {}
