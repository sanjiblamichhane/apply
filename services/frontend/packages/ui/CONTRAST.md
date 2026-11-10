# Contrast (WCAG 2.2 AA)

Computed from `src/styles/tokens.css` by `scripts/contrast-report.mjs`; `tests/contrast.test.ts` fails below
the minimum. Text needs 4.5:1; component boundaries and focus indicators 3:1. Nothing is conveyed by colour
alone: every state also has text or an icon.

| Used for | Pair | Minimum | Light | Dark |
|---|---|---|---|---|
| body text | `foreground` on `background` | 4.5:1 | 15.55:1 pass | 15.41:1 pass |
| text on cards | `card-foreground` on `card` | 4.5:1 | 16.42:1 pass | 14.30:1 pass |
| menus and dialogs | `popover-foreground` on `popover` | 4.5:1 | 16.42:1 pass | 14.30:1 pass |
| text on muted surfaces, muted badges | `foreground` on `muted` | 4.5:1 | 13.70:1 pass | 12.67:1 pass |
| secondary text; a scroll bar's thumb | `muted-foreground` on `background` | 4.5:1 | 6.55:1 pass | 7.97:1 pass |
| secondary text on muted surfaces; a copy value's outline on hover; a switch's knob when off | `muted-foreground` on `muted` | 4.5:1 | 5.77:1 pass | 6.56:1 pass |
| secondary text on cards; the sidebar's scroll bar thumb | `muted-foreground` on `card` | 4.5:1 | 6.92:1 pass | 7.40:1 pass |
| secondary text in menus, dialogs and toasts | `muted-foreground` on `popover` | 4.5:1 | 6.92:1 pass | 7.40:1 pass |
| primary buttons; a switch's knob when on; the chosen theme in the extension's Settings | `primary-foreground` on `primary` | 4.5:1 | 5.48:1 pass | 9.33:1 pass |
| secondary buttons | `secondary-foreground` on `secondary` | 4.5:1 | 7.23:1 pass | 7.54:1 pass |
| highlighted menu items | `accent-foreground` on `accent` | 4.5:1 | 13.79:1 pass | 9.95:1 pass |
| destructive buttons | `destructive-foreground` on `destructive` | 4.5:1 | 5.42:1 pass | 6.36:1 pass |
| success badges | `success-foreground` on `success` | 4.5:1 | 6.00:1 pass | 10.25:1 pass |
| links; a switch's track when on | `primary` on `background` | 4.5:1 | 5.33:1 pass | 9.02:1 pass |
| links on cards; a switch's track when on (cards) | `primary` on `card` | 4.5:1 | 5.63:1 pass | 8.37:1 pass |
| error text | `destructive` on `background` | 4.5:1 | 5.27:1 pass | 6.14:1 pass |
| error text on cards | `destructive` on `card` | 4.5:1 | 5.57:1 pass | 5.70:1 pass |
| the underline marking a warning's words in their sentence | `destructive` on `muted` | 3:1 | 4.64:1 pass | 5.05:1 pass |
| success text | `success` on `background` | 4.5:1 | 5.84:1 pass | 9.91:1 pass |
| success text on cards | `success` on `card` | 4.5:1 | 6.17:1 pass | 9.19:1 pass |
| field borders; a switch's track when off; the extension's theme control | `input` on `background` | 3:1 | 3.71:1 pass | 4.09:1 pass |
| field borders on cards; a switch's track when off (cards) | `input` on `card` | 3:1 | 3.92:1 pass | 3.79:1 pass |
| focus ring | `ring` on `background` | 3:1 | 5.33:1 pass | 9.02:1 pass |
| focus ring on cards | `ring` on `card` | 3:1 | 5.63:1 pass | 8.37:1 pass |
| focus ring on muted tiles (the extension's copy values) | `ring` on `muted` | 3:1 | 4.70:1 pass | 7.42:1 pass |
| a copied value's ring and tick (the extension) | `primary` on `muted` | 3:1 | 4.70:1 pass | 7.42:1 pass |
| the chosen profile's tick in the extension's list | `primary` on `popover` | 3:1 | 5.63:1 pass | 8.37:1 pass |
| text on glass | `foreground` on glass (worst point) | 4.5:1 | 14.77:1 pass | 12.85:1 pass |
| secondary text on glass; field borders on glass | `muted-foreground` on glass (worst point) | 4.5:1 | 6.23:1 pass | 6.64:1 pass |
| links on glass | `primary` on glass (worst point) | 4.5:1 | 5.06:1 pass | 7.52:1 pass |
| error text on glass | `destructive` on glass (worst point) | 4.5:1 | 5.01:1 pass | 5.12:1 pass |
| focus ring on glass | `ring` on glass (worst point) | 3:1 | 5.06:1 pass | 7.52:1 pass |
