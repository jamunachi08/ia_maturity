/** Running total for the questionnaire. Mirrors ia_maturity.scoring.compute. */

export type ScoreBand = { level_name: string; level_name_ar?: string; min_score: number; color?: string };
export type ScoringPolicy = {
  points: Record<string, number>;
  max_points: number;
  weighting_method?: string;
  gating_enabled?: boolean;
  bands: ScoreBand[];
  sections?: { code: string; weight?: number }[];
};
export type ScoreAnswer = {
  section_code: string;
  selected_option?: string;
  selection_mode?: string;
  multi_score_method?: string;
  is_gating?: number | boolean;
  gate_trigger?: string;
  gate_cap_level?: string;
};

const LETTERS = ["A", "B", "C", "D"] as const;

/** Python 3 round(value, 1): half rounds to even. */
function round1(value: number) {
  const sign = value < 0 ? -1 : 1;
  const scaled = Math.abs(value) * 10;
  const base = Math.floor(scaled + 1e-9);
  const frac = scaled - base;
  const digit = Math.abs(frac - 0.5) < 1e-8 ? (base % 2 === 0 ? base : base + 1) : Math.round(scaled);
  return (sign * digit) / 10;
}

function bandFor(pct: number, bands: ScoreBand[]) {
  let chosen = bands[0];
  for (const band of bands) if (pct + 1e-9 >= Number(band.min_score)) chosen = band;
  return chosen;
}

function bandIndex(level: string, bands: ScoreBand[]) {
  const name = level.trim().toLowerCase();
  return bands.findIndex((band) => (band.level_name || "").trim().toLowerCase() === name);
}

export function parseSelected(raw?: string): { kind: "" | "N/A" | "letters" | "invalid"; letters: string[] } {
  const text = (raw || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!text) return { kind: "", letters: [] };
  if (text === "N/A" || text === "NA" || text === "N.A." || text === "N.A")
    return { kind: "N/A", letters: [] };
  const parts = text.replace(/;/g, ",").split(",").filter(Boolean);
  const letters: string[] = [];
  const seen = new Set<string>();
  for (const part of parts) {
    if (!(LETTERS as readonly string[]).includes(part)) return { kind: "invalid", letters: [] };
    if (!seen.has(part)) {
      seen.add(part);
      letters.push(part);
    }
  }
  letters.sort(
    (a, b) => LETTERS.indexOf(a as (typeof LETTERS)[number]) - LETTERS.indexOf(b as (typeof LETTERS)[number]),
  );
  return letters.length ? { kind: "letters", letters } : { kind: "", letters: [] };
}

export function answerPoints(answer: ScoreAnswer, points: Record<string, number>, maxPoints: number) {
  const { kind, letters } = parseSelected(answer.selected_option);
  if (kind !== "letters" || !letters.length) return 0;
  const values = letters.map((letter) => Number(points[letter] ?? 0));
  const multi = (answer.selection_mode || "Single") === "Multi";
  if (!multi || values.length === 1) return values[0];
  const method = (answer.multi_score_method || "Highest").trim();
  if (method === "Average") return values.reduce((a, b) => a + b, 0) / values.length;
  if (method === "Sum (capped)")
    return Math.min(
      values.reduce((a, b) => a + b, 0),
      maxPoints,
    );
  return Math.max(...values);
}

function worstLetter(answer: ScoreAnswer) {
  const { kind, letters } = parseSelected(answer.selected_option);
  if (kind !== "letters" || !letters.length) return "";
  return letters.reduce((worst, letter) =>
    LETTERS.indexOf(letter as (typeof LETTERS)[number]) < LETTERS.indexOf(worst as (typeof LETTERS)[number])
      ? letter
      : worst,
  );
}

export function liveOverall(questions: ScoreAnswer[], policy: ScoringPolicy) {
  const points = policy.points || {};
  const maxPt = Number(policy.max_points) || Math.max(...Object.values(points), 0);
  const bands = [...(policy.bands || [])].sort((a, b) => Number(a.min_score) - Number(b.min_score));
  const sections = new Map(
    (policy.sections || []).map((section) => [
      section.code,
      {
        points: 0,
        max: 0,
        weight: section.weight == null ? 1 : Number(section.weight),
      },
    ]),
  );
  let totalPts = 0,
    totalMax = 0;
  const gates: string[] = [];
  for (const question of questions) {
    const { kind } = parseSelected(question.selected_option);
    const section = sections.get(question.section_code);
    if (!kind || kind === "invalid") {
      if (section) section.max += maxPt;
      totalMax += maxPt;
      continue;
    }
    if (kind === "N/A") continue;
    const earned = answerPoints(question, points, maxPt);
    totalPts += earned;
    totalMax += maxPt;
    if (section) {
      section.points += earned;
      section.max += maxPt;
    }
    const worst = worstLetter(question);
    const letters = (question.gate_trigger || "A").trim() === "A or B" ? ["A", "B"] : ["A"];
    if (
      policy.gating_enabled !== false &&
      question.is_gating &&
      worst &&
      letters.includes(worst) &&
      question.gate_cap_level
    )
      gates.push(question.gate_cap_level);
  }
  let pct = totalMax ? round1((totalPts / totalMax) * 100) : 0;
  if ((policy.weighting_method || "").startsWith("Section")) {
    const scored = [...sections.values()].filter((section) => section.max && section.weight > 0);
    const weight = scored.reduce((sum, section) => sum + section.weight, 0);
    pct = weight
      ? round1(
          scored.reduce(
            (sum, section) => sum + round1((section.points / section.max) * 100) * section.weight,
            0,
          ) / weight,
        )
      : 0;
  }
  let band = bands.length ? bandFor(pct, bands) : undefined;
  if (band && gates.length) {
    const scoreIdx = bandIndex(band.level_name, bands);
    let capIdx = -1;
    for (const level of gates) {
      const idx = bandIndex(level, bands);
      if (idx >= 0 && (capIdx < 0 || idx < capIdx)) capIdx = idx;
    }
    if (capIdx >= 0 && scoreIdx > capIdx) band = bands[capIdx];
  }
  return { pct, band };
}
