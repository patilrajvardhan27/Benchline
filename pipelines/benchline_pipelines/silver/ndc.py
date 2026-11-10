"""NDC normalization to the 11-digit 5-4-2 form used everywhere else."""

from __future__ import annotations

# Segment lengths (labeler, product, package) of the three 10-digit layouts.
_PADDING = {
    (4, 4, 2): (0, 5),  # pad the labeler
    (5, 3, 2): (1, 4),  # pad the product
    (5, 4, 1): (2, 2),  # pad the package
}


def normalize_ndc(raw: str | None) -> str | None:
    """Return the 11-digit NDC, or None if the value cannot be normalized safely.

    A 10-digit NDC without hyphens is ambiguous (three layouts are possible),
    so it is rejected rather than guessed.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if "-" not in text:
        return text if text.isdigit() and len(text) == 11 else None

    parts = text.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    lengths = (len(parts[0]), len(parts[1]), len(parts[2]))
    if lengths == (5, 4, 2):
        return "".join(parts)
    pad = _PADDING.get(lengths)
    if pad is None:
        return None
    index, width = pad
    parts[index] = parts[index].zfill(width)
    return "".join(parts)
