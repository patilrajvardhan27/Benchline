package dev.benchline.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.benchline.common.money.Money;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class MoneyTest {

    @Test
    void parseKeepsFivePlaces() {
        assertThat(Money.parse("0.03121")).isEqualByComparingTo("0.03121");
        assertThat(Money.parse("1.5").scale()).isEqualTo(5);
    }

    @Test
    void parseRejectsNegative() {
        assertThatThrownBy(() -> Money.parse("-0.1")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void timesDoesNotLosePrecision() {
        assertThat(Money.times(new BigDecimal("0.03121"), 1000)).isEqualByComparingTo("31.21000");
    }
}
