package dev.benchline.pricing.benchmark;

import java.util.List;

public record BenchmarkHistory(String groupId, List<BenchmarkView> snapshots) {}
