package dev.benchline.common;

import static org.assertj.core.api.Assertions.assertThat;

import dev.benchline.common.money.Money;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class MoneyTest {

    @Test
    void normalizeKeepsFivePlaces() {
        assertThat(Money.normalize(new BigDecimal("1.5")).scale()).isEqualTo(5);
        assertThat(Money.normalize(new BigDecimal("0.031215"))).isEqualByComparingTo("0.03122");
    }
}
