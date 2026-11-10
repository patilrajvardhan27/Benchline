package dev.benchline.pricing.member;

/** Always synthetic; the database refuses rows that say otherwise. */
public record Facility(String id, String name, String bedBand, String region, boolean synthetic) {}
