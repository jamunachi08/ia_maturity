import AssessmentDisclosure from "./AssessmentDisclosure";
import { useLanguage } from "./i18n";
import { liveOverall, parseSelected } from "./liveScore";
import { sectionScoreColor } from "./sectionScoreColor";
import type { Assessment, Question } from "./types";
export default function MaturityPanel({ doc, questions }: { doc: Assessment; questions: Question[] }) {
  const { t, lang } = useLanguage();
  const mode = doc.overall_maturity_visibility || "Hidden";
  if (!["After assessment completion", "Completed sections only"].includes(mode)) return null;
  const attempted = (q: Question) => ["letters", "N/A"].includes(parseSelected(q.selected_option).kind);
  const codes = [...new Set(questions.map((q) => q.section_code))];
  const completed = codes.filter((code) => questions.filter((q) => q.section_code === code).every(attempted));
  const complete = questions.length > 0 && questions.every(attempted);
  const sectionOnly = mode === "Completed sections only";
  if ((!sectionOnly && !complete) || (sectionOnly && !completed.length)) return null;
  const canCompute = !!doc.editable && !!doc.scoring;
  if (!canCompute && !doc.results_visible) return null;
  const visibleCodes = sectionOnly ? completed : codes;
  const rows = visibleCodes.map((code) => {
    const qs = questions.filter((q) => q.section_code === code),
      stored = doc.section_scores?.find((s) => s.section_code === code);
    const meta = doc.sections?.find((s) => s.code === code);
    const title =
      (lang === "ar" ? meta?.title_ar || qs[0]?.section_title_ar : meta?.title) ||
      qs[0]?.section_title ||
      stored?.section_title ||
      code;
    const applicable = qs.some((q) => parseSelected(q.selected_option).kind === "letters");
    const score = canCompute
      ? liveOverall(qs, { ...doc.scoring!, sections: doc.scoring!.sections?.filter((s) => s.code === code) })
          .pct
      : stored?.score_pct;
    return { code, title, score, applicable };
  });
  const overallApplicable = questions.some((q) => parseSelected(q.selected_option).kind === "letters");
  const overall = canCompute ? liveOverall(questions, doc.scoring!) : null;
  return (
    <AssessmentDisclosure
      title={sectionOnly ? "Completed section scores" : "Overall Maturity"}
      className="maturity-disclosure"
      open
    >
      <section className="scorecard">
        {!sectionOnly && (
          <div className="score-summary">
            <span className="eyebrow">{t("Overall maturity")}</span>
            <div className="score-value">
              {overallApplicable ? (overall?.pct ?? doc.overall_score) : t("Not applicable")}
              {overallApplicable && <span>%</span>}
            </div>
            {overallApplicable && (
              <h2>
                {overall?.band
                  ? lang === "ar"
                    ? overall.band.level_name_ar || overall.band.level_name
                    : overall.band.level_name
                  : doc.maturity_level}
              </h2>
            )}
            <span className={"report-label " + (doc.released ? "released" : "")}>
              {t(doc.released ? "Approved report" : "Preliminary — not reviewed or approved")}
            </span>
          </div>
        )}
        <div className="score-sections" style={sectionOnly ? { gridColumn: "1 / -1" } : undefined}>
          <h3>{t(sectionOnly ? "Completed section scores" : "Section scores")}</h3>
          {rows.map((row) => (
            <div className="score-row" key={row.code}>
              <div>
                <span>{row.title}</span>
                <strong>
                  {row.applicable && row.score !== undefined ? row.score + "%" : t("Not applicable")}
                </strong>
              </div>
              {row.applicable && row.score !== undefined && (
                <div className="progress-track">
                  <span
                    style={{
                      width: row.score + "%",
                      background: sectionScoreColor(row.score, doc.section_color_ranges),
                    }}
                  />
                </div>
              )}
            </div>
          ))}
          {!sectionOnly && doc.gating_note && <p className="muted">{doc.gating_note}</p>}
          <small>{t("This assessment measures maturity; it does not certify regulatory compliance.")}</small>
        </div>
      </section>
    </AssessmentDisclosure>
  );
}
