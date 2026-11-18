import { useAssessmentTypes } from "../assessmentTypes";
import Select from "../Select";
import { useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Copy, Eye, FileStack, Pencil, Plus } from "lucide-react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import {
  Button,
  Empty,
  ErrorNotice,
  Field,
  Form,
  Loading,
  PageTitle,
  SearchInput,
  Status,
} from "../components";
import TemplateFields from "./TemplateFields";
import type { TemplateQuestion, TemplateSection } from "./TemplateFields";
import { liveOverall, parseSelected } from "../liveScore";
import type { ScoringPolicy } from "../liveScore";
import "../assessment.css";
import "../templates.css";
import "../template-controls.css";

const LEVELS: Record<string, string> = { A: "Ad hoc", B: "Foundational", C: "Established", D: "Leading" };
const LETTERS_AR: Record<string, string> = { A: "أ", B: "ب", C: "ج", D: "د" };

function basePath() {
  return "/grc/auditor/admin/templates";
}

function selectedLetters(raw?: string) {
  const parsed = parseSelected(raw);
  return parsed.kind === "letters" ? parsed.letters : parsed.kind === "N/A" ? ["N/A"] : [];
}
function encodeSelection(letters: string[]) {
  if (letters.includes("N/A")) return "N/A";
  return [...new Set(letters.filter((l) => l !== "N/A"))]
    .sort((a, b) => "ABCD".indexOf(a) - "ABCD".indexOf(b))
    .join(",");
}

export function TemplatesPage() {
  const typeLabel = useAssessmentTypes().label;
  const { t } = useLanguage(),
    navigate = useNavigate();
  const { data, error, mutate } = useData<any[]>("templates", { management: 1 });
  const save = useMutation("save_template");
  const [search, setSearch] = useState(""),
    [status, setStatus] = useState("all"),
    [cloneError, setCloneError] = useState<any>(),
    [busy, setBusy] = useState("");
  const rows = (data || []).filter((a) => {
    const q = search.toLowerCase();
    const match =
      !q || a.template_name.toLowerCase().includes(q) || (a.framework || "").toLowerCase().includes(q);
    if (!match) return false;
    if (status === "published") return !!a.grc_published;
    if (status === "draft") return !a.grc_published;
    return true;
  });
  const stats = {
    total: data?.length || 0,
    published: data?.filter((a) => a.grc_published).length || 0,
    draft: data?.filter((a) => !a.grc_published).length || 0,
  };

  async function cloneTemplate(a: any) {
    setBusy(a.name);
    setCloneError(null);
    try {
      const r = await save.execute({
        name: a.name,
        clone: 1,
        data: { template_name: a.template_name + " · revision " + (Number(a.version) + 1) },
      });
      await mutate();
      navigate(basePath() + "/" + encodeURIComponent(r.name));
    } catch (e) {
      setCloneError(e);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageTitle
        eyebrow="Administration"
        title="Questionnaire templates"
        description="Published versions are immutable. Clone a version to change questions or scoring policy."
      >
        <Button onClick={() => navigate(basePath() + "/new")}>
          <Plus size={16} />
          {t("Create template")}
        </Button>
      </PageTitle>
      <ErrorNotice error={cloneError || error} />
      <div className="tpl-stats">
        <div className="tpl-stat">
          <span>{t("Templates")}</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="tpl-stat">
          <span>{t("Published")}</span>
          <strong>{stats.published}</strong>
        </div>
        <div className="tpl-stat">
          <span>{t("Draft")}</span>
          <strong>{stats.draft}</strong>
        </div>
      </div>
      <section className="panel">
        <div className="toolbar">
          <SearchInput value={search} onChange={setSearch} />
          <div className="toolbar-filters">
            <Select aria-label={t("Status")} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="all">{t("All statuses")}</option>
              <option value="draft">{t("Draft")}</option>
              <option value="published">{t("Published")}</option>
            </Select>
          </div>
        </div>
        {!rows.length ? (
          <Empty
            title="No questionnaire templates"
            text="Create a draft template or clone a published version to begin."
          >
            <Button onClick={() => navigate(basePath() + "/new")}>
              <Plus size={16} />
              {t("Create template")}
            </Button>
          </Empty>
        ) : (
          <div className="tpl-card-grid">
            {rows.map((a) => (
              <article className="tpl-card" key={a.name}>
                <div className="tpl-card-top">
                  <FileStack size={18} />
                  <Status value={a.grc_published ? "Published" : "Draft"} />
                </div>
                <h2>{a.template_name}</h2>
                <p>
                  {typeLabel(a.assessment_type || "Internal Audit")} ·{" "}
                  {t(a.is_active ? "Active" : "Disabled")}
                  {a.is_default ? ` · ${t("Default")}` : ""}
                </p>
                <p className="muted">
                  {a.framework || "—"} · v{a.version}
                  {a.question_count != null ? ` · ${a.question_count} ${t("questions")}` : ""}
                </p>
                <div className="tpl-card-actions">
                  <Link className="button secondary" to={basePath() + "/" + encodeURIComponent(a.name)}>
                    <Pencil size={15} />
                    {t(a.grc_published ? "Open" : "Edit")}
                  </Link>
                  <Link
                    className="button ghost"
                    to={basePath() + "/" + encodeURIComponent(a.name) + "/preview"}
                  >
                    <Eye size={15} />
                    {t("Preview")}
                  </Link>
                  <Button variant="ghost" loading={busy === a.name} onClick={() => void cloneTemplate(a)}>
                    <Copy size={15} />
                    {t("Clone version")}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

const seedSection = {
  section_code: "S1",
  section_title: "Domain 1",
  section_title_ar: "المجال 1",
  weight: 1,
  allow_comment: "",
  allow_attachment: "",
};
const seedQuestion = {
  question_code: "Q1",
  section_code: "S1",
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
};

export function TemplateNewPage() {
  const { t } = useLanguage(),
    navigate = useNavigate(),
    save = useMutation("save_template");
  const [error, setError] = useState<any>();
  return (
    <>
      <Link className="back-link" to={basePath()}>
        <ArrowLeft size={15} />
        {t("Questionnaire templates")}
      </Link>
      <PageTitle
        eyebrow="Administration"
        title="Create template"
        description="Start a draft questionnaire. Publish when questions and scoring are ready."
      />
      <ErrorNotice error={error} />
      <section className="panel padded">
        <Form
          onSubmit={async (values) => {
            try {
              const r = await save.execute({
                data: {
                  template_name: values.template_name,
                  framework: values.framework,
                  version: values.version || "1",
                  introduction: values.introduction || "",
                  introduction_ar: values.introduction_ar || "",
                  weighting_method: values.weighting_method || "Points (each question equal)",
                  default_allow_comment: Number(values.default_allow_comment),
                  default_allow_attachment: Number(values.default_allow_attachment),
                  sections: [{ ...seedSection }],
                  questions: [{ ...seedQuestion }],
                },
              });
              navigate(basePath() + "/" + encodeURIComponent(r.name), { replace: true });
            } catch (e) {
              setError(e);
              throw e;
            }
          }}
        >
          <div className="form-grid">
            <Field label="Template name">
              <input name="template_name" required />
            </Field>
            <Field label="Framework">
              <input name="framework" defaultValue="IIA Global Internal Audit Standards" />
            </Field>
            <Field label="Version">
              <input name="version" defaultValue="1" />
            </Field>
            <Field label="Weighting method">
              <Select name="weighting_method" defaultValue="Points (each question equal)">
                <option value="Points (each question equal)">{t("Points (each question equal)")}</option>
                <option value="Section Weights">{t("Section Weights")}</option>
              </Select>
            </Field>
          </div>
          <Field label="Introduction">
            <textarea name="introduction" rows={3} />
          </Field>
          <Field label="Arabic introduction">
            <textarea name="introduction_ar" dir="rtl" rows={3} />
          </Field>
          <div className="form-grid">
            <Field label="Allow comments by default">
              <Select name="default_allow_comment" defaultValue="0">
                <option value="1">{t("Enabled")}</option>
                <option value="0">{t("Disabled")}</option>
              </Select>
            </Field>
            <Field label="Allow attachments by default">
              <Select name="default_allow_attachment" defaultValue="0">
                <option value="1">{t("Enabled")}</option>
                <option value="0">{t("Disabled")}</option>
              </Select>
            </Field>
          </div>
          <Button type="submit">
            <Plus size={16} />
            {t("Create draft")}
          </Button>
        </Form>
      </section>
    </>
  );
}

export function TemplateEditPage() {
  const { id } = useParams(),
    name = decodeURIComponent(id || "");
  const { data, error, mutate } = useData<any>("templates", { name });
  if (!name) return <Navigate to={basePath()} replace />;
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return <TemplateEditor key={data.modified} data={data} mutate={mutate} />;
}

function TemplateEditor({ data, mutate }: { data: any; mutate: () => Promise<any> }) {
  const typeLabel = useAssessmentTypes().label;
  const { t } = useLanguage(),
    navigate = useNavigate();
  const save = useMutation("save_template"),
    publish = useMutation("publish_template"),
    saveSettings = useMutation("save_settings");
  const { data: settings } = useData<any>("settings");
  const [sections, setSections] = useState<TemplateSection[]>(data.sections || []);
  const [questions, setQuestions] = useState<TemplateQuestion[]>(data.questions || []);
  const [activeSection, setActiveSection] = useState(data.sections?.[0]?.section_code || "");
  const [openQuestion, setOpenQuestion] = useState<string | null>(null);
  const [publishError, setPublishError] = useState<any>(),
    [scoreError, setScoreError] = useState<any>(),
    [saveError, setSaveError] = useState<any>();
  const published = !!data.grc_published;
  const points = data.scoring?.points || {
    A: Number(settings?.scoring?.points_a ?? 25),
    B: Number(settings?.scoring?.points_b ?? 50),
    C: Number(settings?.scoring?.points_c ?? 75),
    D: Number(settings?.scoring?.points_d ?? 100),
  };

  async function cloneAndEdit() {
    const r = await save.execute({
      name: data.name,
      clone: 1,
      data: { template_name: data.template_name + " · revision " + (Number(data.version) + 1) },
    });
    navigate(basePath() + "/" + encodeURIComponent(r.name), { replace: true });
  }

  return (
    <>
      <Link className="back-link" to={basePath()}>
        <ArrowLeft size={15} />
        {t("Questionnaire templates")}
      </Link>
      <PageTitle
        eyebrow={data.name}
        title={data.template_name}
        description={
          published
            ? t("Published versions are immutable. Clone a version to change questions or scoring policy.")
            : t("Edit sections, questions, and scoring. Preview the customer experience before publishing.")
        }
      >
        <Status value={published ? "Published" : "Draft"} />
        {data.is_default && (
          <span className="tpl-version">
            {t("Default template")} · {typeLabel(data.assessment_type || "Internal Audit")}
          </span>
        )}
        <span className="tpl-version">v{data.version}</span>
        <Link className="button secondary" to={basePath() + "/" + encodeURIComponent(data.name) + "/preview"}>
          <Eye size={15} />
          {t("Customer preview")}
        </Link>
        {published && (
          <Button variant="secondary" onClick={() => void cloneAndEdit().catch(setPublishError)}>
            <Copy size={15} />
            {t(data.is_default ? "Edit default template" : "Clone to edit")}
          </Button>
        )}
      </PageTitle>
      <ErrorNotice error={publishError || saveError} />

      {published && (
        <div className="notice warning">
          <div>
            <strong>{t("Published — read only")}</strong>
            <p>{t("This version is frozen. Clone it to create an editable draft.")}</p>
          </div>
        </div>
      )}

      <div className="tpl-layout">
        <aside className="tpl-meta-col">
          <section className="panel padded tpl-meta">
            <Form
              id="tpl-meta-form"
              onSubmit={async (values) => {
                if (published) return;
                try {
                  setSaveError(null);
                  await save.execute({
                    name: data.name,
                    data: {
                      template_name: values.template_name,
                      framework: values.framework,
                      introduction: values.introduction,
                      introduction_ar: values.introduction_ar,
                      answer_rule: values.answer_rule,
                      answer_rule_ar: values.answer_rule_ar,
                      weighting_method: values.weighting_method,
                      default_allow_comment: Number(values.default_allow_comment),
                      default_allow_attachment: Number(values.default_allow_attachment),
                      questions,
                      sections,
                    },
                  });
                  await mutate();
                } catch (e) {
                  setSaveError(e);
                  throw e;
                }
              }}
            >
              <h3>{t("Questionnaire")}</h3>
              <fieldset disabled={published}>
                <Field label="Template name">
                  <input
                    name="template_name"
                    defaultValue={data.template_name}
                    required
                    readOnly={published}
                  />
                </Field>
                <Field label="Framework">
                  <input name="framework" defaultValue={data.framework} readOnly={published} />
                </Field>
                <Field label="Weighting method">
                  <Select
                    name="weighting_method"
                    defaultValue={data.weighting_method || "Points (each question equal)"}
                    disabled={published}
                  >
                    <option value="Points (each question equal)">{t("Points (each question equal)")}</option>
                    <option value="Section Weights">{t("Section Weights")}</option>
                  </Select>
                </Field>
                <Field label="Introduction">
                  <textarea
                    name="introduction"
                    defaultValue={data.introduction}
                    readOnly={published}
                    rows={3}
                  />
                </Field>
                <Field label="Arabic introduction">
                  <textarea
                    name="introduction_ar"
                    dir="rtl"
                    defaultValue={data.introduction_ar}
                    readOnly={published}
                    rows={3}
                  />
                </Field>
                <Field label="Answering rule">
                  <textarea
                    name="answer_rule"
                    defaultValue={data.answer_rule}
                    readOnly={published}
                    rows={3}
                  />
                </Field>
                <Field label="Arabic answering rule">
                  <textarea
                    name="answer_rule_ar"
                    dir="rtl"
                    defaultValue={data.answer_rule_ar}
                    readOnly={published}
                    rows={3}
                  />
                </Field>
                <h4>{t("Comments and attachments")}</h4>
                <p className="muted">
                  {t(
                    "Questionnaire defaults. Sections and questions can override; empty inherit uses the parent. Resolution: question → section → questionnaire.",
                  )}
                </p>
                <Field label="Allow comments by default">
                  <Select
                    name="default_allow_comment"
                    defaultValue={data.default_allow_comment ?? 0}
                    disabled={published}
                  >
                    <option value="1">{t("Enabled")}</option>
                    <option value="0">{t("Disabled")}</option>
                  </Select>
                </Field>
                <Field label="Allow attachments by default">
                  <Select
                    name="default_allow_attachment"
                    defaultValue={data.default_allow_attachment ?? 0}
                    disabled={published}
                  >
                    <option value="1">{t("Enabled")}</option>
                    <option value="0">{t("Disabled")}</option>
                  </Select>
                </Field>
              </fieldset>
              {!published && (
                <div className="tpl-sticky-actions">
                  <Button type="submit">{t("Save draft")}</Button>
                </div>
              )}
            </Form>
          </section>

          <section className="panel padded tpl-meta">
            <h3>{t("Option points (A–D)")}</h3>
            <p className="muted">
              {t(
                "Shared scoring policy for future publishes. Existing published versions keep their pinned points.",
              )}
            </p>
            {settings && !published ? (
              <Form
                onSubmit={async (values) => {
                  try {
                    await saveSettings.execute({
                      data: {
                        scoring: {
                          ...settings.scoring,
                          points_a: values.points_a,
                          points_b: values.points_b,
                          points_c: values.points_c,
                          points_d: values.points_d,
                        },
                      },
                    });
                    setScoreError(null);
                    await mutate();
                  } catch (e) {
                    setScoreError(e);
                    throw e;
                  }
                }}
              >
                <div className="form-grid tpl-points-grid">
                  {(["a", "b", "c", "d"] as const).map((c) => (
                    <Field key={c} label={t("Answer") + " " + c.toUpperCase() + " " + t("points")}>
                      <input
                        name={"points_" + c}
                        type="number"
                        min={0}
                        max={100}
                        step="0.1"
                        defaultValue={settings.scoring?.["points_" + c] ?? points[c.toUpperCase()]}
                        required
                      />
                    </Field>
                  ))}
                </div>
                <Button type="submit" variant="secondary">
                  {t("Save scoring points")}
                </Button>
                <ErrorNotice error={scoreError} />
              </Form>
            ) : (
              <div className="tpl-points-readonly">
                {(["A", "B", "C", "D"] as const).map((l) => (
                  <span key={l}>
                    <em>{l}</em> {points[l]}
                  </span>
                ))}
              </div>
            )}
          </section>
        </aside>

        <div className="tpl-workspace">
          <TemplateFields
            sections={sections}
            questions={questions}
            onSections={setSections}
            onQuestions={setQuestions}
            points={points}
            readOnly={published}
            activeSection={activeSection}
            onActiveSection={setActiveSection}
            openQuestion={openQuestion}
            onOpenQuestion={setOpenQuestion}
          />
          {!published && (
            <div className="tpl-workspace-save">
              <Button
                type="button"
                onClick={async () => {
                  try {
                    setSaveError(null);
                    const form = document.getElementById("tpl-meta-form") as HTMLFormElement | null;
                    const values = form ? Object.fromEntries(new FormData(form)) : {};
                    await save.execute({
                      name: data.name,
                      data: {
                        template_name: values.template_name || data.template_name,
                        framework: values.framework || data.framework,
                        introduction: values.introduction ?? data.introduction,
                        introduction_ar: values.introduction_ar ?? data.introduction_ar,
                        answer_rule: values.answer_rule ?? data.answer_rule,
                        answer_rule_ar: values.answer_rule_ar ?? data.answer_rule_ar,
                        weighting_method: values.weighting_method || data.weighting_method,
                        default_allow_comment: Number(
                          values.default_allow_comment ?? data.default_allow_comment ?? 0,
                        ),
                        default_allow_attachment: Number(
                          values.default_allow_attachment ?? data.default_allow_attachment ?? 0,
                        ),
                        questions,
                        sections,
                      },
                    });
                    await mutate();
                  } catch (e) {
                    setSaveError(e);
                  }
                }}
              >
                {t("Save draft")}
              </Button>
            </div>
          )}
        </div>
      </div>

      {published && !!data.is_active && !data.is_default && (
        <section className="panel padded tpl-publish">
          <div className="settings-actions">
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await publish.execute({ name: data.name, make_default: 1 });
                  await mutate();
                } catch (e) {
                  setPublishError(e);
                }
              }}
            >
              {t("Make default for this assessment type")}
            </Button>
          </div>
        </section>
      )}
      {!published && (
        <section className="panel padded tpl-publish">
          <Form
            onSubmit={async (values) => {
              try {
                await publish.execute({
                  name: data.name,
                  make_default: values.make_default === "on" ? 1 : 0,
                });
                await mutate();
              } catch (e) {
                setPublishError(e);
                throw e;
              }
            }}
          >
            <header className="settings-heading">
              <h2>{t("Publish version")}</h2>
              <p className="muted">
                {t(
                  "Publishing freezes this questionnaire and the current scoring defaults for future assessments.",
                )}
              </p>
            </header>
            <label className="settings-check">
              <input type="checkbox" name="make_default" defaultChecked={!!data.grc_default_revision} />
              <span>{t("Make default for this assessment type")}</span>
            </label>
            <div className="settings-actions">
              <Button type="submit">
                <CheckCircle2 size={17} />
                {t("Publish version")}
              </Button>
            </div>
          </Form>
          <ErrorNotice error={publishError} />
        </section>
      )}
    </>
  );
}

export function TemplatePreviewPage() {
  const { id } = useParams(),
    name = id ? decodeURIComponent(id) : "";
  const { data, error } = useData<any>("templates", { name });
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return <TemplatePreview data={data} />;
}

function TemplatePreview({ data }: { data: any }) {
  const { t, lang } = useLanguage();
  const [section, setSection] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const questions = data.questions || [];
  // Memoised so the scoring memo below does not recompute on every render.
  const sectionsMeta = useMemo(() => data.sections || [], [data.sections]);
  const scoring: ScoringPolicy = useMemo(() => {
    const base = data.scoring || {
      points: { A: 25, B: 50, C: 75, D: 100 },
      max_points: 100,
      bands: [],
      sections: [],
    };
    return {
      ...base,
      weighting_method: data.weighting_method || base.weighting_method,
      sections: (sectionsMeta as any[]).map((s) => ({
        code: s.section_code,
        weight: s.weight == null ? 1 : Number(s.weight),
      })),
    };
  }, [data, sectionsMeta]);
  const points = scoring.points || { A: 25, B: 50, C: 75, D: 100 };
  const sectionList = Array.from(
    new Map(
      questions.map((q: any) => {
        const m = sectionsMeta.find((s: any) => s.section_code === q.section_code);
        const title =
          lang === "ar"
            ? m?.section_title_ar || m?.section_title || q.section_code
            : m?.section_title || q.section_code;
        return [
          q.section_code,
          {
            code: q.section_code,
            title,
            reference: lang === "ar" ? m?.reference_ar || m?.reference || "" : m?.reference || "",
          },
        ];
      }),
    ).values(),
  ) as { code: string; title: string; reference: string }[];
  const selected = sectionList[Math.min(section, Math.max(0, sectionList.length - 1))];
  const liveQs = questions.map((q: any) => ({
    section_code: q.section_code,
    selected_option: answers[q.question_code] || "",
    selection_mode: q.selection_mode,
    multi_score_method: q.multi_score_method,
    is_gating: q.is_gating,
    gate_trigger: q.gate_trigger,
    gate_cap_level: q.gate_cap_level,
  }));
  const live = liveOverall(liveQs, scoring);
  const liveBand = live.band;
  const liveBandLabel = liveBand
    ? lang === "ar"
      ? liveBand.level_name_ar || t(liveBand.level_name)
      : t(liveBand.level_name)
    : "";
  const livePct = Number.isInteger(live.pct) ? String(live.pct) : live.pct.toFixed(1);
  const answered = Object.values(answers).filter(Boolean).length;
  const progress = Math.round((answered / Math.max(1, questions.length)) * 100);
  const showLetter = (letter: string) => (lang === "ar" ? LETTERS_AR[letter] || letter : letter);
  const text = (q: any, key: string) => String((lang === "ar" ? q[key + "_ar"] : null) || q[key] || "");

  function toggle(q: any, letter: string) {
    const multi = (q.selection_mode || "Single") === "Multi";
    const chosen = selectedLetters(answers[q.question_code]);
    if (!multi) {
      setAnswers((a) => ({ ...a, [q.question_code]: letter }));
      return;
    }
    if (letter === "N/A") {
      setAnswers((a) => ({ ...a, [q.question_code]: chosen.includes("N/A") ? "" : "N/A" }));
      return;
    }
    const next = chosen.includes(letter)
      ? chosen.filter((x) => x !== letter && x !== "N/A")
      : [...chosen.filter((x) => x !== "N/A"), letter];
    setAnswers((a) => ({ ...a, [q.question_code]: encodeSelection(next) }));
  }

  return (
    <>
      <Link className="back-link" to={basePath() + "/" + encodeURIComponent(data.name)}>
        <ArrowLeft size={15} />
        {t("Back to editor")}
      </Link>
      <PageTitle
        eyebrow="Preview"
        title={data.template_name}
        description={t("Customer view simulation. Answers are not saved and no assessment is created.")}
      >
        <Status value={data.grc_published ? "Published" : "Draft"} />
        <Link className="button secondary" to={basePath() + "/" + encodeURIComponent(data.name)}>
          <Pencil size={15} />
          {t("Edit")}
        </Link>
      </PageTitle>
      <div className="notice">
        <Eye size={18} />
        <div>
          <strong>{t("Preview mode")}</strong>
          <p>{t("Interact with options to see live scoring. This does not create a real assessment.")}</p>
        </div>
      </div>

      <div className="iam-questionnaire">
        <div className="iam-stepper" role="list" aria-label={t("Sections")}>
          {sectionList.map((s, i) => {
            const qs = questions.filter((q: any) => q.section_code === s.code);
            const complete = qs.length > 0 && qs.every((q: any) => answers[q.question_code]);
            return (
              <button
                key={s.code}
                type="button"
                role="listitem"
                className={"iam-step" + (complete ? " done" : "")}
                aria-current={i === section ? "step" : undefined}
                onClick={() => setSection(i)}
              >
                <span className="n">
                  {t("Section")} {i + 1}
                </span>
                <span className="t">{s.title}</span>
              </button>
            );
          })}
        </div>
        <div className="iam-progress-row">
          <div className="assessment-progress">
            <strong>{answered}</strong> {t("of")} {questions.length} {t("answered")}
            <span className="iam-count-ratio">
              {" "}
              {answered}/{questions.length}
            </span>
          </div>
          <p className="iam-live-score" aria-live="polite">
            <span className="iam-live-label">{t("Current score")}</span>
            <strong className="iam-live-pct">
              {livePct}
              <span>%</span>
            </strong>
            {liveBandLabel && (
              <span className="iam-live-band" style={{ color: liveBand?.color || undefined }}>
                {liveBandLabel}
              </span>
            )}
          </p>
        </div>
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: progress + "%" }} />
        </div>
        <section className="panel iam-section">
          <div className="iam-section-head">
            <div>
              <p className="iam-kicker">
                {t("Section")} {section + 1} {t("of")} {sectionList.length}
              </p>
              <h2>{selected?.title}</h2>
              {selected?.reference && (
                <p className="iam-ref">
                  {t("Reference")}: {selected.reference}
                </p>
              )}
            </div>
          </div>
          {questions
            .filter((q: any) => q.section_code === selected?.code)
            .map((q: any) => {
              const multi = (q.selection_mode || "Single") === "Multi";
              const chosen = selectedLetters(answers[q.question_code]);
              return (
                <fieldset className="question-card" key={q.question_code}>
                  <div className="question-heading">
                    <span className="question-code">{q.question_code}</span>
                    <h3>{text(q, "question_text")}</h3>
                  </div>
                  {text(q, "guidance") && <p className="question-guidance">{text(q, "guidance")}</p>}
                  {multi && <p className="question-guidance muted">{t("Select all that apply")}</p>}
                  <div className="iam-opts">
                    {["A", "B", "C", "D", ...(q.allow_na ? ["N/A"] : [])].map((letter) => {
                      const isChosen = chosen.includes(letter);
                      return (
                        <label key={letter} className={"answer-option" + (isChosen ? " chosen" : "")}>
                          <input
                            type={multi ? "checkbox" : "radio"}
                            name={q.question_code + (multi ? `-${letter}` : "")}
                            value={letter}
                            checked={isChosen}
                            onChange={() => toggle(q, letter)}
                          />
                          <span className="iam-opt-top">
                            <span>
                              {letter === "N/A"
                                ? t("Not applicable")
                                : `${showLetter(letter)} · ${t(LEVELS[letter])}`}
                            </span>
                            {letter !== "N/A" && <span className="pts">{points[letter]}</span>}
                          </span>
                          <span className="iam-opt-text">
                            {letter === "N/A"
                              ? t("Excluded from the score.")
                              : text(q, "option_" + letter.toLowerCase())}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </fieldset>
              );
            })}
        </section>
        <div className="editor-footer">
          <Button variant="secondary" disabled={section === 0} onClick={() => setSection((s) => s - 1)}>
            <ArrowLeft size={16} />
            {t("Previous section")}
          </Button>
          {section < sectionList.length - 1 && (
            <Button onClick={() => setSection((s) => s + 1)}>{t("Next section")}</Button>
          )}
        </div>
      </div>
    </>
  );
}
