package dev.benchline.pricing.support;

import dev.benchline.pricing.pricing.PricePointInput;
import dev.benchline.pricing.pricing.PriceSource;
import java.math.BigDecimal;
import java.time.LocalDate;

public final class Fixtures {

    public static final String DESCRIPTION = "ATORVASTATIN CALCIUM 20 MG TAB";

    private Fixtures() {}

    public static PricePointInput nadac(String ndc11, String price, String effective) {
        return new PricePointInput(
                ndc11, DESCRIPTION, false, PriceSource.NADAC, new BigDecimal(price), "EA",
                LocalDate.parse(effective), LocalDate.parse(effective).plusDays(5), null);
    }

    public static PricePointInput grouped(String ndc11, String description, String price, String effective, String groupName) {
        return new PricePointInput(
                ndc11, description, false, PriceSource.NADAC, new BigDecimal(price), "EA",
                LocalDate.parse(effective), LocalDate.parse(effective).plusDays(5), groupName);
    }
}
