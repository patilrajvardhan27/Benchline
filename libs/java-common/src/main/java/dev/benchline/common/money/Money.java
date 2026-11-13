package dev.benchline.common.money;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Helpers for unit prices. Money is BigDecimal everywhere, never double. */
public final class Money {

    /** Matches numeric(14,5) in the database. */
    public static final int SCALE = 5;

    private Money() {}

    public static BigDecimal normalize(BigDecimal value) {
        return value.setScale(SCALE, RoundingMode.HALF_UP);
    }
}
