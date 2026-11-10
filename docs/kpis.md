# KPI definitions

**Benchmark percentiles.** For a product group and a week: each product's latest market price as of
that week's end (within 52 weeks), then p10, p25, p50, p75 and p90 by linear interpolation
(`percentile_cont`). `nObs` is the number of products that contributed.

**Savings opportunity.** For one synthetic purchase line:
`(paid unit price - group p25) * quantity`, counted only when the price is above p25.
A facility's total is the sum over its lines. This is a screening figure, not a forecast.

**Versus median.** `(item latest price - group p50) / group p50`, shown on the item page.

**Anomaly score.** The log of new price over old price is compared with the usual log changes in
the same group (or all groups when the group has fewer than 8 changes) using the modified z-score
`0.6745 * (x - median) / MAD`. A change is flagged when the absolute score is at least 3.5 and it
also lies outside 1.5 interquartile ranges. MAD is floored at 0.005. Flags go to a person to confirm
or dismiss. Precision can be measured once enough flags have been reviewed; none have been yet.
