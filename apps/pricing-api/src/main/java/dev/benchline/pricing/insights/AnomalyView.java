package dev.benchline.pricing.insights;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

public record AnomalyView(
        UUID id,
        UUID pricePointId,
        String groupId,
        String groupName,
        String itemId,
        BigDecimal unitPrice,
        BigDecimal previousUnitPrice,
        LocalDate effectiveDate,
        double score,
        String method,
        AnomalyStatus status,
        Instant detectedAt) {}
