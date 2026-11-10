package dev.benchline.pricing.member;

import java.math.BigDecimal;

public record Opportunity(
        long purchaseLineId,
        String itemId,
        String groupId,
        String description,
        BigDecimal paidUnitPrice,
        BigDecimal benchmarkP25,
        BigDecimal benchmarkP50,
        int qty,
        BigDecimal savingsAmount,
        String source) {}
