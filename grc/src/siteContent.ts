export type SiteContent = Record<string, { en: string; ar: string }>;
export function siteKey(en: string, ar: string) {
  let h = 2166136261;
  for (const c of en + "\0" + ar) {
    h ^= c.codePointAt(0)!;
    h = Math.imul(h, 16777619);
  }
  return "s" + (h >>> 0).toString(16).padStart(8, "0");
}
export function siteCopy(content: SiteContent, lang: "en" | "ar", en: string, ar: string, key?: string) {
  return content[key || siteKey(en, ar)]?.[lang] ?? (lang === "ar" ? ar : en);
}
