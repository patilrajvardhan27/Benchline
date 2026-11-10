package dev.benchline.pricing.insights;

import jakarta.validation.constraints.NotNull;

/** OPEN is not a valid review outcome, so the controller rejects it. */
public record AnomalyReview(@NotNull AnomalyStatus status) {}
