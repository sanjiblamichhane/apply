"""
Draws apply's mark and logo, and writes every file made from them.

The mark is drawn here as geometry, not taken from a font: a rounded tile in the theme's `--primary`, holding a
single-storey "a" (a ring and a stem) in `--primary-foreground`, with a dot lifting off to the upper right of
the stem. The logo is the mark followed by the word "apply" drawn in monoline strokes of a like
weight: flat where a stem meets a bowl, round at the free ends.
Everything is SVG paths and strokes, so nothing needs a font installed.

Source of truth: the numbers below and the two colour tokens in packages/ui/src/styles/tokens.css. This script
writes, from the repo's root:

- docs/brand/apply-logo.svg, apply-logo-dark.svg, apply-icon.svg (and a PNG of each);
- services/frontend/packages/ui/src/brand-paths.ts (what <Logo /> and <LogoMark /> draw);
- services/frontend/apps/web/src/app/icon.svg (the browser tab, in the dark colours when the browser is dark);
- services/frontend/apps/extension/src/icons/icon-{16,32,48,128}.png.

PNGs are rendered from the SVGs by cairosvg and carry the SHA-256 of the SVG they came from (a PNG text chunk),
so tools/tests/test_draw_mark.py can tell a stale PNG without rendering anything. Regenerate with:

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run --no-project --with cairosvg python tools/draw_mark.py
"""

from __future__ import annotations

import colorsys
import hashlib
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "services/frontend"
TOKENS = FRONTEND / "packages/ui/src/styles/tokens.css"
DOCS = ROOT / "docs/brand"
PATHS_TS = FRONTEND / "packages/ui/src/brand-paths.ts"
WEB_ICON = FRONTEND / "apps/web/src/app/icon.svg"
EXTENSION_ICONS = FRONTEND / "apps/extension/src/icons"
EXTENSION_SIZES = (16, 32, 48, 128)
STAMP = b"apply-source-sha256"


def n(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


# The mark, in a 64-unit tile.
TILE, TILE_RADIUS, MARK_STROKE = 64, 15, 10
RING_X, RING_Y, RING_R = 26.5, 37.5, 10.5  # the "a"'s bowl (centre line)
STEM_X = RING_X + RING_R  # flat-ended, flush with the bowl's top and bottom
STEM_TOP, STEM_FOOT = RING_Y - RING_R - MARK_STROKE / 2, RING_Y + RING_R + MARK_STROKE / 2
DOT_X, DOT_Y, DOT_R = 47, 16.5, 6


def ring(cx: float, cy: float, r: float) -> str:
    return f"M{n(cx - r)} {n(cy)}a{n(r)} {n(r)} 0 1 0 {n(2 * r)} 0a{n(r)} {n(r)} 0 1 0 {n(-2 * r)} 0"


def line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"M{n(x1)} {n(y1)}L{n(x2)} {n(y2)}"


MARK_LETTER = ring(RING_X, RING_Y, RING_R) + line(STEM_X, STEM_TOP, STEM_X, STEM_FOOT)

# The word, in logo units: x-height 12..36, ascender from 0, descender to 48. The tile is scaled to 36 (top to
# baseline), so the "l" stands exactly as tall as the mark.
WORD_STROKE = 6
HALF = WORD_STROKE / 2
TOP, X_TOP, BASE, FOOT = 0, 12, 36, 48
BOWL_R = (BASE - X_TOP - WORD_STROKE) / 2  # 9: outer radius 12
BOWL_Y = (X_TOP + BASE) / 2
MARK_SCALE = BASE / TILE
WORD_X = BASE + 9  # the gap after the tile


def word() -> tuple[str, str, float]:
    """The word's centre lines: flat-ended strokes (bowls, and stems where they meet a bowl), round-ended strokes
    (the free ends), and the right edge."""
    x, flat, parts = WORD_X, [], []
    # a: bowl, stem on its right
    cx = x + HALF + BOWL_R
    flat += [ring(cx, BOWL_Y, BOWL_R), line(cx + BOWL_R, X_TOP, cx + BOWL_R, BASE)]
    x = cx + BOWL_R + HALF + 6
    for _ in range(2):  # p: stem into the descender, bowl on its right
        stem = x + HALF
        flat += [line(stem, X_TOP, stem, BOWL_Y), ring(stem + BOWL_R, BOWL_Y, BOWL_R)]
        parts.append(line(stem, BOWL_Y, stem, FOOT - HALF))
        x = stem + 2 * BOWL_R + HALF + 5
    stem = x + HALF  # l
    parts.append(line(stem, TOP + HALF, stem, BASE - HALF))
    x = stem + HALF + 3.5
    left, right, vertex_y = x + HALF, x + HALF + 18, BASE - 2  # y: a V whose right arm runs on into the descender
    vertex_x = (left + right) / 2
    t = (FOOT - HALF - (X_TOP + HALF)) / (vertex_y - (X_TOP + HALF))
    tail_x = right + (vertex_x - right) * t
    parts += [line(left, X_TOP + HALF, vertex_x, vertex_y), line(right, X_TOP + HALF, tail_x, FOOT - HALF)]
    return "".join(flat), "".join(parts), right + HALF


WORD_FLAT, WORD_ROUND, LOGO_WIDTH = word()
LOGO_HEIGHT = FOOT


def token_hex(name: str, dark: bool) -> str:
    css = TOKENS.read_text(encoding="utf-8")
    split = css.index(".dark")
    block = css[split:] if dark else css[:split]
    found = re.search(rf"--{name}:\s*hsl\(([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\)", block)
    if not found:
        raise SystemExit(f"--{name} isn't an hsl() colour in {TOKENS}")
    h, s, l = (float(v) for v in found.groups())
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h / 360, l / 100, s / 100))


def palette(dark: bool) -> tuple[str, str]:
    """(tile and word, the "a" on the tile)."""
    return token_hex("primary", dark), token_hex("primary-foreground", dark)


def mark_group(brand: str, on_brand: str, transform: str = "") -> str:
    attrs = f' transform="{transform}"' if transform else ""
    return (
        f"  <g{attrs}>\n"
        f'    <rect width="{TILE}" height="{TILE}" rx="{TILE_RADIUS}" fill="{brand}"/>\n'
        f'    <path d="{MARK_LETTER}" fill="none" stroke="{on_brand}" stroke-width="{MARK_STROKE}"/>\n'
        f'    <circle cx="{n(DOT_X)}" cy="{n(DOT_Y)}" r="{n(DOT_R)}" fill="{on_brand}"/>\n'
        f"  </g>\n"
    )


def svg(width: float, height: float, body: str) -> str:
    w, h = n(width), n(height)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f"  <title>apply</title>\n{body}</svg>\n"
    )


def icon_svg() -> str:
    return svg(TILE, TILE, mark_group(*palette(dark=False)))


def web_icon_svg() -> str:
    """The icon, switching to the dark colours when the browser is dark (CSS outranks the attributes)."""
    brand, on_brand = palette(dark=True)
    style = (
        f"  <style>@media (prefers-color-scheme: dark) {{ rect {{ fill: {brand} }} path {{ stroke: {on_brand} }} "
        f"circle {{ fill: {on_brand} }} }}</style>\n"
    )
    return svg(TILE, TILE, style + mark_group(*palette(dark=False)))


def logo_svg(dark: bool) -> str:
    brand, on_brand = palette(dark)
    return svg(
        LOGO_WIDTH,
        LOGO_HEIGHT,
        mark_group(brand, on_brand, f"scale({MARK_SCALE:g})")
        + f'  <g fill="none" stroke="{brand}" stroke-width="{WORD_STROKE}">\n'
        f'    <path d="{WORD_FLAT}"/>\n'
        f'    <path d="{WORD_ROUND}" stroke-linecap="round" stroke-linejoin="round"/>\n'
        f"  </g>\n",
    )


def paths_ts() -> str:
    return (
        "// Made by tools/draw_mark.py: don't edit, run the script (its docstring has the command).\n"
        "// Centre lines of strokes (flat-ended; `round` is round-ended), drawn by <Logo /> and <LogoMark />.\n\n"
        f"export const MARK = {{ size: {TILE}, radius: {TILE_RADIUS}, stroke: {MARK_STROKE}, "
        f'letter: "{MARK_LETTER}", dot: {{ cx: {n(DOT_X)}, cy: {n(DOT_Y)}, r: {n(DOT_R)} }} }} as const;\n\n'
        f"export const LOGO = {{ width: {n(LOGO_WIDTH)}, height: {LOGO_HEIGHT}, markScale: {MARK_SCALE:g}, "
        f'stroke: {WORD_STROKE}, flat: "{WORD_FLAT}", round: "{WORD_ROUND}" }} as const;\n'
    )


def texts() -> dict[Path, str]:
    """Every text file the kit writes."""
    icon = icon_svg()
    return {
        DOCS / "apply-icon.svg": icon,
        DOCS / "apply-logo.svg": logo_svg(dark=False),
        DOCS / "apply-logo-dark.svg": logo_svg(dark=True),
        WEB_ICON: web_icon_svg(),
        PATHS_TS: paths_ts(),
    }


def pictures() -> dict[Path, tuple[str, int, int]]:
    """Every PNG the kit writes: (the SVG it's drawn from, width, height)."""
    logo_h = 360
    logo_w = round(LOGO_WIDTH * logo_h / LOGO_HEIGHT)
    return {
        DOCS / "apply-logo.png": (logo_svg(dark=False), logo_w, logo_h),
        DOCS / "apply-logo-dark.png": (logo_svg(dark=True), logo_w, logo_h),
        DOCS / "apply-icon-1024.png": (icon_svg(), 1024, 1024),
        **{EXTENSION_ICONS / f"icon-{s}.png": (icon_svg(), s, s) for s in EXTENSION_SIZES},
    }


def digest(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


def stamped(png: bytes, source: str) -> bytes:
    """The PNG with a tEXt chunk naming its source's hash, put just before IEND."""
    body = STAMP + b"\0" + digest(source).encode()
    chunk = struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", zlib.crc32(b"tEXt" + body))
    end = png.rindex(b"IEND") - 4
    return png[:end] + chunk + png[end:]


def write() -> None:
    import cairosvg

    for path, text in texts().items():
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))
    for path, (source, width, height) in pictures().items():
        png = cairosvg.svg2png(bytestring=source.encode(), output_width=width, output_height=height)
        path.write_bytes(stamped(png, source))
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    write()
