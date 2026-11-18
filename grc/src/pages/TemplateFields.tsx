import Select from "../Select";
import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import { useLanguage } from "../i18n";
import { Button, Field } from "../components";

const inheritOptions = [
  { value: "", label: "Inherit" },
  { value: "Enabled", label: "Enabled" },
  { value: "Disabled", label: "Disabled" },
];

export type TemplateSection = {
  section_code: string;
  section_title?: string;
  section_title_ar?: string;
  weight?: number;
  allow_comment?: string;
  allow_attachment?: string;
  reference?: string;
  reference_ar?: string;
};
export type TemplateQuestion = {
  question_code: string;
  section_code: string;
  short_label?: string;
  question_text?: string;
  question_text_ar?: string;
  guidance?: string;
  guidance_ar?: string;
  option_a?: string;
  option_b?: string;
  option_c?: string;
  option_d?: string;
  option_a_ar?: string;
  option_b_ar?: string;
  option_c_ar?: string;
  option_d_ar?: string;
  selection_mode?: string;
  multi_score_method?: string;
  allow_na?: number;
  is_gating?: number;
  gate_trigger?: string;
  gate_cap_level?: string;
  auto_source?: string;
  allow_comment?: string;
  allow_attachment?: string;
  [key: string]: any;
};

function InheritSelect({
  value,
  onChange,
  label,
  disabled,
}: {
  value?: string;
  onChange: (v: string) => void;
  label: string;
  disabled?: boolean;
}) {
  const { t } = useLanguage();
  return (
    <Field label={label}>
      <Select value={value || ""} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        {inheritOptions.map((o) => (
          <option key={o.value || "inherit"} value={o.value}>
            {t(o.label)}
          </option>
        ))}
      </Select>
    </Field>
  );
}

function move<T>(rows: T[], from: number, to: number) {
  if (to < 0 || to >= rows.length) return rows;
  const next = [...rows];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

const emptyQuestion = (section_code: string, n: number): TemplateQuestion => ({
  question_code: "Q" + n,
  section_code,
  allow_na: 0,
  selection_mode: "Single",
  multi_score_method: "Highest",
  allow_comment: "",
  allow_attachment: "",
  is_gating: 0,
  gate_trigger: "A",
  gate_cap_level: "",
  auto_source: "",
  question_text: "",
  question_text_ar: "",
  guidance: "",
  guidance_ar: "",
  option_a: "",
  option_b: "",
  option_c: "",
  option_d: "",
  option_a_ar: "",
  option_b_ar: "",
  option_c_ar: "",
  option_d_ar: "",
});

export default function TemplateFields({
  sections,
  questions,
  onSections,
  onQuestions,
  points,
  readOnly = false,
  activeSection,
  onActiveSection,
  openQuestion,
  onOpenQuestion,
}: {
  sections: TemplateSection[];
  questions: TemplateQuestion[];
  onSections: (rows: TemplateSection[]) => void;
  onQuestions: (rows: TemplateQuestion[]) => void;
  points?: Record<string, number>;
  readOnly?: boolean;
  activeSection?: string;
  onActiveSection?: (code: string) => void;
  openQuestion?: string | null;
  onOpenQuestion?: (code: string | null) => void;
}) {
  const { t } = useLanguage();
  const sectionCode = activeSection || sections[0]?.section_code || "";
  const sectionChange = (i: number, key: string, value: any) =>
    onSections(sections.map((row, n) => (n === i ? { ...row, [key]: value } : row)));
  const questionChange = (i: number, key: string, value: any) =>
    onQuestions(questions.map((row, n) => (n === i ? { ...row, [key]: value } : row)));
  const sectionIdx = sections.findIndex((s) => s.section_code === sectionCode);
  const section = sections[sectionIdx];
  const sectionQuestions = questions
    .map((q, i) => ({ q, i }))
    .filter(({ q }) => q.section_code === sectionCode);
  const pts = points || { A: 25, B: 50, C: 75, D: 100 };
  const open = openQuestion ?? null;

  function renameSection(oldCode: string, newCode: string) {
    if (!newCode || oldCode === newCode) return;
    onSections(sections.map((s) => (s.section_code === oldCode ? { ...s, section_code: newCode } : s)));
    onQuestions(questions.map((q) => (q.section_code === oldCode ? { ...q, section_code: newCode } : q)));
    onActiveSection?.(newCode);
  }

  return (
    <div className="tpl-editor">
      <aside className="tpl-nav" aria-label={t("Sections")}>
        <div className="tpl-nav-head">
          <h3>{t("Sections")}</h3>
          {!readOnly && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                const code = "S" + (sections.length + 1);
                onSections([
                  ...sections,
                  {
                    section_code: code,
                    section_title: "",
                    section_title_ar: "",
                    weight: 1,
                    allow_comment: "",
                    allow_attachment: "",
                  },
                ]);
                onActiveSection?.(code);
              }}
            >
              <Plus size={15} />
              {t("Add")}
            </Button>
          )}
        </div>
        <ul>
          {sections.map((s, i) => (
            <li key={s.section_code + "-" + i}>
              <button
                type="button"
                className={"tpl-nav-item" + (s.section_code === sectionCode ? " active" : "")}
                onClick={() => onActiveSection?.(s.section_code)}
              >
                <strong>{s.section_code}</strong>
                <span>{s.section_title || t("Untitled section")}</span>
                <small>
                  {questions.filter((q) => q.section_code === s.section_code).length} {t("questions")}
                </small>
              </button>
              {!readOnly && (
                <div className="tpl-nav-tools">
                  <button
                    type="button"
                    aria-label={t("Move up")}
                    disabled={i === 0}
                    onClick={() => onSections(move(sections, i, i - 1))}
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label={t("Move down")}
                    disabled={i === sections.length - 1}
                    onClick={() => onSections(move(sections, i, i + 1))}
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </aside>

      <div className="tpl-main">
        {!section ? (
          <p className="muted">{t("Add a section to begin.")}</p>
        ) : (
          <>
            <section className="panel padded tpl-section-meta">
              <div className="panel-heading tpl-inline-head">
                <h2>
                  {t("Section")} · {section.section_code}
                </h2>
                {!readOnly && (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      onQuestions(questions.filter((q) => q.section_code !== section.section_code));
                      const next = sections.filter((_, n) => n !== sectionIdx);
                      onSections(next);
                      onActiveSection?.(next[0]?.section_code || "");
                    }}
                  >
                    <Trash2 size={15} />
                    {t("Remove section")}
                  </Button>
                )}
              </div>
              <fieldset disabled={readOnly}>
                <div className="form-grid">
                  <Field label="Section code">
                    <input
                      value={section.section_code}
                      onChange={(e) => renameSection(section.section_code, e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Section weight">
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={section.weight ?? 1}
                      onChange={(e) => sectionChange(sectionIdx, "weight", Number(e.target.value))}
                    />
                  </Field>
                  <Field label="English title">
                    <input
                      value={section.section_title || ""}
                      onChange={(e) => sectionChange(sectionIdx, "section_title", e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Arabic title">
                    <input
                      dir="rtl"
                      value={section.section_title_ar || ""}
                      onChange={(e) => sectionChange(sectionIdx, "section_title_ar", e.target.value)}
                      required
                    />
                  </Field>
                </div>
                <div className="form-grid">
                  <InheritSelect
                    label="Allow comments"
                    value={section.allow_comment}
                    onChange={(v) => sectionChange(sectionIdx, "allow_comment", v)}
                    disabled={readOnly}
                  />
                  <InheritSelect
                    label="Allow attachments"
                    value={section.allow_attachment}
                    onChange={(v) => sectionChange(sectionIdx, "allow_attachment", v)}
                    disabled={readOnly}
                  />
                </div>
                <p className="muted">
                  {t("Empty inherit uses the questionnaire default. Question overrides win over section.")}
                </p>
              </fieldset>
            </section>

            <section className="panel padded">
              <div className="panel-heading tpl-inline-head">
                <h2>{t("Questions")}</h2>
                {!readOnly && (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      const q = emptyQuestion(section.section_code, questions.length + 1);
                      onQuestions([...questions, q]);
                      onOpenQuestion?.(q.question_code);
                    }}
                  >
                    <Plus size={16} />
                    {t("Add question")}
                  </Button>
                )}
              </div>
              {!sectionQuestions.length && <p className="muted">{t("No questions in this section yet.")}</p>}
              {sectionQuestions.map(({ q, i }, localIdx) => {
                const isOpen = open === q.question_code;
                return (
                  <article
                    key={q.question_code + "-" + i}
                    className={"tpl-question" + (isOpen ? " open" : "")}
                  >
                    <header className="tpl-question-head">
                      <button
                        type="button"
                        className="tpl-question-toggle"
                        onClick={() => onOpenQuestion?.(isOpen ? null : q.question_code)}
                      >
                        <strong>{q.question_code}</strong>
                        <span>{q.question_text || t("New question")}</span>
                        <em>
                          {(q.selection_mode || "Single") === "Multi"
                            ? `${t("Multi-select")} · ${t(q.multi_score_method || "Highest")}`
                            : t("Single choice")}
                        </em>
                      </button>
                      {!readOnly && (
                        <div className="tpl-nav-tools">
                          <button
                            type="button"
                            aria-label={t("Move up")}
                            disabled={localIdx === 0}
                            onClick={() => {
                              const idxs = sectionQuestions.map((x) => x.i);
                              const a = idxs[localIdx],
                                b = idxs[localIdx - 1];
                              const next = [...questions];
                              const tmp = next[a];
                              next[a] = next[b];
                              next[b] = tmp;
                              onQuestions(next);
                            }}
                          >
                            <ChevronUp size={14} />
                          </button>
                          <button
                            type="button"
                            aria-label={t("Move down")}
                            disabled={localIdx === sectionQuestions.length - 1}
                            onClick={() => {
                              const idxs = sectionQuestions.map((x) => x.i);
                              const a = idxs[localIdx],
                                b = idxs[localIdx + 1];
                              const next = [...questions];
                              const tmp = next[a];
                              next[a] = next[b];
                              next[b] = tmp;
                              onQuestions(next);
                            }}
                          >
                            <ChevronDown size={14} />
                          </button>
                          <button
                            type="button"
                            aria-label={t("Remove question")}
                            onClick={() => onQuestions(questions.filter((_, n) => n !== i))}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </header>
                    {isOpen && (
                      <fieldset className="tpl-question-body" disabled={readOnly}>
                        <div className="form-grid">
                          <Field label="Question code">
                            <input
                              value={q.question_code}
                              onChange={(e) => {
                                questionChange(i, "question_code", e.target.value);
                                onOpenQuestion?.(e.target.value);
                              }}
                              required
                            />
                          </Field>
                          <Field label="Section">
                            <Select
                              value={q.section_code}
                              onChange={(e) => questionChange(i, "section_code", e.target.value)}
                              required
                            >
                              {sections.map((s) => (
                                <option key={s.section_code} value={s.section_code}>
                                  {s.section_title || s.section_code}
                                </option>
                              ))}
                            </Select>
                          </Field>
                          <Field label="Short label">
                            <input
                              value={q.short_label || ""}
                              onChange={(e) => questionChange(i, "short_label", e.target.value)}
                            />
                          </Field>
                        </div>
                        {[
                          ["question_text", "English question"],
                          ["question_text_ar", "Arabic question"],
                          ["guidance", "English guidance"],
                          ["guidance_ar", "Arabic guidance"],
                        ].map(([key, label]) => (
                          <Field key={key} label={label}>
                            <textarea
                              rows={2}
                              dir={key.endsWith("_ar") ? "rtl" : "ltr"}
                              value={q[key] || ""}
                              required={key.startsWith("question_text")}
                              onChange={(e) => questionChange(i, key, e.target.value)}
                            />
                          </Field>
                        ))}

                        <h4>{t("Answers and points")}</h4>
                        <p className="muted">
                          {t(
                            "Option points come from the scoring policy (A–D). They apply to all questions and are pinned when you publish.",
                          )}
                        </p>
                        {(["a", "b", "c", "d"] as const).map((c) => {
                          const letter = c.toUpperCase();
                          return (
                            <div className="tpl-option-row" key={c}>
                              <div className="tpl-option-badge">
                                <span>{letter}</span>
                                <strong>
                                  {pts[letter] ?? 0} {t("pts")}
                                </strong>
                              </div>
                              <div className="form-grid tpl-option-fields">
                                <Field label={t("Answer") + " " + letter + " · " + t("English")}>
                                  <textarea
                                    rows={2}
                                    value={q["option_" + c] || ""}
                                    onChange={(e) => questionChange(i, "option_" + c, e.target.value)}
                                    required
                                  />
                                </Field>
                                <Field label={t("Answer") + " " + letter + " · " + t("Arabic")}>
                                  <textarea
                                    dir="rtl"
                                    rows={2}
                                    value={q["option_" + c + "_ar"] || ""}
                                    onChange={(e) => questionChange(i, "option_" + c + "_ar", e.target.value)}
                                    required
                                  />
                                </Field>
                              </div>
                            </div>
                          );
                        })}

                        <h4>{t("Scoring for this question")}</h4>
                        <div className="form-grid">
                          <Field label={t("Selection mode")}>
                            <Select
                              value={q.selection_mode || "Single"}
                              onChange={(e) => questionChange(i, "selection_mode", e.target.value)}
                            >
                              <option value="Single">{t("Single choice")}</option>
                              <option value="Multi">{t("Multi-select")}</option>
                            </Select>
                          </Field>
                          {(q.selection_mode || "Single") === "Multi" && (
                            <Field label={t("Multi-select scoring")}>
                              <Select
                                value={q.multi_score_method || "Highest"}
                                onChange={(e) => questionChange(i, "multi_score_method", e.target.value)}
                              >
                                <option value="Highest">{t("Highest")}</option>
                                <option value="Average">{t("Average")}</option>
                                <option value="Sum (capped)">{t("Sum (capped)")}</option>
                              </Select>
                            </Field>
                          )}
                          <label className="check-label">
                            <input
                              type="checkbox"
                              checked={!!q.allow_na}
                              onChange={(e) => questionChange(i, "allow_na", e.target.checked ? 1 : 0)}
                            />
                            {t("Allow not applicable")}
                          </label>
                        </div>
                        {(q.selection_mode || "Single") === "Multi" && (
                          <p className="muted">
                            {t(
                              "Respondents can select more than one A–D option. Scoring uses the method above.",
                            )}
                          </p>
                        )}

                        <div className="form-grid">
                          <label className="check-label">
                            <input
                              type="checkbox"
                              checked={!!q.is_gating}
                              onChange={(e) => questionChange(i, "is_gating", e.target.checked ? 1 : 0)}
                            />
                            {t("Gating question")}
                          </label>
                          {!!q.is_gating && (
                            <>
                              <Field label={t("Gate triggers on")}>
                                <Select
                                  value={q.gate_trigger || "A"}
                                  onChange={(e) => questionChange(i, "gate_trigger", e.target.value)}
                                >
                                  <option value="A">A</option>
                                  <option value="A or B">A or B</option>
                                </Select>
                              </Field>
                              <Field label={t("Cap overall level at")}>
                                <input
                                  value={q.gate_cap_level || ""}
                                  onChange={(e) => questionChange(i, "gate_cap_level", e.target.value)}
                                  placeholder="Low"
                                />
                              </Field>
                            </>
                          )}
                          <Field label={t("Auto-calculate from")}>
                            <Select
                              value={q.auto_source || ""}
                              onChange={(e) => questionChange(i, "auto_source", e.target.value)}
                            >
                              <option value="">{t("None")}</option>
                              <option value="Issue Closure Time">{t("Issue Closure Time")}</option>
                            </Select>
                          </Field>
                        </div>
                        {!!q.is_gating && (
                          <p className="muted">{t("This question applies the published maturity cap.")}</p>
                        )}
                        {!!q.auto_source && (
                          <p className="muted">
                            {t("This question uses the published issue-register calculation.")}
                          </p>
                        )}

                        <div className="form-grid">
                          <InheritSelect
                            label="Allow comments"
                            value={q.allow_comment}
                            onChange={(v) => questionChange(i, "allow_comment", v)}
                            disabled={readOnly}
                          />
                          <InheritSelect
                            label="Allow attachments"
                            value={q.allow_attachment}
                            onChange={(v) => questionChange(i, "allow_attachment", v)}
                            disabled={readOnly}
                          />
                        </div>
                        <p className="muted">
                          {t("Empty inherit uses the section override, then the questionnaire default.")}
                        </p>
                      </fieldset>
                    )}
                  </article>
                );
              })}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
