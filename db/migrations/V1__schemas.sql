-- One schema per bounded context. Cross-schema foreign keys are allowed only
-- toward catalog, which every other context reads.
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS pricing;
CREATE SCHEMA IF NOT EXISTS benchmark;
CREATE SCHEMA IF NOT EXISTS member;
CREATE SCHEMA IF NOT EXISTS insights;
