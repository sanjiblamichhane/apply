/**
 * apply's mark and logo, drawn from the strokes tools/draw_mark.py writes to brand-paths.ts (no font needed).
 * The mark is a rounded tile in `primary` holding an "a" and a dot in `primary-foreground`; the logo is the mark
 * followed by the word "apply" in `primary`. Both follow the theme, and both pairs are in lib/contrast.ts
 * (primary-foreground on primary, primary on background and card).
 *
 * `title` (usually "apply") makes either one an image with that name. Without it the graphic is hidden from
 * screen readers, for when words beside it already say the name.
 */
import { LOGO, MARK } from "../brand-paths";
import { cn } from "../lib/utils";

interface BrandProps {
  title?: string;
  className?: string;
}

function a11y(title?: string) {
  return title ? { role: "img" as const, "aria-label": title } : { "aria-hidden": true as const };
}

/** The tile, its "a" and the dot, in the mark's 64-unit square (the tile takes currentColor). */
function MarkShapes({ transform }: { transform?: string }) {
  return (
    <g transform={transform}>
      <rect width={MARK.size} height={MARK.size} rx={MARK.radius} fill="currentColor" />
      <path d={MARK.letter} fill="none" stroke="var(--primary-foreground)" strokeWidth={MARK.stroke} />
      <circle cx={MARK.dot.cx} cy={MARK.dot.cy} r={MARK.dot.r} fill="var(--primary-foreground)" />
    </g>
  );
}

/** The mark and the word "apply": 36 px tall by default, sized with a height class. */
export function Logo({ title, className }: BrandProps) {
  return (
    <svg viewBox={`0 0 ${LOGO.width} ${LOGO.height}`} width={LOGO.width} height={LOGO.height} {...a11y(title)}
      className={cn("h-9 w-auto shrink-0 text-primary", className)}>
      <MarkShapes transform={`scale(${LOGO.markScale})`} />
      <g fill="none" stroke="currentColor" strokeWidth={LOGO.stroke}>
        <path d={LOGO.flat} />
        <path d={LOGO.round} strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

/** The mark alone, for where the whole logo doesn't fit (a collapsed sidebar). */
export function LogoMark({ title, className }: BrandProps) {
  return (
    <svg viewBox={`0 0 ${MARK.size} ${MARK.size}`} width={MARK.size} height={MARK.size} {...a11y(title)}
      className={cn("size-7 shrink-0 text-primary", className)}>
      <MarkShapes />
    </svg>
  );
}
