package dev.benchline.pricing.pricing;

import java.util.Locale;

/**
 * NADAC has no ingredient or strength columns, so NDCs that share a
 * normalized description form one group. See docs/adr/0005-item-grouping.md.
 */
public final class ItemGrouping {

    private ItemGrouping() {}

    public static String normalizeName(String description) {
        return description.trim().replaceAll("\\s+", " ").toUpperCase(Locale.ROOT);
    }

    public static String groupId(String description) {
        String slug = normalizeName(description)
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9]+", "-")
                .replaceAll("^-|-$", "");
        return "grp-" + slug;
    }

    public static String itemId(String ndc11) {
        return "ndc-" + ndc11;
    }
}
