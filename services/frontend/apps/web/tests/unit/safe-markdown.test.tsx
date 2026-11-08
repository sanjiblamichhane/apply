import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SafeMarkdown } from "@/components/safe-markdown";

afterEach(cleanup);

describe("markdown from outside (security review)", () => {
  it("loads no images: a tracking pixel shows as its description", () => {
    const { container } = render(<SafeMarkdown>{"Hello ![logo](https://tracker.example/p.png?id=1)"}</SafeMarkdown>);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("[logo]");
    expect(container.innerHTML).not.toContain("tracker.example");
  });

  it("renders no raw HTML or script links, and links don't send a referrer", () => {
    const { container } = render(
      <SafeMarkdown>{'<img src="https://x.example/a.png" onerror="alert(1)"> [ok](https://example.com) [bad](javascript:alert(1))'}</SafeMarkdown>,
    );
    expect(container.querySelector("img")).toBeNull();
    const links = [...container.querySelectorAll("a")];
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["https://example.com", ""]);
    expect(links[0]!.getAttribute("rel")).toBe("noopener noreferrer nofollow");
  });
});
