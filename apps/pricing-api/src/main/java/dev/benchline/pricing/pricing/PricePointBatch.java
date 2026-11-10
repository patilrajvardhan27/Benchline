package dev.benchline.pricing.pricing;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record PricePointBatch(
        @NotNull @Size(min = 1, max = PricePointBatch.MAX_ROWS) List<@Valid @NotNull PricePointInput> pricePoints) {

    public static final int MAX_ROWS = 1000;
}
