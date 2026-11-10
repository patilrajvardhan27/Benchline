"""Handwriting font: measure text for wrapping, and embed a small subset in each SVG."""

from __future__ import annotations

import io
from base64 import b64encode
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).parent / "fonts"
WEIGHTS = (500, 700)


class Handwriting:
    def __init__(self) -> None:
        self._fonts = {w: TTFont(FONT_DIR / f"caveat-latin-{w}-normal.woff") for w in WEIGHTS}

    def width(self, text: str, size: float, weight: int = 500) -> float:
        font = self._fonts[weight]
        cmap, hmtx = font.getBestCmap(), font["hmtx"]
        per_em = font["head"].unitsPerEm
        return sum(hmtx[cmap.get(ord(ch), cmap[ord("?")])][0] for ch in text) * size / per_em

    def wrap(self, text: str, size: float, max_width: float, weight: int = 500) -> list[str]:
        """Greedy word wrap. Explicit newlines start a new paragraph."""
        lines: list[str] = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                trial = f"{current} {word}".strip()
                if current and self.width(trial, size, weight) > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = trial
            lines.append(current)
        return lines

    def face_css(self, used: dict[int, set[str]]) -> str:
        """@font-face rules with only the glyphs each weight needs, inline, so the SVG is self-contained."""
        rules = []
        for weight, chars in sorted(used.items()):
            options = subset.Options()
            options.flavor = "woff"
            options.layout_features = ["*"]
            font = TTFont(FONT_DIR / f"caveat-latin-{weight}-normal.woff")
            subsetter = subset.Subsetter(options)
            subsetter.populate(text="".join(sorted(chars | {"?"})))
            subsetter.subset(font)
            buffer = io.BytesIO()
            font.flavor = "woff"
            font.save(buffer)
            data = b64encode(buffer.getvalue()).decode()
            rules.append(
                "@font-face{font-family:'Caveat';font-weight:%d;"
                "src:url(data:font/woff;base64,%s) format('woff');}" % (weight, data)
            )
        return "".join(rules)
