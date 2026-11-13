package dev.benchline.benchmark.domain;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Optional;

/** p10 to p90 by linear interpolation, in exact decimal arithmetic, rounded half-up to five places. */
public record Percentiles(BigDecimal p10, BigDecimal p25, BigDecimal p50, BigDecimal p75, BigDecimal p90, int nObs) {

    public static Optional<Percentiles> of(List<BigDecimal> prices) {
        if (prices.isEmpty()) {
            return Optional.empty();
        }
        List<BigDecimal> sorted = prices.stream().sorted().toList();
        return Optional.of(new Percentiles(at(sorted, "0.10"), at(sorted, "0.25"), at(sorted, "0.50"),
                at(sorted, "0.75"), at(sorted, "0.90"), sorted.size()));
    }

    private static BigDecimal at(List<BigDecimal> sorted, String quantile) {
        BigDecimal position = new BigDecimal(quantile).multiply(BigDecimal.valueOf(sorted.size() - 1L));
        int lower = position.intValue();
        BigDecimal value = sorted.get(lower);
        if (lower + 1 < sorted.size()) {
            BigDecimal fraction = position.subtract(BigDecimal.valueOf(lower));
            value = value.add(sorted.get(lower + 1).subtract(value).multiply(fraction));
        }
        return value.setScale(5, RoundingMode.HALF_UP);
    }
}
