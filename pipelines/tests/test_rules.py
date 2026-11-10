import pytest

from benchline_pipelines.normalize.rules import base_ingredient, parse_description
from benchline_pipelines.normalize.vocabulary import SALT_WORDS


@pytest.mark.parametrize(
    ("description", "candidate", "strength", "form", "mods"),
    [
        ("ATORVASTATIN CALCIUM 20 MG TAB", "ATORVASTATIN CALCIUM", "20 MG", "TABLET", ()),
        ("FLUOXETINE HCL 20 MG CAPSULE", "FLUOXETINE HYDROCHLORIDE", "20 MG", "CAPSULE", ()),
        ("ESOMEPRAZOLE MAG DR 20 MG CAP", "ESOMEPRAZOLE MAGNESIUM", "20 MG", "CAPSULE", ("DR",)),
        ("TAPENTADOL ER 100 MG TABLET", "TAPENTADOL", "100 MG", "TABLET", ("ER",)),
        ("MORPHINE SULF ER 100 MG TABLET", "MORPHINE SULFATE", "100 MG", "TABLET", ("ER",)),
        ("KETOROLAC 60 MG/2 ML VIAL", "KETOROLAC", "60 MG/2 ML", "INJECTION", ()),
        ("FLUOROURACIL 5% CREAM", "FLUOROURACIL", "5%", "CREAM", ()),
        ("MISOPROSTOL 100 MCG TABLET", "MISOPROSTOL", "100 MCG", "TABLET", ()),
        ("MESALAMINE 1,000 MG SUPP", "MESALAMINE", "1000 MG", "SUPPOSITORY", ()),
        ("AMETHIA 0.15-0.03-0.01 MG TAB", "AMETHIA", "0.15-0.03-0.01 MG", "TABLET", ()),
        ("CLONIDINE 0.1 MG/DAY PATCH", "CLONIDINE", "0.1 MG/DAY", "PATCH", ()),
        ("DILTIAZEM 24H ER(LA) 360 MG TB", "DILTIAZEM", "360 MG", "TABLET", ("ER",)),
        ("OXYCODONE HCL (IR) 15 MG TAB", "OXYCODONE HYDROCHLORIDE", "15 MG", "TABLET", ()),
        ("PHENYTOIN 50 MG INFATAB CHEW", "PHENYTOIN", "50 MG", "", ("CHEW",)),
    ],
)
def test_reads_real_nadac_descriptions(description, candidate, strength, form, mods) -> None:  # type: ignore[no-untyped-def]
    parsed = parse_description(description)
    assert (parsed.candidate, parsed.strength, parsed.form, parsed.modifiers) == (candidate, strength, form, mods)


def test_a_description_with_no_strength_still_yields_words_and_form() -> None:
    parsed = parse_description("BION TEARS EYE DROP")
    assert parsed.strength == "" and parsed.form == "DROPS" and "BION" in parsed.candidate


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ATORVASTATIN CALCIUM", "ATORVASTATIN"),
        ("METFORMIN HYDROCHLORIDE", "METFORMIN"),
        ("POTASSIUM CHLORIDE", "POTASSIUM CHLORIDE"),  # both words are salt words: keep it whole
        ("SODIUM CHLORIDE", "SODIUM CHLORIDE"),
        ("LEVOTHYROXINE SODIUM", "LEVOTHYROXINE"),
        ("ASPIRIN", "ASPIRIN"),
    ],
)
def test_base_ingredient_drops_only_the_salt(name: str, expected: str) -> None:
    assert base_ingredient(name) == expected


def test_salt_words_are_upper_case_single_words() -> None:
    assert all(w == w.upper() and " " not in w for w in SALT_WORDS)


@pytest.mark.parametrize("name", ["ERTUGLIFLOZIN PIDOLATE", "FLUOCINOLONE ACETONIDE", "OLMESARTAN MEDOXOMIL",
                                  "AMPHETAMINE ASPARTATE"])
def test_ester_and_salt_names_seen_in_real_openfda_data_are_stripped(name: str) -> None:
    assert base_ingredient(name) == name.split()[0]


def test_esters_that_name_different_drugs_do_not_collapse_to_the_same_name() -> None:
    """Fluticasone furoate and propionate are different drugs. FUROATE is not stripped, so they stay apart."""
    assert base_ingredient("FLUTICASONE FUROATE") != base_ingredient("FLUTICASONE PROPIONATE")
