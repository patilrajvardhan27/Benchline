package dev.benchline.common.flags;

import dev.openfeature.sdk.Client;

/** FeatureFlags backed by an OpenFeature client. The provider (flagd) is wired by the app. */
public class OpenFeatureFlags implements FeatureFlags {

    private final Client client;

    public OpenFeatureFlags(Client client) {
        this.client = client;
    }

    @Override
    public boolean isEnabled(String flagKey, boolean defaultValue) {
        return client.getBooleanValue(flagKey, defaultValue);
    }
}
