import { describe, expect, it } from "vitest";

import { fitBand, lines } from "@/lib/discovery";

describe("discovery helpers", () => {
  it("says a fit in words as well as a number", () => {
    expect(fitBand(92)).toBe("strong");
    expect(fitBand(75)).toBe("strong");
    expect(fitBand(60)).toBe("fair");
    expect(fitBand(10)).toBe("weak");
  });
  it("reads one item per line", () => {
    expect(lines(" python \n\nDjango\n")).toEqual(["python", "Django"]);
  });
});

describe("the search form per pack", () => {
  it("offers only what the pack's searches use, and Auto only where it can send", async () => {
    const { searchOptionsFor } = await import("@/lib/discovery");
    expect(searchOptionsFor({ search_options: ["locations", "needs_sponsorship", "remote_only"], auto: true }))
      .toEqual({ locations: true, remoteOnly: true, needsSponsorship: true, auto: true });
    expect(searchOptionsFor({ search_options: ["locations"], auto: false }))
      .toEqual({ locations: true, remoteOnly: false, needsSponsorship: false, auto: false });
    expect(searchOptionsFor(undefined)).toEqual({ locations: false, remoteOnly: false, needsSponsorship: false, auto: false });
  });
});
