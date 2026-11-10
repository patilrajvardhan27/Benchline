package dev.benchline.pricing.insights;

import dev.benchline.common.paging.PageMeta;
import java.util.List;

public record AnomalyPage(List<AnomalyView> content, PageMeta page) {}
