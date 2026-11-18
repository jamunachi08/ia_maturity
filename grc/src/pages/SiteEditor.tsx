import Select from "../Select";
import VisualSiteEditor from "./VisualSiteEditor";
import { useEffect, useMemo, useState } from "react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import { Button, ErrorNotice, Loading, PageTitle } from "../components";
import catalogue from "../site-content-defaults.json";
import type { SiteContent } from "../siteContent";
import "./site-editor.css";

type Revision = {
  name: string;
  status: string;
  content: SiteContent;
  modified: string;
  step: number;
  workflow: string[];
  submitted_by?: string;
  allow_submitter_approval?: boolean;
  base_revision?: string;
};
type State = {
  revision_page: number;
  event_page: number;
  revisions_more: boolean;
  events_more: boolean;
  can_edit: boolean;
  is_admin: boolean;
  roles: string[];
  allow_submitter_approval: boolean;
  editor_roles: string[];
  approval_roles: string[];
  available_roles: string[];
  published: SiteContent;
  published_revision?: string;
  draft?: Revision;
  revisions: (Omit<Revision, "content" | "workflow"> & { owner: string; creation: string })[];
  events: {
    name: string;
    revision: string;
    actor: string;
    action: string;
    details: string;
    creation: string;
  }[];
};
const legal = {
  "legal.privacy": { en: "Privacy notice", ar: "إشعار الخصوصية", section: "Legal" },
  "legal.terms": { en: "Terms of use", ar: "شروط الاستخدام", section: "Legal" },
};
const entries: Record<string, { en: string; ar: string; section: string }> = { ...catalogue, ...legal };
export default function SiteEditor() {
  const { lang } = useLanguage(),
    { session } = useSession(),
    ar = lang === "ar";
  const label = (en: string, arabic: string) => (ar ? arabic : en);
  const [revisionPage, setRevisionPage] = useState(1),
    [eventPage, setEventPage] = useState(1);
  const translate = (value: string) =>
    ar
      ? (
          {
            Shared: "عام",
            Landing: "الرئيسية",
            "Landing sample": "مثال الصفحة الرئيسية",
            Journey: "الرحلة",
            Navigation: "التنقل",
            Footer: "التذييل",
            Legal: "النصوص القانونية",
            services: "الخدمات",
            catalogue: "التقييمات",
            frameworks: "الأطر",
            about: "عن المنصة",
            resources: "الموارد",
            faq: "الأسئلة الشائعة",
            Draft: "مسودة",
            Pending: "بانتظار الاعتماد",
            Published: "منشور",
            Rejected: "مرفوض",
            Discarded: "ملغى",
            "Draft saved": "حُفظت المسودة",
            Submitted: "أُرسل للاعتماد",
            Decision: "قرار",
            "Published event": "نُشر",
            "Workflow configured": "تغيير مسار الاعتماد",
            "Draft discarded": "أُلغيت المسودة",
            "Submission cancelled": "أُلغي الطلب",
          } as Record<string, string>
        )[value] || value
      : value;
  const { data, error, mutate } = useData<State>("site_content_state", {
    revision_page: revisionPage,
    event_page: eventPage,
  });
  const save = useMutation("site_content_save"),
    submit = useMutation("site_content_submit"),
    decide = useMutation("site_content_decide"),
    configure = useMutation("site_content_configure"),
    discard = useMutation("site_content_discard"),
    cancel = useMutation("site_content_cancel"),
    load = useMutation("site_content_revision");
  const [content, setContent] = useState<SiteContent | null>(null),
    [name, setName] = useState<string>(),
    [modified, setModified] = useState<string>(),
    [search, setSearch] = useState(""),
    [roleSearch, setRoleSearch] = useState(""),
    [section, setSection] = useState("all"),
    [busy, setBusy] = useState(false),
    [problem, setProblem] = useState<any>(),
    [message, setMessage] = useState("");
  const [editors, setEditors] = useState<string[]>([]),
    [stages, setStages] = useState<string[]>([]),
    [allowSelf, setAllowSelf] = useState(false),
    [selected, setSelected] = useState<Revision>(),
    [comment, setComment] = useState("");
  // Seeds the editable draft once from server data; later edits stay local until saved.
  useEffect(() => {
    if (!data || content) return;
    const source = data.draft?.content || data.published;
    const merged: SiteContent = { ...source };
    for (const [key, value] of Object.entries(entries))
      merged[key] = source[key] || { en: value.en, ar: value.ar };
    // oxlint-disable-next-line react/set-state-in-effect
    setContent(merged);
    setName(data.draft?.name);
    setModified(data.draft?.modified);
    setEditors(data.editor_roles);
    setStages(data.approval_roles);
    setAllowSelf(data.allow_submitter_approval);
  }, [data, content]);
  const filtered = useMemo(
    () =>
      Object.entries(entries).filter(
        ([key, item]) =>
          (section === "all" || item.section === section) &&
          (!search ||
            [item.en, item.ar, content?.[key]?.en || "", content?.[key]?.ar || ""]
              .join(" ")
              .toLowerCase()
              .includes(search.toLowerCase())),
      ),
    [section, search, content],
  );
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setProblem(undefined);
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setProblem(e);
    } finally {
      setBusy(false);
    }
  };
  const reset = async () => {
    const result = await mutate();
    const state = result?.message as State | undefined;
    if (state) {
      const source = state.draft?.content || state.published;
      const next: SiteContent = { ...source };
      for (const [key, item] of Object.entries(entries))
        next[key] = source[key] || { en: item.en, ar: item.ar };
      setContent(next);
      setName(state.draft?.name);
      setModified(state.draft?.modified);
      setEditors(state.editor_roles);
      setStages(state.approval_roles);
      setAllowSelf(state.allow_submitter_approval);
    }
  };
  const doSave = async () => {
    const result = await save.execute({ content, name, modified });
    setName(result.name);
    setModified(result.modified);
    setMessage(label("Draft saved. It is not live.", "حُفظت المسودة ولم تُنشر بعد."));
    await mutate();
    return result as Revision;
  };
  if (error) return <ErrorNotice error={error} />;
  if (!data || !content) return <Loading />;
  const baseline = data.draft?.content || data.published;
  const structuralChanged = Object.keys({ ...content, ...baseline })
    .filter((k) => !(k in entries))
    .some((k) => content[k]?.en !== baseline[k]?.en || content[k]?.ar !== baseline[k]?.ar);
  const changed =
    structuralChanged ||
    Object.entries(entries).some(([key, item]) => {
      const before = baseline[key] || { en: item.en, ar: item.ar };
      return content[key]?.en !== before.en || content[key]?.ar !== before.ar;
    });
  return (
    <div className="site-editor">
      <PageTitle
        title={label("Website content", "محتوى الموقع")}
        description={label(
          "Edit public website text in both languages. Changes go live only after the required approvals.",
          "عدّل نصوص الموقع العامة باللغتين. لا تُنشر التغييرات حتى تكتمل الموافقات المطلوبة.",
        )}
      />
      <ErrorNotice error={problem} />
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {data.is_admin && (
        <details className="site-workflow-settings">
          <summary>{label("Access and approval workflow", "صلاحيات الوصول ومسار الاعتماد")}</summary>
          <section className="panel padded">
            <h2>{label("Access and approval workflow", "صلاحيات الوصول ومسار الاعتماد")}</h2>
            <p>
              {label(
                "Select roles held by signed-in GRC users who may edit. Every user with a selected role gets access. Administrators can always edit. Add approval roles in order; by default, the submitter cannot approve their own submission. Pending submissions keep their original workflow.",
                "حدد أدوار مستخدمي GRC الذين يمكنهم التعديل. يحصل كل مستخدم يحمل الدور المحدد على الصلاحية. يمكن للمديرين التعديل دائماً. أضف أدوار الاعتماد بالترتيب؛ لا يمكن لمقدم الطلب اعتماد طلبه افتراضياً. تحتفظ الطلبات المرسلة بمسارها الأصلي.",
              )}
            </p>
            <label className="site-role-search">
              {label("Find a role", "البحث عن دور")}
              <input
                value={roleSearch}
                onChange={(e) => setRoleSearch(e.target.value)}
                placeholder={label("Search roles", "بحث عن الأدوار")}
              />
            </label>
            <fieldset className="site-roles">
              <legend>{label("Editor roles", "أدوار المحررين")}</legend>
              {data.available_roles
                .filter((role) => role.toLowerCase().includes(roleSearch.toLowerCase()))
                .sort(
                  (a, b) => Number(b.startsWith("GRC ")) - Number(a.startsWith("GRC ")) || a.localeCompare(b),
                )
                .map((role) => (
                  <label key={role}>
                    <input
                      type="checkbox"
                      checked={editors.includes(role)}
                      onChange={(e) =>
                        setEditors(e.target.checked ? [...editors, role] : editors.filter((r) => r !== role))
                      }
                    />{" "}
                    {role}
                  </label>
                ))}
            </fieldset>
            <label className="site-self-policy">
              <input type="checkbox" checked={allowSelf} onChange={(e) => setAllowSelf(e.target.checked)} />{" "}
              {label(
                "Allow the submitter to approve when they have the required role",
                "السماح لمقدم الطلب بالاعتماد إذا كان يحمل الدور المطلوب",
              )}
            </label>
            <h3>{label("Approval steps", "خطوات الاعتماد")}</h3>
            {stages.map((role, i) => (
              <div className="site-stage" key={i}>
                <span>{i + 1}</span>
                <Select
                  aria-label={label(`Approval step ${i + 1}`, `خطوة الاعتماد ${i + 1}`)}
                  value={role}
                  onChange={(e) => setStages(stages.map((r, n) => (n === i ? e.target.value : r)))}
                >
                  {data.available_roles.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </Select>
                <button
                  type="button"
                  disabled={stages.length === 1}
                  onClick={() => setStages(stages.filter((_, n) => n !== i))}
                >
                  {label("Remove", "إزالة")}
                </button>
              </div>
            ))}
            <div className="site-actions">
              <Button
                variant="secondary"
                disabled={busy || stages.length >= 10}
                onClick={() => setStages([...stages, "GRC App Admin"])}
              >
                {label("Add approval step", "إضافة خطوة اعتماد")}
              </Button>
              <Button
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await configure.execute({
                      editor_roles: editors,
                      approval_roles: stages,
                      allow_submitter_approval: allowSelf ? 1 : 0,
                    });
                    await mutate();
                    setMessage(label("Workflow saved.", "تم حفظ مسار الاعتماد."));
                  })
                }
              >
                {label("Save workflow", "حفظ مسار الاعتماد")}
              </Button>
            </div>
          </section>
        </details>
      )}
      {data.can_edit && (
        <section className="panel padded">
          <div className="site-editor-heading">
            <div>
              <h2>{label("Bilingual draft", "المسودة باللغتين")}</h2>
              <p>
                {name
                  ? label("Editing saved draft", "تعديل مسودة محفوظة") + " " + name
                  : label("New draft based on the published site", "مسودة جديدة من الموقع المنشور")}
              </p>
            </div>
            <div className="site-actions">
              <Button variant="secondary" disabled={busy} onClick={() => void run(reset)}>
                {label("Reload", "إعادة التحميل")}
              </Button>
              <Button
                variant="secondary"
                disabled={busy || !name}
                onClick={() => {
                  if (
                    window.confirm(
                      label(
                        "Discard this draft? Its audit history remains.",
                        "هل تريد إلغاء المسودة؟ سيبقى سجلها.",
                      ),
                    )
                  )
                    void run(async () => {
                      await discard.execute({ name, modified });
                      await mutate();
                      setContent(null);
                      setName(undefined);
                      setModified(undefined);
                    });
                }}
              >
                {label("Discard draft", "إلغاء المسودة")}
              </Button>
              {name && (
                <a
                  className="button secondary"
                  href={"/grc-site?preview=" + encodeURIComponent(name)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {label("Preview saved draft", "معاينة المسودة المحفوظة")}
                </a>
              )}
              <Button
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await doSave();
                  })
                }
              >
                {label("Save draft", "حفظ المسودة")}
              </Button>
              <Button
                disabled={busy || !name || changed}
                onClick={() =>
                  void run(async () => {
                    await submit.execute({ name, modified });
                    await mutate();
                    setContent(null);
                    setName(undefined);
                    setModified(undefined);
                    setMessage(label("Submitted for approval.", "أُرسلت للاعتماد."));
                  })
                }
              >
                {label("Submit for approval", "إرسال للاعتماد")}
              </Button>
            </div>
          </div>
          <p className="notice">
            {label(
              "Save before submitting. The submitted version is locked and its approval steps are captured.",
              "احفظ قبل الإرسال. تُقفل النسخة المرسلة ويُثبت مسار اعتمادها.",
            )}
          </p>
          <VisualSiteEditor content={content} onChange={setContent} />
          <details className="site-advanced">
            <summary>{label("All text fields", "جميع حقول النصوص")}</summary>
            <div className="site-filters">
              <input
                aria-label={label("Search content", "البحث في المحتوى")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={label("Search English or Arabic", "بحث بالإنجليزية أو العربية")}
              />
              <Select
                aria-label={label("Content section", "قسم المحتوى")}
                value={section}
                onChange={(e) => setSection(e.target.value)}
              >
                <option value="all">{label("All sections", "كل الأقسام")}</option>
                {[...new Set(Object.values(entries).map((e) => e.section))].sort().map((s) => (
                  <option key={s} value={s}>
                    {translate(s)}
                  </option>
                ))}
              </Select>
            </div>
            <div className="site-fields">
              {filtered.map(([key, item]) => (
                <article className="site-field" key={key}>
                  <div>
                    <strong>{translate(item.section)}</strong>
                    <small>{item.en}</small>
                  </div>
                  <label>
                    English
                    <textarea
                      lang="en"
                      dir="ltr"
                      rows={3}
                      maxLength={12000}
                      value={content[key]?.en ?? ""}
                      onChange={(e) =>
                        setContent({ ...content, [key]: { ...content[key], en: e.target.value } })
                      }
                    />
                  </label>
                  <label>
                    العربية
                    <textarea
                      lang="ar"
                      dir="rtl"
                      rows={3}
                      maxLength={12000}
                      value={content[key]?.ar ?? ""}
                      onChange={(e) =>
                        setContent({ ...content, [key]: { ...content[key], ar: e.target.value } })
                      }
                    />
                  </label>
                </article>
              ))}
            </div>
          </details>
        </section>
      )}
      <section className="panel padded">
        <h2>{label("Revisions and approvals", "الإصدارات والموافقات")}</h2>
        <p>
          {label(
            "Open a revision to inspect its full bilingual snapshot and decide the current approval step.",
            "افتح الإصدار لعرض المحتوى الكامل باللغتين واتخاذ قرار خطوة الاعتماد الحالية.",
          )}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{label("Revision", "الإصدار")}</th>
                <th>{label("Status", "الحالة")}</th>
                <th>{label("Author", "المؤلف")}</th>
                <th>{label("Date", "التاريخ")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.revisions.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{translate(r.status)}</td>
                  <td>{r.submitted_by || r.owner}</td>
                  <td>{String(r.creation || "").slice(0, 16)}</td>
                  <td>
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          const result = await load.execute({ name: r.name });
                          setSelected(result);
                          setComment("");
                        })
                      }
                    >
                      {label("Open", "فتح")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="site-actions">
          <Button
            variant="secondary"
            disabled={revisionPage === 1}
            onClick={() => setRevisionPage(revisionPage - 1)}
          >
            {label("Previous", "السابق")}
          </Button>
          <span>{revisionPage}</span>
          <Button
            variant="secondary"
            disabled={!data.revisions_more}
            onClick={() => setRevisionPage(revisionPage + 1)}
          >
            {label("Next", "التالي")}
          </Button>
        </div>
      </section>
      {selected && (
        <section className="panel padded">
          <div className="site-editor-heading">
            <h2>
              {label("Revision", "الإصدار")} {selected.name}
            </h2>
            <div className="site-actions">
              <a
                className="button secondary"
                href={"/grc-site?preview=" + encodeURIComponent(selected.name)}
                target="_blank"
                rel="noreferrer"
              >
                {label("Preview site", "معاينة الموقع")}
              </a>
              <Button variant="secondary" onClick={() => setSelected(undefined)}>
                {label("Close", "إغلاق")}
              </Button>
            </div>
          </div>
          <p>
            {translate(selected.status)} · {label("Submitted by", "قدّمه")} {selected.submitted_by || "—"} ·{" "}
            {label("Approval step", "خطوة الاعتماد")} {Math.min(selected.step + 1, selected.workflow.length)}{" "}
            / {selected.workflow.length}
          </p>
          {selected.status === "Pending" && (
            <>
              <p>
                {label("Required role", "الدور المطلوب")}: {selected.workflow[selected.step]}
              </p>
              <label>
                {label("Decision comment (required for rejection)", "تعليق القرار (مطلوب عند الرفض)")}
                <textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} />
              </label>
              <div className="site-actions">
                <Button
                  disabled={
                    busy ||
                    (!selected.allow_submitter_approval && selected.submitted_by === session.user) ||
                    !data.roles.includes(selected.workflow[selected.step])
                  }
                  onClick={() =>
                    void run(async () => {
                      await decide.execute({ name: selected.name, decision: "Approve", comment });
                      setSelected(undefined);
                      await mutate();
                    })
                  }
                >
                  {label("Approve", "اعتماد")}
                </Button>
                <Button
                  variant="secondary"
                  disabled={
                    busy ||
                    (!selected.allow_submitter_approval && selected.submitted_by === session.user) ||
                    !data.roles.includes(selected.workflow[selected.step]) ||
                    !comment.trim()
                  }
                  onClick={() =>
                    void run(async () => {
                      await decide.execute({ name: selected.name, decision: "Reject", comment });
                      setSelected(undefined);
                      await mutate();
                    })
                  }
                >
                  {label("Reject", "رفض")}
                </Button>
              </div>
              {data.is_admin && (
                <Button
                  variant="secondary"
                  disabled={busy || !comment.trim()}
                  onClick={() =>
                    void run(async () => {
                      await cancel.execute({ name: selected.name, comment });
                      setSelected(undefined);
                      await mutate();
                    })
                  }
                >
                  {label("Cancel submission", "إلغاء الطلب")}
                </Button>
              )}
              <p>
                {selected.allow_submitter_approval
                  ? label(
                      "The submitted workflow allows the submitter to decide when they hold the required role.",
                      "يسمح مسار الاعتماد المرسل لمقدم الطلب باتخاذ القرار إذا كان يحمل الدور المطلوب.",
                    )
                  : label(
                      "The submitter cannot decide their own submission. Administrators can cancel a blocked submission with a reason.",
                      "لا يمكن لمقدم الطلب اتخاذ قرار بشأن طلبه. يمكن للمدير إلغاء الطلب المتعثر مع توضيح السبب.",
                    )}
              </p>
            </>
          )}
          {data.can_edit && (
            <div className="site-actions">
              <Button
                variant="secondary"
                disabled={!!data.draft || selected.status === "Pending"}
                onClick={() => {
                  if (
                    changed &&
                    !window.confirm(
                      label(
                        "Replace unsaved changes with this revision?",
                        "هل تريد استبدال التغييرات غير المحفوظة بهذا الإصدار؟",
                      ),
                    )
                  )
                    return;
                  const next: SiteContent = { ...selected.content };
                  for (const [key, item] of Object.entries(entries))
                    next[key] = selected.content[key] || { en: item.en, ar: item.ar };
                  setContent(next);
                  setName(undefined);
                  setModified(undefined);
                  setSelected(undefined);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                {label("Create draft from this revision", "إنشاء مسودة من هذا الإصدار")}
              </Button>
              {data.draft && (
                <span>{label("Discard the existing draft first.", "ألغِ المسودة الحالية أولاً.")}</span>
              )}
            </div>
          )}
          <details>
            <summary>{label("View full bilingual snapshot", "عرض النسخة الكاملة باللغتين")}</summary>
            <div className="site-fields">
              {Object.entries(selected.content).map(([key, value]) => (
                <article className="site-field" key={key}>
                  <strong>{entries[key]?.en || key}</strong>
                  <p dir="ltr">{value.en}</p>
                  <p dir="rtl">{value.ar}</p>
                </article>
              ))}
            </div>
          </details>
        </section>
      )}
      <section className="panel padded">
        <h2>{label("Audit history", "سجل التدقيق")}</h2>
        <p>
          {label(
            "Each save, submission, decision, publication and workflow change records its actor and timestamp. Expand an entry to inspect changes.",
            "يُسجل كل حفظ وإرسال وقرار ونشر وتغيير في المسار مع المنفذ والوقت. وسّع السجل لفحص التغييرات.",
          )}
        </p>
        {data.events.map((e) => (
          <details className="site-event" key={e.name}>
            <summary>
              {String(e.creation).slice(0, 19)} · {e.actor} ·{" "}
              {translate(e.action === "Published" ? "Published event" : e.action)} {e.revision || ""}
            </summary>
            <pre dir="ltr">{JSON.stringify(JSON.parse(e.details || "{}"), null, 2)}</pre>
          </details>
        ))}
        <div className="site-actions">
          <Button variant="secondary" disabled={eventPage === 1} onClick={() => setEventPage(eventPage - 1)}>
            {label("Previous", "السابق")}
          </Button>
          <span>{eventPage}</span>
          <Button
            variant="secondary"
            disabled={!data.events_more}
            onClick={() => setEventPage(eventPage + 1)}
          >
            {label("Next", "التالي")}
          </Button>
        </div>
      </section>
    </div>
  );
}
