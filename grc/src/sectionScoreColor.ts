import defaults from "../../ia_maturity/public/section-color-ranges.json" with { type: "json" };
export type ColorRange = { min_score: number; color: string };
export const defaultColorRanges: ColorRange[] = defaults;
export function sectionScoreColor(score: number, ranges: ColorRange[] = defaults): string {
  return (
    [...ranges].sort((a, b) => b.min_score - a.min_score).find((row) => score >= row.min_score)?.color ||
    defaults[0].color
  );
}
