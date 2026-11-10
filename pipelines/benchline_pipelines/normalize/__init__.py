"""Item normalization: turn a raw product description into ingredient, strength and form.

Order of trust: openFDA lookup by NDC, then rules, then an LLM through LiteLLM, then a person.
"""
