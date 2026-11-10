"""Word lists used to read drug descriptions. Short on purpose: each entry earns its place."""

from __future__ import annotations

# Abbreviations in NADAC descriptions, expanded to the full salt name that openFDA uses.
SALT_ABBREVIATIONS = {
    "HCL": "HYDROCHLORIDE", "HCI": "HYDROCHLORIDE", "HC": "HYDROCHLORIDE", "HBR": "HYDROBROMIDE",
    "SULF": "SULFATE", "SO4": "SULFATE", "MAG": "MAGNESIUM", "SOD": "SODIUM", "POT": "POTASSIUM",
    "CALC": "CALCIUM", "PH": "PHOSPHATE", "PHOS": "PHOSPHATE", "HYC": "HYCLATE", "MES": "MESYLATE",
    "BESYL": "BESYLATE", "TART": "TARTRATE", "SUCC": "SUCCINATE", "MAL": "MALEATE", "FUM": "FUMARATE",
}

# Trailing words that name the salt, not the drug. Stripped to form the base ingredient.
SALT_WORDS = frozenset({
    "HYDROCHLORIDE", "HYDROBROMIDE", "SULFATE", "SODIUM", "POTASSIUM", "CALCIUM", "MAGNESIUM",
    "PHOSPHATE", "MESYLATE", "MALEATE", "TARTRATE", "SUCCINATE", "FUMARATE", "BESYLATE", "ACETATE",
    "CITRATE", "HYCLATE", "BROMIDE", "CHLORIDE", "NITRATE", "OXIDE", "MONOHYDRATE", "ANHYDROUS",
    "DIHYDRATE", "HEMIHYDRATE", "TRIHYDRATE", "HYDRATE", "MOFETIL", "PIDOLATE", "TRIFENATATE",
    "ACETONIDE", "MEDOXOMIL", "ASPARTATE", "SACCHARATE", "DIHYDROCHLORIDE", "BISULFATE", "TOSYLATE",
    "BESILATE", "PROPIONATE", "DISODIUM", "MEGLUMINE", "HEXAHYDRATE", "TROMETHAMINE", "BITARTRATE",
    "GLUCONATE", "LACTATE", "PAMOATE",
})

FORMS = {
    "TAB": "TABLET", "TABS": "TABLET", "TABLET": "TABLET", "TABLETS": "TABLET", "TB": "TABLET",
    "CAP": "CAPSULE", "CAPS": "CAPSULE", "CAPSULE": "CAPSULE", "CAPSULES": "CAPSULE",
    "SOLN": "SOLUTION", "SOLUTION": "SOLUTION", "SOL": "SOLUTION",
    "SUSP": "SUSPENSION", "SUSPENSION": "SUSPENSION",
    "SYRUP": "SYRUP", "ELIXIR": "ELIXIR", "LIQUID": "LIQUID", "DROPS": "DROPS", "DROP": "DROPS",
    "CREAM": "CREAM", "OINT": "OINTMENT", "OINTMENT": "OINTMENT", "GEL": "GEL", "LOTION": "LOTION",
    "FOAM": "FOAM", "PATCH": "PATCH", "SPRAY": "SPRAY", "INHALER": "INHALER", "POWDER": "POWDER",
    "SUPP": "SUPPOSITORY", "SUPPOSITORY": "SUPPOSITORY", "VIAL": "INJECTION", "INJ": "INJECTION",
    "INJECTION": "INJECTION", "SYRINGE": "INJECTION", "AMPUL": "INJECTION", "AMPULE": "INJECTION",
    "FILM": "FILM", "PACKET": "POWDER", "LOZENGE": "LOZENGE", "KIT": "KIT",
}

# Release and delivery modifiers. Different release profiles are different products,
# so they stay part of the group; extended-release spellings collapse to one.
MODIFIERS = {
    "ER": "ER", "XR": "ER", "SR": "ER", "CR": "ER", "LA": "ER", "XL": "ER", "24H": "ER", "12H": "ER",
    "12HR": "ER", "24HR": "ER", "DR": "DR", "EC": "DR", "ODT": "ODT", "CHEW": "CHEW", "CHEWABLE": "CHEW",
}

IGNORED = frozenset({"IR", "(IR)", "PK", "(2PK)", "PUMP", "FOR", "AND", "W/", "WITH"})

# openFDA dosage_form pieces to our modifiers. Coatings do not change the product here.
FDA_MODIFIERS = {
    "EXTENDED RELEASE": "ER", "DELAYED RELEASE": "DR", "ORALLY DISINTEGRATING": "ODT",
    "CHEWABLE": "CHEW", "SUSTAINED ACTION": "ER",
}
FDA_FORM_BASE = {
    "TABLET": "TABLET", "CAPSULE": "CAPSULE", "SOLUTION": "SOLUTION", "SUSPENSION": "SUSPENSION",
    "SYRUP": "SYRUP", "ELIXIR": "ELIXIR", "CREAM": "CREAM", "OINTMENT": "OINTMENT", "GEL": "GEL",
    "LOTION": "LOTION", "FOAM": "FOAM", "PATCH": "PATCH", "SPRAY": "SPRAY", "POWDER": "POWDER",
    "INJECTION": "INJECTION", "SUPPOSITORY": "SUPPOSITORY", "LIQUID": "LIQUID", "DROPS": "DROPS",
    "INHALANT": "INHALER", "AEROSOL": "INHALER", "FILM": "FILM", "LOZENGE": "LOZENGE", "KIT": "KIT",
    "TROCHE": "LOZENGE", "GRANULE": "POWDER",
}
