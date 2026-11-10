package dev.benchline.common.flags;

/** The only way application code reads a flag. Keeps the vendor SDK out of business logic. */
public interface FeatureFlags {

    String ANOMALY_ALERTS = "anomaly-alerts-enabled";

    boolean isEnabled(String flagKey, boolean defaultValue);

    default boolean anomalyAlertsEnabled() {
        return isEnabled(ANOMALY_ALERTS, false);
    }
}
