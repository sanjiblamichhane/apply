/**
 * The panel's theme: Match the system (the default), Light or Dark, as the web app's Appearance setting. The choice
 * is kept in chrome.storage.local (so every open panel follows it) and mirrored in localStorage, which can be read
 * before the first paint, so a dark panel never flashes light.
 */
export const THEMES = ["system", "light", "dark"] as const;
export type Theme = (typeof THEMES)[number];
export const THEME_KEY = "theme";

export const isTheme = (value: unknown): value is Theme => THEMES.includes(value as Theme);

/** Whether the page should be dark, for a choice and whether the system is dark. */
export const isDark = (theme: Theme, systemDark: boolean): boolean =>
  theme === "dark" || (theme === "system" && systemDark);

const system = () => window.matchMedia("(prefers-color-scheme: dark)");
let current: Theme = "system";

function paint(theme: Theme): void {
  current = theme;
  const dark = isDark(theme, system().matches);
  const root = document.documentElement;
  if (root.classList.contains("dark") === dark && root.style.colorScheme) return;
  // All at once: no control fades through the other theme's colours (as the web app's disableTransitionOnChange).
  const still = document.createElement("style");
  still.textContent = "*,*::before,*::after{transition:none!important}";
  document.head.appendChild(still);
  root.classList.toggle("dark", dark);
  root.style.colorScheme = dark ? "dark" : "light";
  void getComputedStyle(root).color; // apply the new colours before transitions come back
  requestAnimationFrame(() => still.remove());
}

/** Paint the saved theme now, and again whenever the choice or the system changes. */
export function followTheme(): void {
  const cached = localStorage.getItem(THEME_KEY);
  paint(isTheme(cached) ? cached : "system");
  system().addEventListener("change", () => paint(current));
  void chrome.storage.local.get(THEME_KEY).then((saved) => {
    const theme = isTheme(saved[THEME_KEY]) ? saved[THEME_KEY] : "system";
    localStorage.setItem(THEME_KEY, theme);
    paint(theme);
  });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local" || !(THEME_KEY in changes)) return;
    const next = changes[THEME_KEY].newValue;
    const theme = isTheme(next) ? next : "system";
    localStorage.setItem(THEME_KEY, theme);
    paint(theme);
  });
}

/** The saved choice. */
export async function savedTheme(): Promise<Theme> {
  const saved = await chrome.storage.local.get(THEME_KEY);
  return isTheme(saved[THEME_KEY]) ? saved[THEME_KEY] : "system";
}

/** Keep a choice: painted at once, here and in every other open panel. */
export function chooseTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  paint(theme);
  void chrome.storage.local.set({ [THEME_KEY]: theme });
}
