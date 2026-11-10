package dev.benchline.pricing.system;

import java.time.LocalDate;

public record Overview(
        long itemCount, long groupCount, long pricePointCount, LocalDate latestAsOfDate, long openAnomalies) {}
