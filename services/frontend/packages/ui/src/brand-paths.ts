// Made by tools/draw_mark.py: don't edit, run the script (its docstring has the command).
// Centre lines of strokes (flat-ended; `round` is round-ended), drawn by <Logo /> and <LogoMark />.

export const MARK = { size: 64, radius: 15, stroke: 10, letter: "M16 37.5a10.5 10.5 0 1 0 21 0a10.5 10.5 0 1 0 -21 0M37 22L37 53", dot: { cx: 47, cy: 16.5, r: 6 } } as const;

export const LOGO = { width: 166.5, height: 48, markScale: 0.5625, stroke: 6, flat: "M48 24a9 9 0 1 0 18 0a9 9 0 1 0 -18 0M66 12L66 36M78 12L78 24M78 24a9 9 0 1 0 18 0a9 9 0 1 0 -18 0M107 12L107 24M107 24a9 9 0 1 0 18 0a9 9 0 1 0 -18 0", round: "M78 24L78 45M107 24L107 45M136 3L136 33M145.5 15L154.5 34M163.5 15L149.29 45" } as const;
