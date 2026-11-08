import type { NextConfig } from "next";

// /api/* is passed to the backend by src/proxy.ts, at request time (rewrites here would be fixed at build).

// Everything comes from apply itself: no third-party scripts, images, fonts or frames. Next.js's own inline
// scripts need 'unsafe-inline' (and dev's hot reload 'unsafe-eval'); untrusted markdown renders no HTML or images.
const dev = process.env.NODE_ENV !== "production";
const CSP = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self'${dev ? " ws:" : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",                     // the container image runs .next/standalone/apps/web/server.js
  outputFileTracingRoot: new URL("../..", import.meta.url).pathname,
  poweredByHeader: false,
  transpilePackages: ["@apply/api", "@apply/i18n", "@apply/kit", "@apply/ui"],
  // Markdown imported with `?raw` (the help guides, via import.meta.glob in src/help/guides.ts) arrives as a string.
  turbopack: { rules: { "*.md": { condition: { query: "?raw" }, type: "text" } } },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: CSP },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};

export default config;
