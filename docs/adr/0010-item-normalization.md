# 0010. Item normalization: lookups first, an LLM last

Status: accepted. Supersedes the grouping rule in [0005](0005-item-grouping.md) when a group map is supplied.

## Context
Grouping by raw description splits one drug across many groups and hides brand and generic differences.
We want groups by ingredient, strength and form. Parsing every description by rule is not enough:
75% of NDCs resolve that way, and brand names do not.

## Decision
Normalize in layers, cheapest and most trustworthy first: openFDA lookup by NDC, rules on the description,
an LLM through LiteLLM for what is left, a person for what the model flags. The API accepts an optional
`groupName` on a price point. When present it decides the group; when absent the description does, as before.
Model output is checked against the description, cached, budget-capped, and anything not grounded in the
text is marked for review. Models are called through LiteLLM, either as a library (a Router with retries
and a fallback) or through a gateway (virtual keys, budgets, spend tracking), chosen by configuration.

## Consequences
Most NDCs never touch a model, so cost and risk stay small and the pipeline works with no key at all.
LiteLLM keeps the provider choice out of the code. A group built from a model answer can always be found
(`method = llm`) and reviewed. Changing groups requires reloading into an empty database, because existing
items keep their first group. The API field is optional, so old clients and data are unaffected.
