import type { SiteContent } from "./siteContent";
export type SiteCard = { id: string; title: string; body: string };
export type SiteSection = SiteCard & { cards: SiteCard[] };
export type SiteLayout = {
  hidden: string[];
  removedCards: Record<string, number[]>;
  cards: Record<string, SiteCard[]>;
  sections: Record<string, SiteSection[]>;
};
export const emptyLayout = (): SiteLayout => ({ hidden: [], removedCards: {}, cards: {}, sections: {} });
export function getLayout(content: SiteContent): SiteLayout {
  try {
    return { ...emptyLayout(), ...JSON.parse(content.__layout?.en || "{}") };
  } catch {
    return emptyLayout();
  }
}
export function withLayout(content: SiteContent, layout: SiteLayout): SiteContent {
  const value = JSON.stringify(layout);
  return { ...content, __layout: { en: value, ar: value } };
}
