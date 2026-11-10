import type { Item } from "../shared/api/types";

export const ITEM: Item = {
  id: "ndc-00000000001", ndc11: "00000000001", description: "ATORVASTATIN CALCIUM 20 MG TAB",
  groupId: "grp-atorvastatin", groupName: "ATORVASTATIN CALCIUM 20 MG TAB", otc: false,
  latestPrice: "0.03121", latestEffectiveDate: "2026-10-29",
};
const OTHER: Item = { ...ITEM, id: "ndc-00000000002", ndc11: "00000000002", latestPrice: "0.02000" };
const METFORMIN: Item = {
  ...ITEM, id: "ndc-00000000003", ndc11: "00000000003", description: "METFORMIN HCL 500 MG TAB",
  groupId: "grp-metformin", groupName: "METFORMIN HCL 500 MG TAB", latestPrice: "0.01500",
};

export const FILES: Record<string, unknown> = {
  "overview.json": { itemCount: 3, groupCount: 2, pricePointCount: 10, latestAsOfDate: "2026-10-28", openAnomalies: 1 },
  "config.json": { anomalyAlertsEnabled: true },
  "items.json": [ITEM, OTHER, METFORMIN],
  "items/ndc-00000000001.json": {
    prices: [
      { id: "p1", itemId: ITEM.id, source: "NADAC", unitPrice: "0.03307", pricingUnit: "EA", effectiveDate: "2026-09-01", asOfDate: "2026-09-09" },
      { id: "p2", itemId: ITEM.id, source: "NADAC", unitPrice: "0.03121", pricingUnit: "EA", effectiveDate: "2026-10-29", asOfDate: "2026-11-03" },
    ],
    equivalents: [{ itemId: OTHER.id, ndc11: OTHER.ndc11, latestPrice: "0.02000", savingsPerUnit: "0.01121" }],
  },
  "benchmarks/grp-atorvastatin.json": {
    latest: { groupId: "grp-atorvastatin", groupName: ITEM.groupName, asOfWeek: "2026-10-26", p10: "0.02", p25: "0.025", p50: "0.03", p75: "0.035", p90: "0.04", nObs: 12, method: "percentile_cont/latest-per-item/52w" },
    history: { groupId: "grp-atorvastatin", snapshots: [] },
  },
  "members.json": [{ id: "fac-1", name: "Demo General", bedBand: "200-399", region: "South", synthetic: true }],
  "opportunities/fac-1.json": {
    facility: { id: "fac-1", name: "Demo General", bedBand: "200-399", region: "South", synthetic: true },
    totalSavings: "125.50000",
    lines: [{ purchaseLineId: 1, itemId: ITEM.id, groupId: "grp-atorvastatin", description: ITEM.description, paidUnitPrice: "0.05000", benchmarkP25: "0.02500", benchmarkP50: "0.03000", qty: 5000, savingsAmount: "125.00000", source: "SYNTHETIC_DEMO" }],
  },
  "anomalies.json": [{
    id: "a1", pricePointId: "p2", groupId: "grp-atorvastatin", groupName: ITEM.groupName, itemId: ITEM.id,
    unitPrice: "0.09000", previousUnitPrice: "0.03000", effectiveDate: "2026-10-29", score: 6.2,
    method: "robust-z/log-change", status: "OPEN", detectedAt: "2026-11-03T10:00:00Z",
  }],
};
