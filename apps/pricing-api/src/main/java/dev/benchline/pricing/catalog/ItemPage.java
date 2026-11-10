package dev.benchline.pricing.catalog;

import dev.benchline.common.paging.PageMeta;
import java.util.List;

public record ItemPage(List<ItemView> content, PageMeta page) {}
