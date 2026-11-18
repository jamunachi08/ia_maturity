import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { Building2, ClipboardList, LayoutDashboard, ArrowRight, Globe2, Eye, FileCheck2 } from "lucide-react";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import { PageTitle, Status } from "../components";

const examples = [
  {
    id: "DEMO-001",
    customer: "Riyadh Example Organization",
    ar: "منظمة الرياض الافتراضية",
    state: "Under Review",
    answered: 20,
    score: 75,
  },
  {
    id: "DEMO-002",
    customer: "Jeddah Example Organization",
    ar: "منظمة جدة الافتراضية",
    state: "In Progress",
    answered: 12,
    score: 60,
  },
];
export default function Demo() {
  const { session } = useSession(),
    { lang, setLang, t } = useLanguage(),
    { kind } = useParams(),
    [params, setParams] = useSearchParams(),
    ar = lang === "ar";
  if (kind !== "customer" && kind !== "auditor") return <Navigate to="/grc/demo/customer" replace />;
  if (session.kind === "Guest")
    return (
      <div className="standalone">
        <h1>{ar ? "عرض تجريبي للمنصة" : "GRC workspace preview"}</h1>
        <p>
          {ar
            ? "سجّل الدخول بحساب تخطيط الموارد لمشاهدة أمثلة افتراضية."
            : "Sign in with your ERP account to view fictional examples."}
        </p>
        <a className="button primary" href={"/login?next=/grc/demo/" + kind}>
          {t("Sign in")}
        </a>
      </div>
    );
  if (session.kind !== "ERP" && !session.is_admin) return <Navigate to={session.home} replace />;
  const auditor = kind === "auditor",
    view = params.get("view") || "overview",
    rows = auditor ? examples : examples.slice(0, 1);
  const title = ar
    ? auditor
      ? "عرض مساحة المدقق"
      : "عرض مساحة العميل"
    : auditor
      ? "Auditor workspace preview"
      : "Customer workspace preview";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/grc-site">
          <img src="/assets/ia_maturity/images/alphax_logo.png" alt="AlphaX" />
          <span>GRC</span>
        </Link>
        <div className="workspace-label">
          <Eye size={20} />
          <strong>{ar ? "عرض تجريبي" : "Demonstration"}</strong>
        </div>
        <nav>
          {[
            ["overview", "Overview", LayoutDashboard],
            ["assessments", "Assessments", ClipboardList],
            ["customers", "Assigned customers", Building2],
            ["scorecard", "Scorecards", FileCheck2],
          ]
            .filter(([v]) => auditor || v !== "customers")
            .map(([v, label, Icon]: any) => (
              <Link key={v} className={view === v ? "active" : ""} to={"?view=" + v}>
                <Icon size={18} />
                {t(label)}
              </Link>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <a href="/app">{ar ? "العودة إلى تخطيط الموارد" : "Return to ERP"}</a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <Link to={"/grc/demo/" + (auditor ? "customer" : "auditor")}>
            {ar
              ? auditor
                ? "عرض العميل"
                : "عرض المدقق"
              : auditor
                ? "View customer demo"
                : "View auditor demo"}
          </Link>
          <button className="button ghost" onClick={() => setLang(ar ? "en" : "ar")}>
            <Globe2 size={16} />
            {ar ? "English" : "العربية"}
          </button>
        </header>
        <main className="main-content">
          <div className="notice demo-notice">
            <Eye size={20} />
            <span>
              {ar
                ? "بيانات افتراضية للعرض فقط. لا يتم تحميل سجلات العملاء الحقيقية ولا يمكن حفظ أي تغييرات."
                : "Fictional, read-only demonstration. No real customer records are loaded and no changes can be saved."}
            </span>
          </div>
          <PageTitle title={title} />
          {view === "overview" && (
            <>
              <div className="demo-metrics">
                {[
                  [ar ? "العملاء" : "Customers", rows.length, "customers"],
                  [ar ? "التقييمات" : "Assessments", rows.length, "assessments"],
                  [ar ? "بانتظار المراجعة" : "Awaiting review", 1, "assessments"],
                  [ar ? "مثال لبطاقة النتائج" : "Sample scorecard", "75%", "scorecard"],
                ].map(([label, value, target]) => (
                  <button className="panel" key={label} onClick={() => setParams({ view: String(target) })}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                    <ArrowRight size={18} />
                  </button>
                ))}
              </div>
              <section className="panel padded">
                <h2>{ar ? "من التقييم إلى تقرير معتمد" : "From assessment to an approved report"}</h2>
                <p>
                  {ar
                    ? "استعرض مراحل العمل أدناه. هذا المثال لا يمنح صلاحيات للعملاء أو المراجعين."
                    : "Explore the workflow below. This example does not grant customer or reviewer permissions."}
                </p>
                <ol className="demo-flow">
                  {["Draft", "In Progress", "Submitted", "Under Review", "Approved", "Report Released"].map(
                    (s) => (
                      <li key={s}>
                        <Status value={s} />
                      </li>
                    ),
                  )}
                </ol>
              </section>
            </>
          )}
          {(view === "assessments" || view === "customers") && (
            <section className="panel padded">
              <h2>{t(view === "customers" ? "Assigned customers" : "Assessments")}</h2>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>{t("Organization")}</th>
                      <th>{t("Status")}</th>
                      <th>{ar ? "التقدم" : "Progress"}</th>
                      <th>{ar ? "الإجراء" : "Action"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {ar ? row.ar : row.customer}
                          <small className="muted"> · {row.id}</small>
                        </td>
                        <td>
                          <Status value={row.state} />
                        </td>
                        <td>{row.answered}/20</td>
                        <td>
                          <Link to="?view=scorecard">{ar ? "عرض المثال" : "View example"}</Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          {view === "scorecard" && (
            <section className="panel padded demo-scorecard">
              <span className="eyebrow">
                {ar ? "مثال توضيحي - ليس نتيجة حقيقية" : "ILLUSTRATIVE SAMPLE — NOT A REAL RESULT"}
              </span>
              <h2>{ar ? examples[0].ar : examples[0].customer}</h2>
              <strong>75%</strong>
              <p>
                {ar
                  ? "تعرض بطاقة النتائج المعتمدة المحاور الستة ومجالات التحسين. يتاح تقرير PDF الحقيقي بعد الموافقة والإصدار."
                  : "An approved scorecard shows all six sections and improvement areas. Real PDF reports become available after approval and release."}
              </p>
              {[80, 70, 75, 70, 80, 75].map((score, i) => (
                <div className="demo-section" key={i}>
                  <span>
                    {ar ? "المحور" : "Section"} {i + 1}
                  </span>
                  <progress value={score} max={100} />
                  <b>{score}%</b>
                </div>
              ))}
            </section>
          )}
          <Link className="button secondary" to="/grc-site">
            {ar ? "العودة إلى الموقع" : "Back to website"}
          </Link>
        </main>
      </div>
    </div>
  );
}
