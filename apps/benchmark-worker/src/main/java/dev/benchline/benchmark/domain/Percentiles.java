package dev.benchline.benchmark.domain;

import java.math.BigDecimal;

/** Result of one benchmark computation. */
public record Percentiles(BigDecimal p10, BigDecimal p25, BigDecimal p50, BigDecimal p75, BigDecimal p90, int nObs) {}
