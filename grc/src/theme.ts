import type { CSSProperties } from "react";

/** Colours of a portal theme, as sent by the server (GRC Theme). */
export type ThemeTokens = {
  name?: string;
  primary: string;
  primary_dark: string;
  accent: string;
  ink: string;
  muted: string;
  background: string;
  surface: string;
  border: string;
};

const STORAGE_KEY = "grc-theme";
const HEX = /^#[0-9a-f]{6}$/i;

/** CSS custom properties for a theme. Every brand shade in the stylesheets derives from these. */
export function themeVariables(theme: ThemeTokens): Record<string, string> {
  const vars: Record<string, string> = {
    "--brand": theme.primary,
    "--brand-dark": theme.primary_dark,
    "--accent": theme.accent,
    "--ink": theme.ink,
    "--muted": theme.muted,
    "--page-bg": theme.background,
    "--surface": theme.surface,
    "--border": theme.border,
  };
  // Never apply a malformed colour: the stylesheet defaults stay in place instead.
  return Object.fromEntries(Object.entries(vars).filter(([, value]) => HEX.test(value || "")));
}

/** Inline style that scopes a theme to one element, for previews. */
export function themeStyle(theme: ThemeTokens): CSSProperties {
  return themeVariables(theme) as CSSProperties;
}

/** Apply a theme to the whole document and remember it for the next first paint. */
export function applyTheme(theme?: ThemeTokens | null) {
  if (!theme) return;
  const root = document.documentElement;
  for (const [name, value] of Object.entries(themeVariables(theme))) root.style.setProperty(name, value);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(theme));
  } catch {
    // Storage can be unavailable (private mode, embedded views); the server theme still applies.
  }
}

/** Apply the last known theme before React renders, avoiding a flash of default colours. */
export function applyStoredTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) applyTheme(JSON.parse(stored) as ThemeTokens);
  } catch {
    // Ignore unreadable storage; the bootstrap response applies the theme moments later.
  }
}
