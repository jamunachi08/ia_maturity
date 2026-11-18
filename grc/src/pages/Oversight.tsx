import { useState } from "react";
import { Link } from "react-router-dom";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import Select from "../Select";
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

type Policy = { onboarding: boolean; assignments: boolean; stages: string[]; allow_self: boolean };
function download(rows: any[], filename: string) {
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  const escape = (v: any) =>
    '"' +
    String(typeof v === "object" ? JSON.stringify(v) : (v ?? ""))
      .replaceAll('"', '""')
      .replace(/^[=+@-]/, "'$&") +
    '"';
  const csv =
    "\ufeff" +
    [keys.map(escape).join(","), ...rows.map((r) => keys.map((k) => escape(r[k])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
export default function Oversight() {
  const { t } = useLanguage(),
    { session } = useSession();
  const { data, error, mutate } = useData<any>("operations_overview");
  const [tab, setTab] = useState("customers"),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1),
    [dialog, setDialog] = useState<any>();
  const configure = useMutation("operations_configure"),
    decide = useMutation("operations_decide"),
    onboard = useMutation("operations_onboard_auditor");
  if (!session.can_operations && !session.is_admin)
    return (
      <Empty
        title="Access restricted"
        text="This overview is for authorized customer managers. Continue your assigned work from Overview, or ask your department manager for access."
      >
        <Link className="button secondary" to={session.home}>
          {t("Overview")}
        </Link>
      </Empty>
    );
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const rows = (
    tab === "customers" ? data.customers : tab === "auditors" ? data.auditors : data.requests
  ).filter((r: any) => JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));
  const canReview = (r: any) =>
    r.status === "Pending" &&
    (r.requested_by !== session.user || r.workflow.allow_self) &&
    (data.is_admin ||
      (r.workflow.stages[r.step] === "GRC Manager" &&
        data.assignments.some(
          (a: any) => a.entity === r.entity && a.auditor === session.user && a.responsibility === "Manager",
        )));
  const canCancel = (r: any) => r.status === "Pending" && (data.is_admin || r.requested_by === session.user);
  const openPolicy = (entity = "") =>
    setDialog({
      kind: "policy",
      entity,
      config: structuredClone(entity ? data.customer_policies[entity] : data.policy),
    });
  return (
    <>
      <PageTitle
        title="Customer and auditor overview"
        description="Only customers in your authorized department management scope appear here."
      >
        {data.is_admin && (
          <Button variant="secondary" onClick={() => openPolicy()}>
            {t("Global workflow")}
          </Button>
        )}
        <Button disabled={!data.customers.length} onClick={() => setDialog({ kind: "onboard" })}>
          {t("Request auditor onboarding")}
        </Button>
      </PageTitle>
      <p className="notice">
        {t(
          "Open a customer to inspect its work or manage its team. Check Approvals for requests awaiting an authorized decision. Search and section filters are optional.",
        )}
      </p>
      <div className="oversight-metrics">
        {[
          ["Customers", data.customers.length],
          ["Auditors", data.auditors.length],
          ["Pending approvals", data.requests.filter((r: any) => r.status === "Pending").length],
          ["Active assignments", data.assignments.length],
        ].map(([label, value]) => (
          <section className="panel padded" key={label}>
            <span>{t(String(label))}</span>
            <strong>{value}</strong>
          </section>
        ))}
      </div>
      <section className="panel">
        <div className="toolbar">
          <div className="oversight-tabs" role="tablist" aria-label={t("Overview sections")}>
            {["customers", "auditors", "approvals"].map((v) => (
              <Button
                key={v}
                role="tab"
                aria-selected={tab === v}
                variant={tab === v ? "primary" : "ghost"}
                onClick={() => {
                  setTab(v);
                  setSearch("");
                  setPage(1);
                }}
              >
                {t(v === "customers" ? "Customers" : v === "auditors" ? "Auditors" : "Approvals")}
              </Button>
            ))}
          </div>
          <SearchInput
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
          />
          <Button variant="secondary" onClick={() => download(rows, tab + ".csv")}>
            {t("Export CSV")}
          </Button>
        </div>
        {tab === "customers" ? (
          <Table headers={["Organization", "Sector", "Contact email", "Status", "Active assignments", ""]}>
            {rows.slice((page - 1) * 15, page * 15).map((r: any) => (
              <tr key={r.name}>
                <td>
                  <strong>{r.entity_name}</strong>
                  <small>{r.name}</small>
                </td>
                <td>{t(r.sector || "—")}</td>
                <td>{r.contact_email}</td>
                <td>
                  <Status value={r.is_active ? "Active" : "Inactive"} />
                </td>
                <td>{data.assignments.filter((a: any) => a.entity === r.name).length}</td>
                <td>
                  <div className="oversight-actions">
                    <Button variant="ghost" onClick={() => setDialog({ kind: "customer", name: r.name })}>
                      {t("View overview")}
                    </Button>
                    <Button variant="ghost" onClick={() => openPolicy(r.name)}>
                      {t("Workflow")}
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={!!r.ownership_locked}
                      onClick={() => setDialog({ kind: "assign", entity: r.name })}
                    >
                      {t("Assign customer")}
                    </Button>
                    {r.ownership_locked && (
                      <small className="muted">
                        {t("Ownership locked; ask an app administrator to review staff access.")}
                      </small>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </Table>
        ) : tab === "auditors" ? (
          <Table headers={["Name", "Email", "Role", "Status", "Last login", "Active assignments", ""]}>
            {rows.slice((page - 1) * 15, page * 15).map((r: any) => (
              <tr key={r.name}>
                <td>{r.full_name}</td>
                <td>{r.name}</td>
                <td>{r.roles.map((v: string) => t(v)).join(", ")}</td>
                <td>
                  <Status value={r.enabled ? "Active" : "Inactive"} />
                </td>
                <td>{r.last_login || "—"}</td>
                <td>{data.assignments.filter((a: any) => a.auditor === r.name).length}</td>
                <td>
                  <Button variant="ghost" onClick={() => setDialog({ kind: "auditor", name: r.name })}>
                    {t("View overview")}
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <Table
            headers={["Request", "Organization", "Requested by", "Status", "Approval stage", "Date", ""]}
          >
            {rows.slice((page - 1) * 15, page * 15).map((r: any) => (
              <tr key={r.name}>
                <td>
                  {t(r.kind)}
                  <small>{r.name}</small>
                </td>
                <td>
                  {data.customers.find((c: any) => c.name === r.entity)?.entity_name ||
                    r.payload.data?.entity_name ||
                    "—"}
                </td>
                <td>{r.requested_by}</td>
                <td>
                  <Status value={r.status} />
                </td>
                <td>{r.status === "Pending" ? t(r.workflow.stages[r.step]) : "—"}</td>
                <td>{r.creation?.slice(0, 16)}</td>
                <td>
                  <Button variant="ghost" onClick={() => setDialog({ kind: "request", request: r })}>
                    {t("Review request")}
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
        {!rows.length && (
          <Empty
            title={
              search
                ? "No matching records"
                : tab === "customers"
                  ? "No managed customers"
                  : tab === "auditors"
                    ? "No assigned staff yet"
                    : "No approval requests"
            }
            text={
              search
                ? "Clear the search or choose another section."
                : tab === "customers"
                  ? "No customers are currently in your authorized department management scope. Use Customer onboarding if permitted, or ask an app administrator to review your department access."
                  : tab === "auditors"
                    ? "Staff appear as customer assignments are created. Open a managed customer to review its team, or request auditor onboarding."
                    : "Pending requests appear here when an approval workflow requires a decision. You do not need to create a request to continue current work."
            }
          >
            {search ? (
              <Button variant="secondary" onClick={() => setSearch("")}>
                {t("Clear filter")}
              </Button>
            ) : (
              session.can_invite_customers &&
              tab === "customers" && (
                <Link className="button secondary" to={session.home + "/onboarding"}>
                  {t("Customer onboarding")}
                </Link>
              )
            )}
          </Empty>
        )}
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
      {dialog?.kind === "customer" || dialog?.kind === "auditor" ? (
        <Modal
          title={dialog.kind === "customer" ? "Customer overview" : "Auditor overview"}
          onClose={() => setDialog(undefined)}
        >
          <Detail kind={dialog.kind} name={dialog.name} assignments={data.assignments} />
        </Modal>
      ) : null}
      {dialog?.kind === "policy" && (
        <Modal title="Operations workflow" onClose={() => setDialog(undefined)}>
          <p>
            {dialog.entity
              ? data.customers.find((c: any) => c.name === dialog.entity)?.entity_name
              : t("Global workflow")}
          </p>
          <p className="muted">
            {t(
              "New requests freeze these approval stages. Existing pending requests keep their original workflow. Disabled controls apply changes immediately. Auditor onboarding requested by a manager always requires approval.",
            )}
          </p>
          <Form
            onSubmit={async () => {
              await configure.execute({ entity: dialog.entity || undefined, config: dialog.config });
              mutate();
              setDialog(undefined);
            }}
          >
            {(["onboarding", "assignments", "allow_self"] as const).map((key) => (
              <Field
                key={key}
                label={
                  key === "onboarding"
                    ? "Require onboarding approval"
                    : key === "assignments"
                      ? "Require assignment approval"
                      : "Allow requester to approve own request"
                }
              >
                <Select
                  value={Number(dialog.config[key])}
                  onChange={(e) =>
                    setDialog({ ...dialog, config: { ...dialog.config, [key]: e.target.value === "1" } })
                  }
                >
                  <option value="0">{t("No")}</option>
                  <option value="1">{t("Yes")}</option>
                </Select>
              </Field>
            ))}
            <p>
              {t(
                "Approval stages run in order. For example: Manager, then App administrator. Global onboarding requires an app administrator because no customer has been assigned yet.",
              )}
            </p>
            {(dialog.config as Policy).stages.map((stage, i) => (
              <div className="oversight-stage" key={i}>
                <Field label="Approval stage">
                  <Select
                    value={stage}
                    onChange={(e) => {
                      const stages = [...dialog.config.stages];
                      stages[i] = e.target.value;
                      setDialog({ ...dialog, config: { ...dialog.config, stages } });
                    }}
                  >
                    <option value="GRC App Admin">{t("GRC App Admin")}</option>
                    {dialog.entity && <option value="GRC Manager">{t("GRC Manager")}</option>}
                  </Select>
                </Field>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={dialog.config.stages.length === 1}
                  onClick={() =>
                    setDialog({
                      ...dialog,
                      config: {
                        ...dialog.config,
                        stages: dialog.config.stages.filter((_: string, n: number) => n !== i),
                      },
                    })
                  }
                >
                  {t("Remove")}
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="secondary"
              disabled={dialog.config.stages.length >= 5}
              onClick={() =>
                setDialog({
                  ...dialog,
                  config: { ...dialog.config, stages: [...dialog.config.stages, "GRC App Admin"] },
                })
              }
            >
              {t("Add approval stage")}
            </Button>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
      {dialog?.kind === "request" && (
        <Modal title="Review request" onClose={() => setDialog(undefined)}>
          <RequestSummary request={dialog.request} />
          {dialog.request.status === "Pending" && !canReview(dialog.request) && (
            <p className="notice">
              {t(
                dialog.request.requested_by === session.user && !dialog.request.workflow.allow_self
                  ? "A different authorized reviewer must decide your request. You may cancel it if no longer needed."
                  : "This request is waiting for the reviewer responsible for its current approval stage. You can inspect its history here.",
              )}
            </p>
          )}
          {(canReview(dialog.request) || canCancel(dialog.request)) && (
            <Form
              onSubmit={async (v) => {
                await decide.execute({ name: dialog.request.name, ...v });
                mutate();
                setDialog(undefined);
              }}
            >
              <Field label="Decision">
                <Select
                  name="decision"
                  defaultValue={canReview(dialog.request) ? "Approve" : "Cancel"}
                  onChange={(e) => setDialog({ ...dialog, decision: e.target.value })}
                >
                  {canReview(dialog.request) && (
                    <>
                      <option value="Approve">{t("Approve")}</option>
                      <option value="Reject">{t("Reject")}</option>
                    </>
                  )}
                  {canCancel(dialog.request) && <option value="Cancel">{t("Cancel request")}</option>}
                </Select>
              </Field>
              <Field label="Decision reason">
                <textarea
                  name="comment"
                  required={dialog.decision ? dialog.decision !== "Approve" : !canReview(dialog.request)}
                  maxLength={2000}
                />
              </Field>
              <p className="muted">
                {t(
                  "Rejection and cancellation require a reason. Final approval applies the change. Access does not change while a request is pending.",
                )}
              </p>
              <Button type="submit">{t("Submit decision")}</Button>
              <Button type="button" variant="secondary" onClick={() => setDialog(undefined)}>
                {t("Close")}
              </Button>
            </Form>
          )}
        </Modal>
      )}
      {dialog?.kind === "onboard" && (
        <Modal title="Request auditor onboarding" onClose={() => setDialog(undefined)}>
          <p className="muted">
            {t(
              "Approval creates a separate staff account and assigns it to the selected customer. The auditor can set a password using password recovery after approval.",
            )}
          </p>
          <Form
            onSubmit={async (v) => {
              await onboard.execute(v);
              mutate();
              setDialog(undefined);
            }}
          >
            <Field label="Organization">
              <Select name="entity">
                {data.customers.map((c: any) => (
                  <option key={c.name} value={c.name}>
                    {c.entity_name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Full name">
              <input name="full_name" required />
            </Field>
            <Field label="Email">
              <input name="email" type="email" required />
            </Field>
            <Field label="Role">
              <Select name="role">
                {["GRC Auditor", "GRC Consultant", "GRC Reviewer"].map((r) => (
                  <option key={r} value={r}>
                    {t(r)}
                  </option>
                ))}
              </Select>
            </Field>
            <Button type="submit">{t("Submit for approval")}</Button>
          </Form>
        </Modal>
      )}
      {dialog?.kind === "assign" && (
        <CustomerAssignment
          entity={dialog.entity}
          isAdmin={data.is_admin}
          onClose={() => setDialog(undefined)}
          onDone={() => {
            void mutate();
            setDialog(undefined);
          }}
        />
      )}
    </>
  );
}
function RequestSummary({ request: r }: { request: any }) {
  const { t } = useLanguage();
  const payload = r.payload.data || r.payload;
  return (
    <>
      <Status value={r.status} />
      <h3>{t(r.kind)}</h3>
      <dl className="oversight-profile">
        {Object.entries(payload)
          .filter(([k]) => !k.startsWith("_"))
          .map(([k, v]) => (
            <div key={k}>
              <dt>
                {t(
                  (
                    {
                      entity_name: "Organization name",
                      contact_email: "Contact email",
                      full_name: "Full name",
                      email: "Email",
                      membership_role: "Membership role",
                      role: "Role",
                      entity: "Organization",
                      auditor: "Auditor",
                      consultant: "Consultant",
                      reviewer: "Reviewer",
                      respondent: "Respondent",
                      due_date: "Due date",
                      review_due_date: "Review due date",
                      reason: "Reason",
                      active: "Active",
                      enabled: "Enabled",
                      sector: "Sector",
                      notes: "Notes",
                      listed_company: "Listed company",
                      parent_organization: "Parent organization",
                      regulators: "Regulators",
                      responsibility: "Responsibility",
                      name: "Assessment",
                    } as Record<string, string>
                  )[k] || k,
                )}
              </dt>
              <dd>{String(v ?? "—")}</dd>
            </div>
          ))}
      </dl>
      <h3>{t("Approval history")}</h3>
      <p>
        {t("Requested by")}: {r.requested_by}
      </p>
      <ol>
        {r.workflow.stages.map((s: string, i: number) => (
          <li key={i}>
            {t(s)} {r.status === "Pending" && i === r.step ? " ← " + t("Current stage") : ""}
          </li>
        ))}
      </ol>
      {r.decisions.map((d: any, i: number) => (
        <div className="notice" key={i}>
          <strong>{t(d.decision)}</strong> · {d.actor} · {d.time}
          <p>{d.comment}</p>
        </div>
      ))}
    </>
  );
}
function Detail({ kind, name, assignments }: { kind: string; name: string; assignments: any[] }) {
  const { t } = useLanguage(),
    { session } = useSession(),
    { data, error } = useData<any>("operations_detail", { kind, name });
  const [tab, setTab] = useState("profile"),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const profile =
    kind === "customer"
      ? Object.fromEntries(
          Object.entries(data.profile).filter(
            ([k]) =>
              !k.startsWith("can_") &&
              ![
                "units",
                "members",
                "auditors",
                "invitations",
                "read_only",
                "membership_role",
                "ownership_locked",
                "auditor_owner",
              ].includes(k),
          ),
        )
      : data.profile;
  const sections = ["profile", "assessments", "actions", "followups", "activity"];
  const labels: Record<string, string> = {
    profile: "Profile",
    assessments: "Assessments",
    actions: "Actions",
    followups: "Follow-ups",
    activity: "Activity",
  };
  const rows = (Array.isArray(data[tab]) ? data[tab] : []).filter((r: any) =>
    JSON.stringify(r).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="oversight-tabs">
        {sections.map((s) => (
          <Button
            key={s}
            variant={s === tab ? "primary" : "ghost"}
            onClick={() => {
              setTab(s);
              setPage(1);
              setSearch("");
            }}
          >
            {t(labels[s])}
            {Array.isArray(data[s]) ? " (" + data[s].length + ")" : ""}
          </Button>
        ))}
      </div>
      {tab === "profile" ? (
        <>
          <h2>{profile.entity_name || profile.full_name}</h2>
          <dl className="oversight-profile">
            {Object.entries(profile)
              .filter(([k]) => !["doctype", "owner", "modified_by", "idx", "docstatus"].includes(k))
              .map(([k, v]) => (
                <div key={k}>
                  <dt>
                    {t(
                      (
                        {
                          entity_name: "Organization name",
                          contact_email: "Contact email",
                          full_name: "Full name",
                          mobile_no: "Mobile number",
                          phone: "Phone",
                          language: "Language",
                          time_zone: "Time zone",
                          enabled: "Enabled",
                          last_login: "Last login",
                          creation: "Created",
                          email: "Email",
                          sector: "Sector",
                          notes: "Notes",
                          listed_company: "Listed company",
                          parent_organization: "Parent organization",
                          regulators: "Regulators",
                          grc_optional_reminders: "Optional reminders",
                          grc_optional_status_updates: "Optional status updates",
                          roles: "Roles",
                          name: "ID",
                          is_active: "Active",
                        } as Record<string, string>
                      )[k] || k,
                    )}
                  </dt>
                  <dd>
                    {Array.isArray(v)
                      ? v.map((r) => t(String(r))).join(", ")
                      : [
                            "enabled",
                            "listed_company",
                            "is_active",
                            "grc_optional_reminders",
                            "grc_optional_status_updates",
                          ].includes(k)
                        ? t(Number(v) ? "Yes" : "No")
                        : String(v ?? "—")}
                  </dd>
                </div>
              ))}
          </dl>
          {kind === "customer" && (
            <Link className="button secondary" to={session.home + "/customers/" + name}>
              {t("Open customer workspace")}
            </Link>
          )}
          {kind === "customer" && (
            <>
              <h3>{t("Members")}</h3>
              <Table headers={["Email", "Role", "Status"]}>
                {(data.profile.members || []).map((m: any) => (
                  <tr key={m.name}>
                    <td>{m.user}</td>
                    <td>{t(m.membership_role)}</td>
                    <td>
                      <Status value={m.active ? "Active" : "Inactive"} />
                    </td>
                  </tr>
                ))}
              </Table>
              <h3>{t("Organization units")}</h3>
              <Table headers={["Name", "Type", "Responsibilities"]}>
                {(data.profile.units || []).map((u: any) => (
                  <tr key={u.name}>
                    <td>{u.unit_name}</td>
                    <td>{t(u.unit_type)}</td>
                    <td>{u.responsibilities}</td>
                  </tr>
                ))}
              </Table>
            </>
          )}
          <h3>{t("Active assignments")}</h3>
          <Table headers={["Organization", "Auditor", "Responsibility"]}>
            {assignments
              .filter((a) => (kind === "customer" ? a.entity === name : a.auditor === name))
              .map((a) => (
                <tr key={a.name}>
                  <td>{a.entity}</td>
                  <td>{a.auditor}</td>
                  <td>{t(a.responsibility)}</td>
                </tr>
              ))}
          </Table>
        </>
      ) : (
        <>
          <div className="toolbar">
            <SearchInput
              value={search}
              onChange={(s) => {
                setSearch(s);
                setPage(1);
              }}
            />
            <Button variant="secondary" onClick={() => download(rows, kind + "-" + tab + ".csv")}>
              {t("Export CSV")}
            </Button>
          </div>
          {tab === "activity" && (
            <div className="oversight-summary">
              {Object.entries(data.activity_summary).map(([action, count]) => (
                <span key={action}>
                  {t(action)}: <strong>{String(count)}</strong>
                </span>
              ))}
            </div>
          )}
          <Table
            headers={
              tab === "activity"
                ? ["Activity", "Actor", "Organization", "Date", "Details"]
                : tab === "assessments"
                  ? [
                      "Assessment",
                      "Organization",
                      "Respondent",
                      "Consultant",
                      "Reviewer",
                      "Status",
                      "Due date",
                    ]
                  : ["Name", "Organization", "Status", "Assigned to", "Due date"]
            }
          >
            {rows.slice((page - 1) * 15, page * 15).map((r: any) => (
              <tr key={r.name}>
                {tab === "activity" ? (
                  <>
                    <td>{t(r.action)}</td>
                    <td>{r.actor}</td>
                    <td>{r.entity}</td>
                    <td>{r.creation?.slice(0, 16)}</td>
                    <td>
                      <details>
                        <summary>{t("View details")}</summary>
                        <pre className="oversight-event">
                          {typeof r.details === "string" ? r.details : JSON.stringify(r.details, null, 2)}
                        </pre>
                      </details>
                    </td>
                  </>
                ) : tab === "assessments" ? (
                  <>
                    <td>
                      <Link to={session.home + "/assessments/" + r.assessment}>{r.assessment}</Link>
                    </td>
                    <td>{r.entity}</td>
                    <td>{r.respondent}</td>
                    <td>{r.consultant || "—"}</td>
                    <td>{r.reviewer || "—"}</td>
                    <td>
                      <Status value={r.workflow_state} />
                    </td>
                    <td>{r.due_date}</td>
                  </>
                ) : (
                  <>
                    <td>{r.finding_title || r.note || r.name}</td>
                    <td>{r.entity}</td>
                    <td>
                      <Status value={r.status} />
                    </td>
                    <td>{r.assigned_to}</td>
                    <td>{r.due_date}</td>
                  </>
                )}
              </tr>
            ))}
          </Table>
          {!rows.length && (
            <Empty
              title={
                search
                  ? "No matching records"
                  : tab === "assessments"
                    ? "No assessments yet"
                    : tab === "actions"
                      ? "No improvement actions yet"
                      : tab === "followups"
                        ? "No customer follow-ups yet"
                        : "No activity yet"
              }
              text={
                search
                  ? "Clear the search or choose another section."
                  : tab === "assessments"
                    ? "Assessments appear after the customer starts the selected audit journey. Open the customer workspace to check permitted details and assignments."
                    : tab === "actions"
                      ? "Improvement actions appear when assessment findings create assigned work."
                      : tab === "followups"
                        ? "Authorized staff can record customer contact from Customer follow-ups."
                        : "Activity appears as customers and their assigned staff progress through the assessment."
              }
            />
          )}
          <Pagination page={page} total={rows.length} onPage={setPage} />
        </>
      )}
    </>
  );
}

function CustomerAssignment({
  entity,
  isAdmin,
  onClose,
  onDone,
}: {
  entity: string;
  isAdmin: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const { t } = useLanguage(),
    { data: staff, error } = useData<any[]>("staff", { entity }),
    assign = useMutation("assign_customer");
  const enabled = staff?.filter((row) => row.enabled) || [];
  return (
    <Modal title="Customer assignment" onClose={onClose}>
      <p>
        {t(
          "Assign customer access first. Then open the assessment and allocate the consultant and reviewer; assigning customer access alone does not allocate a review task.",
        )}
      </p>
      <p className="muted">
        {t("When assignment approval is enabled, access changes only after the final approval.")}
      </p>
      <ErrorNotice error={error} />
      {!staff && !error ? (
        <Loading />
      ) : !enabled.length ? (
        <Empty
          title="No eligible active staff"
          text="Ask an app administrator to configure active staff in the same department before assigning this customer."
        />
      ) : (
        <Form
          onSubmit={async (values) => {
            await assign.execute({ ...values, entity });
            onDone();
          }}
        >
          <Field label="Auditor">
            <Select name="auditor" required defaultValue={enabled[0].name}>
              {enabled.map((row) => (
                <option key={row.name} value={row.name}>
                  {row.full_name} · {row.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Responsibility">
            <Select name="responsibility" defaultValue="Consultant">
              {["Consultant", "Reviewer", ...(isAdmin ? ["Manager"] : [])].map((role) => (
                <option key={role} value={role}>
                  {t(role)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Status">
            <Select name="active" defaultValue="1">
              <option value="1">{t("Active")}</option>
              <option value="0">{t("Revoked")}</option>
            </Select>
          </Field>
          <Button type="submit">{t("Save changes")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </Form>
      )}
    </Modal>
  );
}
