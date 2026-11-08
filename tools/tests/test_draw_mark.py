"""
The committed brand files are what tools/draw_mark.py makes from its geometry and the theme's tokens, and the
mark's colours keep their contrast. No rendering here: a PNG names the hash of the SVG it was drawn from. Run by
tests/check.sh:

    uv run --no-project --with pytest pytest tools/tests -q -p no:cacheprovider
"""

import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import draw_mark as kit  # noqa: E402

RERUN = "run tools/draw_mark.py (its docstring has the command)"


def png_info(path: Path) -> tuple[tuple[int, int], dict[bytes, bytes]]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} isn't a PNG"
    size, notes, at = (0, 0), {}, 8
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        if kind == b"IHDR":
            size = struct.unpack(">II", body[:8])
        elif kind == b"tEXt":
            key, _, value = body.partition(b"\0")
            notes[key] = value
        at += 12 + length
    return size, notes


def luminance(colour: str) -> float:
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(int(colour[i : i + 2], 16) / 255) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_text_files_are_current():
    for path, text in kit.texts().items():
        assert path.read_text(encoding="utf-8") == text, f"{path.relative_to(kit.ROOT)} is stale: {RERUN}"


def test_pngs_are_drawn_from_the_current_svgs():
    for path, (source, width, height) in kit.pictures().items():
        size, notes = png_info(path)
        name = path.relative_to(kit.ROOT)
        assert size == (width, height), f"{name} is {size}, not {(width, height)}: {RERUN}"
        assert notes.get(kit.STAMP) == kit.digest(source).encode(), f"{name} is stale: {RERUN}"


def test_the_apps_draw_what_the_svgs_show():
    ts = kit.PATHS_TS.read_text(encoding="utf-8")
    paths = dict(re.findall(r'(\w+): "([^"]+)"', ts))
    icon = (kit.DOCS / "apply-icon.svg").read_text(encoding="utf-8")
    assert f'd="{paths["letter"]}"' in icon
    for logo in ("apply-logo.svg", "apply-logo-dark.svg"):
        svg = (kit.DOCS / logo).read_text(encoding="utf-8")
        assert f'd="{paths["flat"]}"' in svg and f'd="{paths["round"]}"' in svg and f'd="{paths["letter"]}"' in svg
    web = kit.WEB_ICON.read_text(encoding="utf-8")
    assert f'd="{paths["letter"]}"' in web and "prefers-color-scheme: dark" in web


def test_every_file_is_named_and_outlined():
    for path, text in kit.texts().items():
        if path.suffix == ".svg":
            assert "<title>apply</title>" in text and "<text" not in text, path


def test_the_mark_holds_its_contrast_in_both_themes():
    # The mark and word are graphics: WCAG 2.2 AA asks 3:1 of them against what they sit on. The "a" on the tile
    # is held to the text bar (4.5:1), as primary-foreground on primary is everywhere else.
    for dark in (False, True):
        brand, on_brand = kit.palette(dark)
        ground = kit.token_hex("background", dark)
        card = kit.token_hex("card", dark)
        assert ratio(on_brand, brand) >= 4.5, (dark, on_brand, brand)
        assert ratio(brand, ground) >= 3 and ratio(brand, card) >= 3, (dark, brand, ground, card)
    # The extension's and the store's PNGs are the light colours on whatever the browser's chrome is: the tile
    # holds 3:1 on white and on the dark theme's ground, and the light "a" holds it on any dark chrome.
    tile, letter = kit.palette(dark=False)
    assert ratio(tile, "#ffffff") >= 3 and ratio(tile, kit.token_hex("background", True)) >= 3
    assert ratio(letter, "#3c4043") >= 3

