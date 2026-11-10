package dev.benchline.pricing.member;

import dev.benchline.common.paging.PageMeta;
import java.math.BigDecimal;
import java.util.List;

public record OpportunityReport(Facility facility, BigDecimal totalSavings, List<Opportunity> lines, PageMeta page) {}
