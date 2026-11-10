import type { components } from "./generated/schema";

type Schemas = components["schemas"];

export type Item = Schemas["Item"];
export type ItemPage = Schemas["ItemPage"];
export type PricePoint = Schemas["PricePoint"];
export type Equivalent = Schemas["Equivalent"];
export type BenchmarkSnapshot = Schemas["BenchmarkSnapshot"];
export type BenchmarkHistory = Schemas["BenchmarkHistory"];
export type Facility = Schemas["Facility"];
export type Opportunity = Schemas["Opportunity"];
export type OpportunityReport = Schemas["OpportunityReport"];
export type Anomaly = Schemas["Anomaly"];
export type AnomalyPage = Schemas["AnomalyPage"];
export type AnomalyStatus = Schemas["AnomalyStatus"];
export type Overview = Schemas["Overview"];
export type FeatureConfig = Schemas["FeatureConfig"];
export type PageMeta = Schemas["PageMeta"];
