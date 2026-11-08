/**
 * The text of each globbed guide file. The glob hands back whole modules, and each file's text is read from the
 * module's default export here: the glob's own `import: "default"` option comes back empty in production builds,
 * where the bundler renames exports.
 */
export function texts(modules: Record<string, { default: string }>): Record<string, string> {
  return Object.fromEntries(Object.entries(modules).map(([path, module]) => [path, module.default]));
}
