import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Eye } from "lucide-react";
import { useData } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { useAssessmentTypes } from "../assessmentTypes";
import { Empty, ErrorNotice, Loading, PageTitle, SearchInput, Table } from "../components";
import "./reports.css";

type ReportRow = {
  name: string;
  entity: string;
  report_id: string;
  assessment_type?: string;
  overall_score?: number;
  maturity_level?: string;
  modified: string;
  state?: string;
  released?: boolean;
  can_download_report?: boolean;
};

/** Reports this user may view (role-based for staff; release policy for customers). */
export function ReportsPage() {
  const { session } = useSession(),
    { t } = useLanguage(),
    types = useAssessmentTypes(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const { data, error } = useData<{ rows: ReportRow[]; page: number; has_more: boolean }>(
    "report_list",
    { search, page },
    30000,
  );
  return (
    <>
      <PageTitle
        title="Reports"
        description="Assessment reports you are allowed to view. Access follows your role and your organizations and departments."
      />
      <section className="panel">
        <div className="toolbar">
          <SearchInput value={search} onChange={(v: string) => (setSearch(v), setPage(1))} />
        </div>
        {error && <ErrorNotice error={error} />}
        {!data && !error && <Loading />}
        {data && !data.rows.length && (
          <Empty title="No reports yet" text="Reports appear here once an assessment is submitted." />
        )}
        {data && !!data.rows.length && (
          <div className="table-scroll">
            <Table headers={["Report ID", "Organization", "Type", "Score", "Status", ""]}>
              {data.rows.map((row) => (
                <tr key={row.name}>
                  <td>
                    <code>{row.report_id}</code>
                  </td>
                  <td>{row.entity}</td>
                  <td>{types.label(row.assessment_type || "Internal Audit")}</td>
                  <td>
                    {row.overall_score != null ? Math.round(row.overall_score) + "%" : "—"}
                    {row.maturity_level ? " · " + t(row.maturity_level) : ""}
                  </td>
                  <td>{t(row.released ? "Report Released" : row.state || "Submitted")}</td>
                  <td className="row-actions">
                    <Link
                      className="button secondary"
                      to={session.home + "/assessments/" + row.name + "/report"}
                    >
                      <Eye size={15} />
                      {t("View report")}
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        )}
        {data && (page > 1 || data.has_more) && (
          <div className="row-actions reports-pager">
            <button className="button secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              {t("Previous")}
            </button>
            <button className="button secondary" disabled={!data.has_more} onClick={() => setPage(page + 1)}>
              {t("Next")}
            </button>
          </div>
        )}
      </section>
    </>
  );
}

type Section = {
  title: string;
  pct: number;
  points?: number;
  max_points?: number;
  color: string;
  level_label?: string;
};
type ReportView = {
  assessment: string;
  report_id: string;
  lang: string;
  dir: string;
  t: Record<string, string>;
  entity: string;
  date?: string;
  respondent?: string;
  questions_text?: string;
  preliminary?: boolean;
  overall: number;
  level_label?: string;
  level_color?: string;
  points_text?: string;
  interpretation?: string;
  findings_text?: string;
  gating_note?: string;
  strongest?: { title: string; pct: number };
  weakest?: { title: string; pct: number };
  sections?: Section[];
  show?: Record<string, boolean>;
  scoring_text?: string;
  can_download_report?: boolean;
};

/** The report on screen: the same content as the PDF (frozen release data when released). */
export function ReportViewPage() {
  const { name } = useParams(),
    { session } = useSession(),
    { t } = useLanguage();
  const { data, error } = useData<ReportView>("report_view", { name });
  const back = (
    <Link className="back-link" to={session.home + "/assessments/" + name}>
      <ArrowLeft size={15} />
      {t("Back to assessment")}
    </Link>
  );
  if (error)
    return (
      <>
        {back}
        <ErrorNotice error={error} />
      </>
    );
  if (!data) return <Loading />;
  const r = data,
    pct = (value?: number) => (value == null ? "—" : `${Number(value.toFixed(1))}%`);
  return (
    <div className="report-view" dir={r.dir} lang={r.lang}>
      {back}
      <PageTitle
        eyebrow={r.t.results_report || "Results report"}
        title={r.t.title || "Assessment report"}
        description={r.entity}
      >
        {r.can_download_report && (
          <a
            className="button primary"
            href={"/api/method/ia_maturity.grc.api.download_report?name=" + encodeURIComponent(r.assessment)}
          >
            <Download size={16} />
            {t("Download PDF")}
          </a>
        )}
      </PageTitle>
      {r.preliminary && (
        <p className="notice">
          {r.lang === "ar"
            ? "تقرير أولي — لم تتم مراجعته أو اعتماده"
            : "Preliminary — not reviewed or approved"}
        </p>
      )}
      <section className="panel padded report-meta">
        <dl>
          <div>
            <dt>{r.t.assessment_date || "Assessment date"}</dt>
            <dd>{r.date || "—"}</dd>
          </div>
          <div>
            <dt>{r.t.assessed_by || "Assessed by"}</dt>
            <dd>{r.respondent || "—"}</dd>
          </div>
          <div>
            <dt>{r.t.questions || "Questions"}</dt>
            <dd>{r.questions_text || "—"}</dd>
          </div>
          <div>
            <dt>{r.lang === "ar" ? "رقم التقرير" : "Report ID"}</dt>
            <dd>
              <code>{r.report_id}</code>
            </dd>
          </div>
        </dl>
      </section>
      {r.show?.summary !== false && (
        <section className="panel padded report-summary">
          <h2>{r.t.exec_summary || "Executive summary"}</h2>
          <div className="report-score">
            <strong style={{ color: r.level_color }}>
              {Number(r.overall.toFixed(1))}
              <small>%</small>
            </strong>
            {r.level_label && (
              <span className="report-level" style={{ borderColor: r.level_color, color: r.level_color }}>
                {r.level_label}
              </span>
            )}
            {r.points_text && <span className="muted">{r.points_text}</span>}
          </div>
          <div>
            {r.interpretation && <p>{r.interpretation}</p>}
            {r.strongest && r.weakest && (
              <p className="muted">
                {r.t.strongest}: <b>{r.strongest.title}</b> ({pct(r.strongest.pct)}). {r.t.weakest}:{" "}
                <b>{r.weakest.title}</b> ({pct(r.weakest.pct)}). {r.findings_text}
              </p>
            )}
            {r.gating_note && <p className="notice">{r.gating_note}</p>}
          </div>
        </section>
      )}
      {r.show?.sections !== false && !!r.sections?.length && (
        <section className="panel padded">
          <h2>{r.t.results_by_section || "Results by section"}</h2>
          <div className="report-bars" role="img" aria-label={r.t.results_by_section || "Results by section"}>
            {r.sections.map((s, i) => (
              <div className="report-bar" key={i}>
                <span>{s.title}</span>
                <div className="report-bar-track">
                  <div style={{ width: Math.max(0, Math.min(100, s.pct)) + "%", background: s.color }} />
                </div>
                <b>{pct(s.pct)}</b>
              </div>
            ))}
          </div>
          <div className="table-scroll">
            <Table
              headers={[
                "#",
                r.t.section || "Section",
                r.t.points || "Points",
                r.t.score || "Score",
                r.t.maturity || "Maturity",
              ]}
            >
              {r.sections.map((s, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{s.title}</td>
                  <td>
                    {s.points ?? "—"} / {s.max_points ?? "—"}
                  </td>
                  <td>{pct(s.pct)}</td>
                  <td>
                    <span className="report-level" style={{ borderColor: s.color, color: s.color }}>
                      {s.level_label}
                    </span>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </section>
      )}
      {r.show?.scoring_method && r.scoring_text && (
        <section className="panel padded">
          <h2>{r.t.scoring_method || "Scoring method"}</h2>
          <p className="muted">{r.scoring_text}</p>
        </section>
      )}
    </div>
  );
}
