import { describe, expect, it } from "vitest";

import { buttonVariants } from "../src/components/button";

describe("hit targets", () => {
  it("every button size is at least 44 px (min-h-11 / size-11 or larger)", () => {
    for (const size of ["default", "sm", "lg", "icon"] as const) {
      const classes = buttonVariants({ size });
      expect(classes, size).toMatch(/\b(min-h-1[1-9]|size-1[1-9]|min-h-12)\b/);
    }
  });
});
