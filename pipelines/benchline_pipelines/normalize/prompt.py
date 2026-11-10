"""The instructions and worked examples sent to the model. Change PROMPT_VERSION in llm.py when you edit them."""

from __future__ import annotations

import json

INSTRUCTIONS = """You normalize US drug product descriptions from a pharmacy price list.
Reply with JSON only: {"ingredient": str, "is_brand": bool, "strength": str|null, "form": str|null}.

- ingredient: the generic active ingredient in UPPER CASE, without salt words (write ATORVASTATIN, not
  ATORVASTATIN CALCIUM). Separate combination products with " / ". If the description starts with a
  brand name, give the generic ingredient of that brand.
- is_brand: true if the description begins with a brand or store-brand name, false if it begins with
  a generic ingredient name.
- strength: copy it from the description, for example "20 MG". Never invent a number.
- form: TABLET, CAPSULE, SOLUTION, CREAM, INJECTION and so on, or null if the description does not say.
- If you are not sure what the ingredient is, return "UNKNOWN" for it. A wrong answer is worse than UNKNOWN.

Examples:"""
EXAMPLES: list[tuple[str, dict[str, object]]] = [
    ("ZYPREXA 15 MG TABLET", {"ingredient": "OLANZAPINE", "is_brand": True, "strength": "15 MG", "form": "TABLET"}),
    ("MISOPROSTOL 100 MCG TABLET",
     {"ingredient": "MISOPROSTOL", "is_brand": False, "strength": "100 MCG", "form": "TABLET"}),
    ("SM ALLERGY RELIEF 50 MCG SPRAY",
     {"ingredient": "UNKNOWN", "is_brand": True, "strength": "50 MCG", "form": None}),
]
SYSTEM_PROMPT = INSTRUCTIONS + "\n" + "\n".join(f'"{d}" -> {json.dumps(r)}' for d, r in EXAMPLES)
