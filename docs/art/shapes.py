"""Hand-drawn looking SVG building blocks. Wobble is seeded, so output is reproducible."""

from __future__ import annotations

import random
from xml.sax.saxutils import escape

from font import Handwriting

INK, MUTED = "#28292b", "#5c5e63"
TEAL, TEAL_DARK, TEAL_PALE = "#018380", "#016b68", "#dcefee"
EMBER, EMBER_DARK, EMBER_PALE = "#ff4e00", "#b83800", "#fbe9e1"
PAPER, LINE = "#fcfbf8", "#d9d6cf"

FONT = Handwriting()


def _jitter(rng: random.Random, amount: float) -> float:
    return rng.uniform(-amount, amount)


class Canvas:
    def __init__(self, width: int, height: int, title: str, description: str, seed: int = 1) -> None:
        self.w, self.h, self.title, self.description = width, height, title, description
        self.rng = random.Random(seed)
        self.parts: list[str] = []
        self.used: dict[int, set[str]] = {}

    # --- shapes ---------------------------------------------------------------
    def rect(self, x: float, y: float, w: float, h: float, fill: str = "none", stroke: str = INK,
             width: float = 3, wobble: float = 2.2) -> None:
        r = self.rng
        pts = [(x + _jitter(r, wobble), y + _jitter(r, wobble)), (x + w + _jitter(r, wobble), y + _jitter(r, wobble)),
               (x + w + _jitter(r, wobble), y + h + _jitter(r, wobble)), (x + _jitter(r, wobble), y + h + _jitter(r, wobble))]
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} " + " ".join(f"L{px:.1f},{py:.1f}" for px, py in pts[1:] + [pts[0]])
        # a second, slightly different pass is what makes it look pen-drawn
        q = [(px + _jitter(r, 1.5), py + _jitter(r, 1.5)) for px, py in pts]
        d2 = f"M{q[0][0]:.1f},{q[0][1]:.1f} " + " ".join(f"L{px:.1f},{py:.1f}" for px, py in q[1:] + [q[0]])
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" '
                          'stroke-linejoin="round" stroke-linecap="round"/>')
        self.parts.append(f'<path d="{d2}" fill="none" stroke="{stroke}" stroke-width="{width * 0.5}" '
                          'stroke-linejoin="round" stroke-linecap="round" opacity="0.6"/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, stroke: str = INK, width: float = 3,
             dash: str = "") -> None:
        mx, my = (x1 + x2) / 2 + _jitter(self.rng, 4), (y1 + y2) / 2 + _jitter(self.rng, 4)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="M{x1:.1f},{y1:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}" fill="none" '
                          f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"{extra}/>')

    def arrow(self, x1: float, y1: float, x2: float, y2: float, stroke: str = INK, width: float = 3.5) -> None:
        self.line(x1, y1, x2, y2, stroke, width)
        dx, dy = x2 - x1, y2 - y1
        length = max((dx * dx + dy * dy) ** 0.5, 1)
        ux, uy = dx / length, dy / length
        for sign in (1, -1):
            hx = x2 - 18 * ux + sign * 10 * -uy
            hy = y2 - 18 * uy + sign * 10 * ux
            self.line(x2, y2, hx, hy, stroke, width)

    def check(self, x: float, y: float, size: float = 34, stroke: str = TEAL_DARK) -> None:
        self.parts.append(f'<path d="M{x:.1f},{y + size * 0.55:.1f} L{x + size * 0.35:.1f},{y + size * 0.9:.1f} '
                          f'L{x + size:.1f},{y:.1f}" fill="none" stroke="{stroke}" stroke-width="6" '
                          'stroke-linecap="round" stroke-linejoin="round"/>')

    def underline(self, x: float, y: float, w: float, stroke: str = EMBER) -> None:
        self.line(x, y, x + w, y + _jitter(self.rng, 5), stroke, 5)
        self.line(x + 12, y + 9, x + w - 14, y + 9 + _jitter(self.rng, 4), stroke, 3)

    def circle(self, cx: float, cy: float, r: float, fill: str = "none", stroke: str = INK, width: float = 3) -> None:
        self.parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{r + _jitter(self.rng, 1.5):.1f}" '
                          f'ry="{r + _jitter(self.rng, 1.5):.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    # --- text -----------------------------------------------------------------
    def text(self, x: float, y: float, content: str, size: float = 30, fill: str = INK, weight: int = 500,
             anchor: str = "start") -> None:
        self.used.setdefault(weight, set()).update(content)
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                          f'text-anchor="{anchor}">{escape(content)}</text>')

    def paragraph(self, x: float, y: float, content: str, max_width: float, size: float = 28, fill: str = INK,
                  weight: int = 500, anchor: str = "start", leading: float = 1.15) -> float:
        """Wrapped text. Returns the y just below the last line."""
        cursor = y
        for line in FONT.wrap(content, size, max_width, weight):
            tx = {"middle": x + max_width / 2, "end": x + max_width}.get(anchor, x)
            self.text(tx, cursor, line, size, fill, weight, anchor)
            cursor += size * leading
        return cursor

    def box(self, x: float, y: float, w: float, h: float, title: str, body: str = "", fill: str = TEAL_PALE,
            stroke: str = TEAL_DARK, title_size: float = 34, body_size: float = 25) -> None:
        self.rect(x, y, w, h, fill, stroke)
        self.text(x + w / 2, y + 44, title, title_size, stroke, 700, "middle")
        if body:
            self.paragraph(x + 14, y + 44 + body_size + 8, body, w - 28, body_size, INK, 500, "middle")

    # --- output ---------------------------------------------------------------
    def svg(self, border: bool = True) -> str:
        if border:
            self.rect(6, 6, self.w - 12, self.h - 12, "none", LINE, 3, 3)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
                f'<title id="t">{escape(self.title)}</title><desc id="d">{escape(self.description)}</desc>'
                f'<style>{FONT.face_css(self.used)}text{{font-family:Caveat,"Comic Sans MS","Bradley Hand",cursive}}</style>'
                f'<rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>' + "".join(self.parts) + "</svg>\n")
