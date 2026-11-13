package dev.benchline.benchmark;

import static org.assertj.core.api.Assertions.assertThat;

import dev.benchline.benchmark.domain.Percentiles;
import java.math.BigDecimal;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

class PercentilesTest {

    private static List<BigDecimal> prices(String... values) {
        return Stream.of(values).map(BigDecimal::new).toList();
    }

    @Test
    void matchesHandComputedValues() {
        Percentiles p = Percentiles.of(prices("0.5", "0.1", "0.4", "0.2", "0.3")).orElseThrow();
        assertThat(List.of(p.p10(), p.p25(), p.p50(), p.p75(), p.p90()))
                .usingElementComparator(BigDecimal::compareTo)
                .containsExactly(new BigDecimal("0.14"), new BigDecimal("0.2"), new BigDecimal("0.3"),
                        new BigDecimal("0.4"), new BigDecimal("0.46"));
        assertThat(p.nObs()).isEqualTo(5);
    }

    @Test
    void anExactHalfRoundsUp() {
        // p10 of these two is 0.050285 exactly; a double would hold 0.0502849999... and round down.
        Percentiles p = Percentiles.of(prices("0.05023", "0.05078")).orElseThrow();
        assertThat(p.p10()).isEqualByComparingTo("0.05029");
    }

    @Test
    void oneProductGivesItsOwnPriceEverywhere() {
        Percentiles p = Percentiles.of(prices("1.23456")).orElseThrow();
        assertThat(p.p10()).isEqualByComparingTo("1.23456");
        assertThat(p.p90()).isEqualByComparingTo("1.23456");
    }

    @Test
    void noProductsGiveNoBenchmark() {
        assertThat(Percentiles.of(List.of())).isEmpty();
    }
}
