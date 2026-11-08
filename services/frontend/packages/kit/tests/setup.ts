// jsdom has no ResizeObserver, which every browser apply supports has. Radix measures some parts with it (a
// tooltip's arrow, for one), so tests get one that never reports a size change.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
