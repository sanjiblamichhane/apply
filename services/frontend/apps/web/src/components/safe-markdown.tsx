"use client";

import ReactMarkdown, { type Components } from "react-markdown";

/**
 * Markdown from outside (a pasted or fetched notice, or what a model wrote from one): no raw HTML (react-markdown
 * never renders it), and no images, which would load from wherever the text says and tell that server you
 * looked. An image shows as its description. Links open as links, without telling the site where you came from.
 */
const COMPONENTS: Components = {
  img: ({ alt }) => (alt ? <span>[{alt}]</span> : null),
  a: ({ href, children }) => <a href={href} rel="noopener noreferrer nofollow">{children}</a>,
};

/** ``components`` may swap the link (the guides open other guides in place); images stay off whatever is passed. */
export function SafeMarkdown({ children, components }: { children: string; components?: Pick<Components, "a"> }) {
  return <ReactMarkdown components={{ ...COMPONENTS, ...components, img: COMPONENTS.img }}>{children}</ReactMarkdown>;
}
