import pytest

from benchline_pipelines.silver.ndc import normalize_ndc


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00093715698", "00093715698"),  # already 11 digits
        ("0093-7156-98", "00093715698"),  # 4-4-2 pads the labeler
        ("00093-715-98", "00093071598"),  # 5-3-2 pads the product
        ("00093-7156-9", "00093715609"),  # 5-4-1 pads the package
        ("00093-7156-98", "00093715698"),  # already 5-4-2
        ("  00093715698 ", "00093715698"),
    ],
)
def test_normalizes_known_layouts(raw: str, expected: str) -> None:
    assert normalize_ndc(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", None, "123", "0093715698", "00093-7156", "00093-71a6-98", "1-2-3", "000937156980"],
)
def test_rejects_values_it_cannot_place(raw: str | None) -> None:
    # A bare 10-digit value could be any of three layouts, so it is rejected, not guessed.
    assert normalize_ndc(raw) is None
