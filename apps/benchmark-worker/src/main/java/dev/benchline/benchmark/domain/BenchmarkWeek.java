package dev.benchline.benchmark.domain;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.TemporalAdjusters;

/**
 * A benchmark snapshot belongs to a Monday-start week and is computed as of
 * the end of that week. Using the week end, not the event date, makes the
 * result the same whatever order events arrive in.
 */
public record BenchmarkWeek(LocalDate start) {

    public static BenchmarkWeek containing(LocalDate date) {
        return new BenchmarkWeek(date.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)));
    }

    public LocalDate end() {
        return start.plusDays(6);
    }
}
