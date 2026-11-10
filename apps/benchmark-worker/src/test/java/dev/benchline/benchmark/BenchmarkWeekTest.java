package dev.benchline.benchmark;

import static org.assertj.core.api.Assertions.assertThat;

import dev.benchline.benchmark.domain.BenchmarkWeek;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;

class BenchmarkWeekTest {

    @Test
    void weekStartsOnMonday() {
        // 2026-11-04 is a Wednesday
        BenchmarkWeek week = BenchmarkWeek.containing(LocalDate.parse("2026-11-04"));
        assertThat(week.start()).isEqualTo(LocalDate.parse("2026-11-02"));
        assertThat(week.end()).isEqualTo(LocalDate.parse("2026-11-08"));
    }

    @Test
    void mondayAndSundayShareAWeek() {
        assertThat(BenchmarkWeek.containing(LocalDate.parse("2026-11-02")))
                .isEqualTo(BenchmarkWeek.containing(LocalDate.parse("2026-11-08")));
    }
}
