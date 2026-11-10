package dev.benchline.pricing.catalog;

import java.math.BigDecimal;
import java.time.LocalDate;

public record ItemView(
        String id,
        String ndc11,
        String description,
        String groupId,
        String groupName,
        boolean otc,
        BigDecimal latestPrice,
        LocalDate latestEffectiveDate) {}
