import { assessmentMilestones } from "../assessmentMilestones";
import Select from "../Select";
import AssessmentTypeChoice from "../AssessmentTypeChoice";
import StaffWelcome from "../StaffWelcome";
import { Navigate } from "react-router-dom";
import { activeAssessmentTemplates } from "../assessmentTemplates";
import { useEffect, useRef, useState } from "react";
import { useAssessmentTypes } from "../assessmentTypes";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  AlertCircle,
  Plus,
} from "lucide-react";
import { useData, useMutation } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import {
  Button,
  Empty,
  ErrorNotice,
  Field,
  Form,
  Loading,
  Modal,
  PageTitle,
  Pagination,
  SearchInput,
  Status,
  Table,
} from "../components";
import { SectorSelect } from "../components";
import type { DashboardData } from "../types";

export function OrganizationSetup() {
  const { t } = useLanguage(),
    { session, refresh } = useSession(),
    save = useMutation("save_organization");
  if (session.pending_auditor_invitations) return <Navigate to={session.home + "/onboarding"} replace />;
  if (session.pending_onboarding?.length)
    return (
      <section className="panel padded">
        <h2>{t("Onboarding awaiting approval")}</h2>
        <p>
          {t(
            "Your organization request has been received. An authorized reviewer will decide it before access is activated.",
          )}
        </p>
      </section>
    );
  return (
    <section className="onboarding panel">
      <div className="onboarding-illustration">
        <ClipboardCheck size={38} />
        <span>01</span>
      </div>
      <h2>{t("Set up your organization")}</h2>
      <p>{t("Create your organization profile to start an assessment and invite colleagues.")}</p>
      {session.signup_organization && (
        <p className="notice">
          {t(
            "Your email is verified. To join an existing organization, ask its administrator for an invitation. You can also create a new organization with a different name.",
          )}
        </p>
      )}
      <Form
        onSubmit={async (data) => {
          await save.execute({ data });
          refresh();
        }}
      >
        <Field label="Organization name">
          <input
            name="entity_name"
            required
            maxLength={140}
            defaultValue={session.signup_organization?.entity_name}
          />
        </Field>
        <div className="form-grid">
          <Field label="Sector">
            <SectorSelect required defaultValue={session.signup_organization?.sector} />
          </Field>
          <Field label="Contact email">
            <input name="contact_email" type="email" defaultValue={session.user} required />
          </Field>
        </div>
        <Button type="submit">
          {t("Create organization")}
          <ArrowRight size={16} />
        </Button>
      </Form>
    </section>
  );
}
export function StartAssessment({
  onClose,
  onDone,
  initialType = "",
  fromFirstChoice = false,
}: {
  onClose: () => void;
  onDone?: (name: string) => void;
  initialType?: string;
  fromFirstChoice?: boolean;
}) {
  const { session, activeOrganization } = useSession(),
    { t } = useLanguage(),
    navigate = useNavigate(),
    create = useMutation("start_assessment"),
    assessmentTypes = useAssessmentTypes();
  const organizations =
    session.organizations?.filter(
      (o) =>
        session.is_admin ||
        (session.kind === "Auditor"
          ? session.assignments?.some(
              (a) => a.entity === o.name && ["Manager", "Consultant"].includes(a.responsibility),
            )
          : session.memberships?.some((m) => m.entity === o.name && m.membership_role !== "Viewer")),
    ) || [];
  const [entity, setEntity] = useState(
    organizations.some((o) => o.name === activeOrganization)
      ? activeOrganization
      : organizations[0]?.name || "",
  );
  const granted = session.audit_type_access?.[entity] || session.allowed_assessment_types || [];
  const allowed =
    session.kind === "Auditor" && !session.is_admin
      ? session.department_memberships?.map((d) => d.department) || granted
      : granted;
  const availableTypes = allowed.length
    ? allowed
    : session.kind === "Auditor" && !session.is_admin
      ? []
      : assessmentTypes.names;
  const [chosenType, setAssessmentType] = useState(initialType);
  const assessmentType =
    availableTypes.length === 1 ? availableTypes[0] : availableTypes.includes(chosenType) ? chosenType : "";
  const { data: templates } = useData<any[]>("templates", { assessment_type: assessmentType || undefined });
  const availableTemplates = activeAssessmentTemplates(templates).filter(
    (a) => assessmentType && (a.assessment_type || "Internal Audit") === assessmentType,
  );
  const defaultTemplate = availableTemplates.find((a) => a.is_default)?.name || availableTemplates[0]?.name;
  // The type was already chosen on the dashboard: with one organization and a default template
  // there is nothing left to confirm, so start straight away instead of asking again.
  const autoStart =
    fromFirstChoice &&
    !!initialType &&
    assessmentType === initialType &&
    session.kind !== "Auditor" &&
    organizations.length === 1 &&
    !!defaultTemplate;
  const [autoFailed, setAutoFailed] = useState<unknown>();
  const started = useRef(false);
  useEffect(() => {
    if (!autoStart || started.current) return;
    started.current = true;
    create
      .execute({ assessment_type: assessmentType, entity: organizations[0].name, template: defaultTemplate })
      .then((result: { name: string }) => {
        onDone?.(result.name);
        navigate(session.home + "/assessments/" + encodeURIComponent(result.name));
        onClose();
      })
      .catch(setAutoFailed);
  }, [autoStart]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!organizations.length)
    return (
      <Modal title="Start assessment" onClose={onClose}>
        <Empty
          title="No customers assigned"
          text="An assigned customer organization is needed before you can start an assessment. Invite a customer or ask your department manager for an assignment."
        />
        <Button variant="secondary" onClick={onClose}>
          {t("Close")}
        </Button>
      </Modal>
    );
  if (autoStart && !autoFailed)
    return (
      <Modal title="Start assessment" onClose={onClose}>
        <Loading />
      </Modal>
    );
  return (
    <Modal title="Start assessment" onClose={onClose}>
      {!!autoFailed && <ErrorNotice error={autoFailed} />}
      <Form
        onSubmit={async (data) => {
          const result = await create.execute(data);
          onDone?.(result.name);
          navigate(session.home + "/assessments/" + encodeURIComponent(result.name));
          onClose();
        }}
      >
        {availableTypes.length > 1 && !(fromFirstChoice && initialType && assessmentType === initialType) ? (
          <AssessmentTypeChoice
            value={assessmentType}
            onChange={setAssessmentType}
            allowedTypes={availableTypes}
          />
        ) : (
          <p className="notice">
            {t("Assessment type")}: {assessmentTypes.label(assessmentType)}
          </p>
        )}
        <input type="hidden" name="assessment_type" value={assessmentType} />
        {organizations.length > 1 ? (
          <Field label="Organization">
            <Select name="entity" required value={entity} onChange={(e) => setEntity(e.target.value)}>
              {organizations.map((o) => (
                <option key={o.name} value={o.name}>
                  {o.entity_name}
                </option>
              ))}
            </Select>
          </Field>
        ) : (
          <>
            <input type="hidden" name="entity" value={entity} />
            <p>{organizations[0]?.entity_name}</p>
          </>
        )}
        {session.kind === "Auditor" ? (
          <Field label="Template">
            <Select
              name="template"
              required
              disabled={!availableTemplates.length}
              key={defaultTemplate || "loading"}
              defaultValue={defaultTemplate}
            >
              {availableTemplates.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.template_name} · v{a.version}
                  {a.is_default ? ` · ${t("Default")}` : ""}
                </option>
              ))}
            </Select>
          </Field>
        ) : (
          <input type="hidden" name="template" value={defaultTemplate || ""} />
        )}
        {session.kind === "Auditor" && (
          <>
            <Field label="Customer owner">
              <input name="respondent" type="email" />
            </Field>
            <p className="muted">
              {t("Leave blank to prepare a draft before inviting a customer administrator.")}
            </p>
          </>
        )}
        {!assessmentType && (
          <p className="notice">
            {t(
              "Choose an audit type to see the available assessment. No draft is created until you select Start assessment.",
            )}
          </p>
        )}
        {templates && assessmentType && !availableTemplates.length && (
          <p className="notice">
            {t("No active published assessment templates are available.")}{" "}
            {t(
              "Choose another available audit type or ask your department team to publish a template. You can close this window and return later.",
            )}
          </p>
        )}
        <div className="row-actions">
          <Button type="submit" disabled={!availableTemplates.length}>
            {t("Start assessment")}
            <ArrowRight size={16} />
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </div>
      </Form>
    </Modal>
  );
}
export default function Dashboard({
  listOnly = false,
  reports = false,
}: {
  listOnly?: boolean;
  reports?: boolean;
}) {
  const { session, activeOrganization, setOrganization } = useSession(),
    { t } = useLanguage(),
    [params, setParams] = useSearchParams(),
    [start, setStart] = useState(false);
  const [entryType, setEntryType] = useState("");
  const [startFromEntry, setStartFromEntry] = useState(false);
  const search = params.get("search") || "",
    entity = params.get("entity") ?? activeOrganization,
    state = params.get("state") || "",
    group = params.get("group") || "",
    page = Math.max(1, Number(params.get("page")) || 1);
  const update = (key: string, value: string) =>
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.delete("page");
      if (key === "state") next.delete("group");
      return next;
    });
  const setSearch = (v: string) => update("search", v),
    setEntity = (v: string) => update("entity", v),
    setState = (v: string) => update("state", v),
    setPage = (v: number) => update("page", String(v));
  const groupLabels: Record<string, string> = {
    in_progress: "In progress",
    awaiting_review: "Awaiting review",
    overdue: "Overdue",
    released: "Reports released",
  };
  const assessmentLink = (filter: string) => session.home + "/assessments?group=" + filter;
  const customerLink =
    session.home +
    "/customers" +
    (session.organizations?.length === 1 ? "/" + encodeURIComponent(session.organizations[0].name) : "");
  const { data, error } = useData<DashboardData>(
    "dashboard",
    { entity: entity || undefined, search, state, group, page, scorecards: reports ? 1 : 0 },
    30000,
  );
  const auditor = session.kind === "Auditor",
    title = reports
      ? "Scorecards"
      : listOnly
        ? "Assessments"
        : auditor
          ? "My review queue"
          : "Your assessments";
  const granted =
    session.audit_type_access?.[entity || session.organizations?.[0]?.name || ""] ||
    session.allowed_assessment_types ||
    [];
  if (!auditor && !session.organizations?.length && session.pending_auditor_invitations)
    return <Navigate to={session.home + "/onboarding"} replace />;
  if (!auditor && !session.organizations?.length && session.pending_onboarding?.length)
    return (
      <section className="panel padded">
        <h1>{t("Onboarding awaiting approval")}</h1>
        <p>
          {t(
            "Your organization request has been received. An authorized reviewer will decide it before access is activated.",
          )}
        </p>
      </section>
    );
  if (!auditor && !session.organizations?.length) return <OrganizationSetup />;
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const counts = data.counts,
    next = data.assessments.find(
      (a) =>
        a.editable ||
        a.review_actions.length > 0 ||
        (!auditor &&
          a.current !== false &&
          ["Draft", "In Progress", "Clarification Required"].includes(a.state)),
    );
  const eligibleOrganizations =
    session.organizations?.filter(
      (o) =>
        session.is_admin ||
        session.assignments?.some(
          (a) => a.entity === o.name && ["Manager", "Consultant"].includes(a.responsibility),
        ),
    ) || [];
  const canStart = auditor
    ? eligibleOrganizations.length > 0
    : session.memberships?.some((m) => m.membership_role !== "Viewer");
  const managementScope = auditor && !!session.can_manage_departments;
  const filtered = !!(search || state || group || entity),
    latest = data.assessments[0];
  const waiting =
    !!latest &&
    !latest.editable &&
    !next &&
    ["Submitted", "Resubmitted", "Under Review", "Approved", "Report Released"].includes(latest.state);
  const clearFilters = () => {
    setOrganization("");
    setParams(new URLSearchParams());
  };
  return (
    <>
      <PageTitle
        eyebrow={auditor ? "Auditor workspace" : "Customer workspace"}
        title={title}
        description={
          auditor
            ? managementScope
              ? "Customers and assessments available within your department management scope."
              : "Only customers assigned to you appear in this workspace."
            : undefined
        }
      >
        {canStart && !reports && (
          <Button
            onClick={() => {
              setStartFromEntry(false);
              setStart(true);
            }}
          >
            <Plus size={17} />
            {t("Start assessment")}
          </Button>
        )}
        {session.is_admin && (
          <Link className="button secondary" to={session.home + "/admin/assignments"}>
            {t("Assign customer")}
          </Link>
        )}
      </PageTitle>
      {auditor && !listOnly && !reports && <StaffWelcome empty={!session.organizations?.length} />}
      {!auditor && !listOnly && !reports && waiting && (
        <section className="next-action">
          <div>
            <span className="eyebrow light">{t("Your next action")}</span>
            <h2>
              {t(
                latest.state === "Report Released"
                  ? "Your official report is ready"
                  : latest.state === "Approved"
                    ? "Your assessment is approved"
                    : "Your assessment is with the review team",
              )}
            </h2>
            <p>
              {t(
                latest.state === "Report Released"
                  ? "Open the assessment to download or email the official report."
                  : latest.state === "Approved"
                    ? "The review team will release the official report. Open the assessment for available results and report options."
                    : "Your submitted answers are locked. Open the assessment for available results, or wait for the team to request clarification.",
              )}
            </p>
          </div>
          <Link className="button white" to={session.home + "/assessments/" + latest.name}>
            {t("View assessment and results")}
            <ArrowUpRight size={17} />
          </Link>
        </section>
      )}
      {!listOnly && !reports && !auditor && canStart && !data.assessments.length && !filtered && (
        <section className="panel padded">
          <h2>{t("Choose your assessment")}</h2>
          <AssessmentTypeChoice
            value={entryType || (granted.length === 1 ? granted[0] : "")}
            onChange={setEntryType}
            allowedTypes={granted.length ? granted : undefined}
          />
          <Button
            disabled={!entryType && granted.length !== 1}
            onClick={() => {
              setStartFromEntry(true);
              setStart(true);
            }}
          >
            {t("Continue")}
          </Button>
        </section>
      )}
      {!listOnly && !reports && (
        <>
          {!auditor && next && (
            <section className="next-action">
              <div>
                <span className="eyebrow light">{t("Your next action")}</span>
                <h2>
                  {next.state === "Clarification Required"
                    ? t("Clarification Required")
                    : t("Keep your assessment moving")}
                </h2>
                <p>
                  {next.entity} · {next.answered_count}/{next.question_count} {t("Questions")}
                </p>
                {next.profile_required && (
                  <p>
                    {t(
                      "Complete your company profile to continue this assessment. Your existing draft is saved.",
                    )}
                  </p>
                )}
              </div>
              <Link className="button white" to={session.home + "/assessments/" + next.name}>
                {t(
                  next.editable || ["Draft", "In Progress", "Clarification Required"].includes(next.state)
                    ? "Continue assessment"
                    : "Review assessment",
                )}
                <ArrowUpRight size={17} />
              </Link>
            </section>
          )}
          <div className="stat-grid">
            {[
              [
                auditor ? (managementScope ? "Available customers" : "Assigned customers") : "In progress",
                auditor ? data.customer_count : (counts.Draft || 0) + (counts["In Progress"] || 0),
                ClipboardCheck,
                auditor ? customerLink : assessmentLink("in_progress"),
              ],
              [
                "Awaiting review",
                (counts.Submitted || 0) + (counts.Resubmitted || 0) + (counts["Under Review"] || 0),
                Clock3,
                assessmentLink("awaiting_review"),
              ],
              ["Overdue", data.overdue, AlertCircle, assessmentLink("overdue")],
              ["Reports released", counts["Report Released"] || 0, FileCheck2, assessmentLink("released")],
            ].map(([label, value, Icon, to]: any) => (
              <Link className="stat-card" key={label} to={to} aria-label={t(label) + ": " + value}>
                <div>
                  <span>{t(label)}</span>
                  <strong>{value}</strong>
                </div>
                <Icon size={21} />
                <ArrowUpRight className="stat-card-arrow" size={15} />
              </Link>
            ))}
          </div>
        </>
      )}
      {!listOnly && !reports && (data.overdue_actions_count > 0 || data.recent_activity.length > 0) && (
        <div className="dashboard-context">
          <section className="panel">
            <div className="panel-heading">
              <h2>
                {t("Overdue improvement actions")}{" "}
                <span className="muted">({data.overdue_actions_count})</span>
              </h2>
              <Link to={session.home + "/actions"}>{t("Open")}</Link>
            </div>
            {data.overdue_actions.length ? (
              <ul className="dashboard-items">
                {data.overdue_actions.map((a) => (
                  <li key={a.name}>
                    <Link to={session.home + "/actions"}>{a.finding_title}</Link>
                    <small>
                      {a.entity} · {a.due_date}
                    </small>
                    <Status value={a.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="dashboard-empty muted">{t("No overdue improvement actions.")}</p>
            )}
          </section>
          <section className="panel">
            <div className="panel-heading">
              <h2>{t(auditor ? "Review timeline" : "Assessment dates")}</h2>
              <Link to={session.home + "/activity"}>{t(auditor ? "Activity" : "Assessment dates")}</Link>
            </div>
            <ol className="dashboard-items">
              {(auditor ? data.recent_activity : assessmentMilestones(data.recent_activity)).map((a) => (
                <li key={a.name}>
                  <strong>{t(a.action)}</strong>
                  <small>
                    {a.entity} ·{" "}
                    {auditor
                      ? new Date(a.creation).toLocaleDateString()
                      : new Date(a.creation).toLocaleString()}
                  </small>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{t(reports ? "Scorecards" : auditor ? "Customer portfolio" : "Assessment progress")}</h2>
            <span className="muted">
              {data.total} {t("Assessments")}
            </span>
          </div>
        </div>
        {group && groupLabels[group] && (
          <div className="active-filter">
            <span>
              {t("Filtered by")}: <strong>{t(groupLabels[group])}</strong>
            </span>
            <Button variant="ghost" onClick={() => update("group", "")}>
              {t("Clear filter")}
            </Button>
          </div>
        )}
        {!auditor || session.organizations?.length || search || state || group || entity ? (
          <>
            <div className="toolbar">
              <SearchInput
                value={search}
                onChange={(s) => {
                  setSearch(s);
                }}
              />
              <div className="toolbar-filters">
                {!!session.organizations?.length && (
                  <Select
                    aria-label={t("Organization")}
                    value={entity}
                    onChange={(e) => {
                      setEntity(e.target.value);
                    }}
                  >
                    <option value="">{t("All organizations")}</option>
                    {session.organizations?.map((o) => (
                      <option key={o.name} value={o.name}>
                        {o.entity_name}
                      </option>
                    ))}
                  </Select>
                )}
                {!reports && (
                  <Select
                    aria-label={t("Status")}
                    value={state}
                    onChange={(e) => {
                      setState(e.target.value);
                    }}
                  >
                    <option value="">{t("All statuses")}</option>
                    {[
                      "Draft",
                      "In Progress",
                      "Submitted",
                      "Under Review",
                      "Clarification Required",
                      "Resubmitted",
                      "Approved",
                      "Report Released",
                    ].map((s) => (
                      <option key={s} value={s}>
                        {t(s)}
                      </option>
                    ))}
                  </Select>
                )}
              </div>
            </div>
            {auditor && (
              <p className="muted" style={{ padding: "0 24px" }}>
                {t(
                  "Filters are optional. Leave All organizations and All statuses selected to see all work available to you.",
                )}
              </p>
            )}
          </>
        ) : null}
        {!data.assessments.length ? (
          <Empty
            title={
              filtered
                ? "No matching assessments"
                : auditor && !data.customer_count
                  ? managementScope
                    ? "No customers in your management scope"
                    : "No customers assigned"
                  : reports
                    ? "No released reports yet"
                    : "No assessments yet"
            }
            text={
              filtered
                ? "No assessments match these filters. Clear the filters to see all work available to you."
                : auditor && !data.customer_count
                  ? managementScope
                    ? "Invite a customer for your department, or review department access and customer assignments if an existing customer should appear."
                    : session.can_invite_customers
                      ? "Invite a customer through Customer onboarding, or ask your department manager to assign an existing customer. No selection is required here."
                      : "Your department manager will assign customer organizations and assessments to you. Contact your department manager if you are waiting for work."
                  : reports
                    ? "Your approved scorecards and reports will appear here."
                    : canStart
                      ? "Choose your audit type and start an assessment. You can save your answers and return later."
                      : "Your organization administrator or department team must assign an assessment before you can begin."
            }
          >
            {filtered && (
              <Button variant="secondary" onClick={clearFilters}>
                {t("Clear filters")}
              </Button>
            )}
          </Empty>
        ) : (
          <Table headers={["Assessment", "Status", "Progress", "Due date", "Owner", ""]}>
            {data.assessments.map((a) => (
              <tr key={a.name}>
                <td>
                  <Link className="record-link" to={session.home + "/assessments/" + a.name}>
                    {a.entity}
                    <ArrowUpRight size={14} />
                  </Link>
                  <small>{a.name}</small>
                </td>
                <td>
                  <Status value={a.state} />
                  {a.needs_reassignment && session.is_admin && (
                    <small className="warning-text">{t("Assign team")}</small>
                  )}
                </td>
                <td>
                  <div className="table-progress">
                    <span>{Math.round((a.answered_count / Math.max(1, a.question_count)) * 100)}%</span>
                    <div className="progress-track">
                      <span
                        style={{ width: (a.answered_count / Math.max(1, a.question_count)) * 100 + "%" }}
                      />
                    </div>
                  </div>
                </td>
                <td>{a.due_date || "—"}</td>
                <td>
                  <span className="owner-cell">
                    <span className="avatar small">{(a.respondent_name || a.respondent).slice(0, 1)}</span>
                    {a.respondent_name || a.respondent}
                  </span>
                </td>
                <td>
                  <Link className="button ghost" to={session.home + "/assessments/" + a.name}>
                    {t("Open")}
                    <ArrowRight size={15} />
                  </Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
        <Pagination page={page} total={data.total} onPage={setPage} />
      </section>
      {start && (
        <StartAssessment
          initialType={startFromEntry ? entryType || (granted.length === 1 ? granted[0] : "") : ""}
          fromFirstChoice={startFromEntry}
          onClose={() => setStart(false)}
        />
      )}
    </>
  );
}
