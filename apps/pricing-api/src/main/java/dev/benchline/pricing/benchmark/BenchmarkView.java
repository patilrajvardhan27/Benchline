package dev.benchline.pricing.benchmark;

import java.math.BigDecimal;
import java.time.LocalDate;

public record BenchmarkView(
        String groupId,
        String groupName,
        LocalDate asOfWeek,
        BigDecimal p10,
        BigDecimal p25,
        BigDecimal p50,
        BigDecimal p75,
        BigDecimal p90,
        int nObs,
        String method) {}
