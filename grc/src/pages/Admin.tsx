import Select from "../Select";
import EmailDelivery from "./EmailDelivery";
import VerificationLimits from "./VerificationLimits";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
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

export function AssignmentsPage() {
  const { session } = useSession(),
    { t } = useLanguage(),
    [entity, setEntity] = useState(""),
    [dialog, setDialog] = useState<any>(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const org = entity || session.organizations?.[0]?.name || "";
  const { data, error, mutate } = useData<any>("organization_detail", { name: org }),
    { data: staff } = useData<any[]>("staff"),
    save = useMutation("assign_customer");
  const { data: queue } = useData<any>("dashboard", { entity: org || undefined });
  const rows =
    data?.auditors?.filter((a: any) => a.auditor.toLowerCase().includes(search.toLowerCase())) || [];
  return (
    <>
      <PageTitle
        eyebrow="Administration"
        title="Customer assignments"
        description="Customer visibility requires an active assignment. Assessment allocation further controls review actions."
      >
        <Button disabled={!org} onClick={() => setDialog({})}>
          <Plus size={16} />
          {t("Assign customer")}
        </Button>
      </PageTitle>
      <section className="panel">
        <div className="toolbar">
          <Select
            aria-label={t("Organization")}
            value={org}
            onChange={(e) => {
              setEntity(e.target.value);
              setPage(1);
            }}
          >
            {session.organizations?.map((o) => (
              <option key={o.name} value={o.name}>
                {o.entity_name}
              </option>
            ))}
          </Select>
          <SearchInput
            value={search}
            onChange={(s) => {
              setSearch(s);
              setPage(1);
            }}
          />
        </div>
        {org && <ErrorNotice error={error} />}
        <Table headers={["Auditor", "Responsibility", "Status", ""]}>
          {rows.slice((page - 1) * 15, page * 15).map((a: any) => (
            <tr key={a.name}>
              <td>{a.auditor}</td>
              <td>{t(a.responsibility)}</td>
              <td>
                <Status value={a.active ? "Active" : "Revoked"} />
              </td>
              <td>
                <Button variant="ghost" onClick={() => setDialog(a)}>
                  {t("Edit")}
                </Button>
              </td>
            </tr>
          ))}
        </Table>
        {!rows.length && <Empty />}
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>{t("Reassignment queue")}</h2>
        </div>
        {queue?.assessments
          ?.filter((a: any) => a.needs_reassignment)
          .map((a: any) => (
            <div className="queue-item" key={a.name}>
              <div>
                <strong>{a.entity}</strong>
                <small>
                  {a.name} · {t(a.state)}
                </small>
              </div>
              <Link className="button secondary" to={session.home + "/assessments/" + a.name}>
                {t("Assign team")}
              </Link>
            </div>
          ))}
        {!queue?.assessments?.some((a: any) => a.needs_reassignment) && (
          <Empty title="No work awaiting reassignment" />
        )}
      </section>
      {dialog && (
        <Modal title="Customer assignment" onClose={() => setDialog(undefined)}>
          <p className="muted">
            {t(
              "Revoking an assignment removes access on the next request and returns outstanding work for reassignment.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, entity: org });
              mutate();
              setDialog(undefined);
            }}
          >
            <Field label="Auditor">
              <Select name="auditor" defaultValue={dialog.auditor} required>
                {staff
                  ?.filter((s) => s.enabled)
                  .map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.full_name} · {s.name}
                    </option>
                  ))}
              </Select>
            </Field>
            <Field label="Responsibility">
              <Select name="responsibility" defaultValue={dialog.responsibility || "Consultant"}>
                <option value="Consultant">{t("Consultant")}</option>
                <option value="Reviewer">{t("Reviewer")}</option>
                <option value="Manager">{t("Manager")}</option>
              </Select>
            </Field>
            <Field label="Status">
              <Select name="active" defaultValue={dialog.active ?? 1}>
                <option value="1">{t("Active")}</option>
                <option value="0">{t("Revoked")}</option>
              </Select>
            </Field>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}
export function StaffPage() {
  const { t } = useLanguage(),
    { data, error, mutate } = useData<any[]>("staff"),
    save = useMutation("save_staff"),
    [selected, setSelected] = useState<any>(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const rows =
    data?.filter((a) => (a.full_name + " " + a.name).toLowerCase().includes(search.toLowerCase())) || [];
  return (
    <>
      <PageTitle
        eyebrow="Administration"
        title="Staff"
        description="GRC staff use separate portal accounts. MFA depends on the configured security policy."
      >
        <Button onClick={() => setSelected({})}>
          <Plus size={16} />
          {t("Add staff")}
        </Button>
      </PageTitle>
      <section className="panel">
        <div className="toolbar">
          <SearchInput
            value={search}
            onChange={(s) => {
              setSearch(s);
              setPage(1);
            }}
          />
        </div>
        <ErrorNotice error={error} />
        <Table headers={["Name", "Email", "Role", "Status", ""]}>
          {rows.slice((page - 1) * 15, page * 15).map((s) => (
            <tr key={s.name}>
              <td>{s.full_name}</td>
              <td>{s.name}</td>
              <td>{s.grc_roles.join(", ")}</td>
              <td>
                <Status value={s.enabled ? "Active" : "Inactive"} />
              </td>
              <td>
                <Button variant="ghost" onClick={() => setSelected(s)}>
                  {t("Edit")}
                </Button>
              </td>
            </tr>
          ))}
        </Table>
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
      {selected && (
        <Modal title="GRC staff account" onClose={() => setSelected(undefined)}>
          <Form
            onSubmit={async (values) => {
              await save.execute(values);
              mutate();
              setSelected(undefined);
            }}
          >
            <Field label="Full name">
              <input name="full_name" defaultValue={selected.full_name} required />
            </Field>
            <Field label="Email">
              <input
                name="email"
                type="email"
                defaultValue={selected.name}
                readOnly={!!selected.name}
                required
              />
            </Field>
            <Field label="Role">
              <Select name="role" defaultValue={selected.grc_roles?.[0] || "GRC Auditor"}>
                {["GRC Consultant", "GRC Reviewer", "GRC Manager", "GRC Auditor", "GRC App Admin"].map(
                  (r) => (
                    <option key={r}>{r}</option>
                  ),
                )}
              </Select>
            </Field>
            <Field label="Status">
              <Select name="enabled" defaultValue={selected.enabled ?? 1}>
                <option value="1">{t("Active")}</option>
                <option value="0">{t("Inactive")}</option>
              </Select>
            </Field>
            <p className="muted">
              {t(
                "Staff can set their password through the password recovery screen. MFA applies when required by policy.",
              )}
            </p>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}
const scoringLabels: Record<string, string> = {
  points_a: "Answer A points",
  points_b: "Answer B points",
  points_c: "Answer C points",
  points_d: "Answer D points",
  create_actions_for: "Create actions for answers",
  evidence_required_from: "Require evidence from level",
  issue_lookback_months: "Issue lookback (months)",
  issue_min_sample: "Minimum issue sample",
  closure_a_above: "A threshold (months)",
  closure_b_above: "B threshold (months)",
  closure_c_above: "C threshold (months)",
  lock_auto_answers: "Lock calculated answers",
};
export function SettingsPage() {
  const { t } = useLanguage(),
    { data, error, mutate } = useData<any>("settings"),
    save = useMutation("save_settings");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        eyebrow="Administration"
        title="Settings"
        description="Changes are audited. Results visibility applies immediately to unreleased assessments."
      />
      <section className="panel padded">
        <Form
          onSubmit={async (values) => {
            const scoring = Object.fromEntries(
              Object.keys(data.scoring)
                .filter((k) => values["score_" + k] !== undefined)
                .map((k) => [k, values["score_" + k]]),
            );
            const profile_editable_fields = data.profile_fields
              .filter((f: any) => values["profile_" + f.fieldname] === "on")
              .map((f: any) => f.fieldname);
            await save.execute({ data: { ...values, scoring, profile_editable_fields } });
            mutate();
          }}
        >
          <h2>{t("Assessment presentation")}</h2>
          <Field label="Overall Maturity panel">
            <Select
              name="overall_maturity_visibility"
              defaultValue={data.overall_maturity_visibility || "Hidden"}
            >
              {["Hidden", "After assessment completion", "Completed sections only"].map((v) => (
                <option key={v} value={v}>
                  {t(v === "Hidden" ? "Don't show at all" : v)}
                </option>
              ))}
            </Select>
          </Field>
          <div className="form-grid">
            <Field label="Customer scoring visibility">
              <Select
                name="customer_score_timing"
                defaultValue={data.customer_score_timing || "After all answers"}
              >
                {["After all answers", "During assessment", "After submission"].map((v) => (
                  <option key={v} value={v}>
                    {t(v)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Customer section overview">
              <Select
                name="customer_sections_visibility"
                defaultValue={data.customer_sections_visibility || "Always expanded"}
              >
                {["Collapsed until complete", "Always collapsed", "Always expanded", "Hidden"].map((v) => (
                  <option key={v} value={v}>
                    {t(v)}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="form-grid">
            {[
              ["question_extras_enabled", "Enable question comments and evidence"],
              ["expand_report", "Expand report by default"],
            ].map(([key, label]) => (
              <Field key={key} label={label}>
                <Select name={key} defaultValue={data[key] ?? 0}>
                  <option value="0">{t("Disabled")}</option>
                  <option value="1">{t("Enabled")}</option>
                </Select>
              </Field>
            ))}
          </div>
          <h2>{t("Customer results before report release")}</h2>
          <div className="setting-options">
            {[
              [
                "Preliminary scorecard",
                "Show clearly labeled self-assessment scores after submission. The final PDF remains unavailable until release.",
              ],
              [
                "Status only",
                "Show progress, status, and required actions. Withhold scores and reports until release.",
              ],
            ].map(([value, description]) => (
              <label className="setting-option" key={value}>
                <input
                  type="radio"
                  name="results_visibility"
                  value={value}
                  defaultChecked={data.results_visibility === value}
                />
                <div>
                  <strong>{t(value)}</strong>
                  <p>{t(description)}</p>
                </div>
              </label>
            ))}
          </div>
          <p className="muted">{t("Released reports retain their authorized availability.")}</p>
          <hr />
          <h2>{t("Report download and email")}</h2>
          <p className="muted">
            {t(
              "Controls customer PDF download and report email. Enforced in the API as well as the portal UI.",
            )}
          </p>
          <div className="form-grid">
            <Field label="Allow report PDF download">
              <Select name="allow_report_download" defaultValue={data.allow_report_download ?? 1}>
                <option value="1">{t("Enabled")}</option>
                <option value="0">{t("Disabled")}</option>
              </Select>
            </Field>
            <Field label="Allow report email">
              <Select name="allow_report_email" defaultValue={data.allow_report_email ?? 1}>
                <option value="1">{t("Enabled")}</option>
                <option value="0">{t("Disabled")}</option>
              </Select>
            </Field>
          </div>
          <div className="setting-options">
            {[
              ["After Audit", "Only after an authorized reviewer releases the report (Report Released)."],
              [
                "Before Audit",
                "From customer submission onward. Download serves a preliminary PDF until release.",
              ],
            ].map(([value, description]) => (
              <label className="setting-option" key={value}>
                <input
                  type="radio"
                  name="report_access_timing"
                  value={value}
                  defaultChecked={(data.report_access_timing || "After Audit") === value}
                />
                <div>
                  <strong>{t(value)}</strong>
                  <p>{t(description)}</p>
                </div>
              </label>
            ))}
          </div>
          <hr />
          <h2>{t("Organization profile and new user defaults")}</h2>
          <div className="form-grid">
            <Field label="Organization yes/no answers">
              <Select
                name="organization_yes_no_display"
                defaultValue={data.organization_yes_no_display || "Dropdown"}
              >
                <option value="Dropdown">{t("Dropdown")}</option>
                <option value="Buttons">{t("Buttons")}</option>
              </Select>
            </Field>
            <Field label="Page tours for new users">
              <Select
                name="new_user_page_tour_default"
                defaultValue={data.new_user_page_tour_default || "Enabled"}
              >
                <option value="Enabled">{t("Enabled")}</option>
                <option value="Disabled">{t("Disabled")}</option>
              </Select>
            </Field>
            <Field label="Help and guides for new users">
              <Select name="new_user_help_default" defaultValue={data.new_user_help_default || "Enabled"}>
                <option value="Enabled">{t("Enabled")}</option>
                <option value="Disabled">{t("Disabled")}</option>
              </Select>
            </Field>
          </div>
          <p className="muted">
            {t(
              "Defaults apply only to new GRC users. Each user can change their own preferences in their profile.",
            )}
          </p>
          <hr />
          <h2>{t("Signup email policy")}</h2>
          <p className="muted">
            {t(
              "Allow all valid personal and organizational emails by default. Domain restrictions apply only to new accounts; existing customers can still sign in.",
            )}
          </p>
          <Field label="Signup email policy">
            <Select name="signup_email_policy" defaultValue={data.signup_email_policy || "All valid emails"}>
              <option value="All valid emails">{t("All valid emails")}</option>
              <option value="Allowed domains only">{t("Allowed domains only")}</option>
            </Select>
          </Field>
          <Field label="Allowed signup email domains">
            <textarea
              name="signup_allowed_domains"
              defaultValue={data.signup_allowed_domains || ""}
              rows={3}
              placeholder="example.com"
            />
            <small>
              {t(
                "One exact domain per line. Subdomains must be listed separately. Required only when domain restrictions are enabled.",
              )}
            </small>
          </Field>
          <hr />
          <h2>{t("Reminders")}</h2>
          <div className="form-grid">
            {[
              ["reminders_enabled", "Reminders enabled"],
              ["scoring_owner_approved", "Scoring owner approved"],
              ["content_approved", "Bilingual content approved"],
            ].map(([key, label]) => (
              <Field key={key} label={label}>
                <Select name={key} defaultValue={data[key] || 0}>
                  <option value="0">{t("No")}</option>
                  <option value="1">{t("Yes")}</option>
                </Select>
              </Field>
            ))}
            {[
              ["reminder_days", "Reminder interval (days)"],
              ["default_due_days", "Default assessment deadline (days)"],
            ].map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  name={key}
                  type="number"
                  min={1}
                  max={key === "reminder_days" ? 90 : 365}
                  defaultValue={data[key]}
                  required
                />
              </Field>
            ))}
          </div>
          <hr />
          <h2>{t("Scoring policy")}</h2>
          <p className="muted">
            {t(
              "Scoring changes affect newly published versions only. Existing assessments retain their pinned policy.",
            )}
          </p>
          <div className="form-grid">
            {Object.entries(data.scoring).map(([key, value]) => (
              <Field key={key} label={scoringLabels[key] || key}>
                {key === "lock_auto_answers" ? (
                  <Select name={"score_" + key} defaultValue={Number(value) || 0}>
                    <option value="0">{t("No")}</option>
                    <option value="1">{t("Yes")}</option>
                  </Select>
                ) : (
                  <input name={"score_" + key} defaultValue={String(value ?? "")} />
                )}
              </Field>
            ))}
          </div>
          <hr />
          <h2>{t("Profile editing permissions")}</h2>
          <p className="muted">
            {t(
              "Choose which personal fields customers and staff may edit. Changes apply immediately to profile saves.",
            )}
          </p>
          <div className="profile-permissions">
            {data.profile_fields.map((field: any) => (
              <label className="setting-option" key={field.fieldname}>
                <input
                  type="checkbox"
                  name={"profile_" + field.fieldname}
                  defaultChecked={data.profile_editable_fields.includes(field.fieldname)}
                />
                <span>{t(field.label)}</span>
              </label>
            ))}
          </div>
          <p className="muted">
            {t(
              "Email, access roles, account type, and organization assignments always remain administrator-managed. Password changes remain available to the account owner.",
            )}
          </p>
          <hr />
          <h2>{t("Publication settings")}</h2>
          <div className="form-grid">
            <Field label="Production hostname">
              <input name="production_hostname" defaultValue={data.production_hostname} />
            </Field>
            <Field label="Framework version">
              <input name="framework_version" defaultValue={data.framework_version} />
            </Field>
          </div>
          <p className="muted">
            {t("Privacy and terms are managed through the site content approval workflow.")}
          </p>
          <Button type="submit">{t("Save changes")}</Button>
        </Form>
      </section>
      <EmailDelivery />
      <VerificationLimits />
      <section className="panel">
        <div className="panel-heading">
          <h2>{t("Reminder delivery history")}</h2>
        </div>
        <Table headers={["Recipient", "Subject", "Status", "Date"]}>
          {data.delivery.map((d: any) => (
            <tr key={d.name}>
              <td>{d.recipient}</td>
              <td>
                {d.subject}
                {d.error && <small className="warning-text">{d.error}</small>}
              </td>
              <td>
                <Status value={d.status} />
              </td>
              <td>{d.creation?.slice(0, 16)}</td>
            </tr>
          ))}
        </Table>
      </section>
    </>
  );
}
