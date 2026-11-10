package dev.benchline.common.money;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Helpers for unit prices. Money is BigDecimal everywhere, never double. */
public final class Money {

    /** Matches numeric(14,5) in the database. */
    public static final int SCALE = 5;

    private Money() {}

    public static BigDecimal parse(String raw) {
        BigDecimal value = new BigDecimal(raw.trim());
        if (value.signum() < 0) {
            throw new IllegalArgumentException("Price cannot be negative");
        }
        return normalize(value);
    }

    public static BigDecimal normalize(BigDecimal value) {
        return value.setScale(SCALE, RoundingMode.HALF_UP);
    }

    public static BigDecimal times(BigDecimal unitPrice, long qty) {
        return normalize(unitPrice.multiply(BigDecimal.valueOf(qty)));
    }
}
