# apply's logo and icon

- **The mark** is a rounded tile in the theme's cyan (`--primary`: a deep shade of #0DC8DB in light, #0DC8DB
  itself in dark). On it sits a lowercase "a", a ring with a flat-ended stem, and a dot lifting off to the upper
  right of the stem: the step forward you take when you apply. The "a" and the dot are the tile's foreground
  colour (`--primary-foreground`).
- **The logo** is the mark followed by the word "apply" in the same cyan, drawn in even, monoline strokes:
  flat where a stem meets a bowl, round at the free ends. The "l" stands as tall as the tile.
- **The icon** is the mark alone. It reads at 16 px.

| File | Use |
|---|---|
| [apply-logo.svg](apply-logo.svg), [.png](apply-logo.png) | The logo for light grounds (the PNG is 1249 × 360, transparent) |
| [apply-logo-dark.svg](apply-logo-dark.svg), [.png](apply-logo-dark.png) | The logo for dark grounds |
| [apply-icon.svg](apply-icon.svg), [apply-icon-1024.png](apply-icon-1024.png) | The app icon (1024 × 1024 for a store listing) |

For a slide, a printer or a partner's site, use these files, never a screenshot. They are paths, not text, so
they look the same everywhere and need no font.

In the apps, `<Logo />` and `<LogoMark />` (`@apply/ui`) draw the same shapes in the theme's colours: in the
sidebar, on the sign-in pages and on the extension's connect screen. The browser tab uses
`apps/web/src/app/icon.svg` (it switches to the dark colours when the browser is dark), and the browser's
toolbar uses the extension's `src/icons`.

`tools/draw_mark.py` makes all of them from a few numbers and the theme's tokens. Run it after changing either:
its docstring has the command. `tools/tests/test_draw_mark.py`, part of tests/check.sh, fails while any file
differs from what the script would write.

**Contrast** (WCAG 2.2 AA asks 3:1 of graphics; the "a" on the tile is held to 4.5:1):

| | Light | Dark |
|---|---|---|
| Tile on the page (`--background`) | 5.4:1 | 9.0:1 |
| Tile on a card (`--card`) | 5.7:1 | 8.3:1 |
| "a" and dot on the tile | 5.5:1 | 9.3:1 |

The PNG icons keep the light colours on any browser chrome: the tile is 5.7:1 on white and 3.2:1 on the dark
theme's ground, and the light "a" is over 10:1 on dark chrome. Leave clear space around the logo of at least half
the tile's height. Never recolour it, except to the dark version on dark grounds.
