import { useAssessmentTypes } from "../assessmentTypes";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useData, useMutation, rawPost } from "../api";
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
  SectorSelect,
  Status,
  Table,
} from "../components";
import Select from "../Select";
import "../audit-packages.css";

type Invitation = {
  name: string;
  email: string;
  invited_by: string;
  company?: string;
  assessment_type?: string;
  team_label?: string;
  minimum_sections?: string[];
  status: string;
  delivery_status: string;
  creation: string;
  last_sent_on?: string;
  expires_on?: string;
  last_activity_on?: string;
  started_on?: string;
  verified_on?: string;
  profile_submitted_on?: string;
  completed_on?: string;
  entity?: string;
  blocker: string;
  next_action: string;
  needs_attention: boolean;
  unread_owner_event?: number;
  permitted_actions?: string[];
  events?: { action: string; at: string; actor: string }[];
};
function stamp(value?: string) {
  return value ? new Date(value.replace(" ", "T")).toLocaleString() : "—";
}

export function OnboardingInvitations() {
  const { session } = useSession(),
    { t } = useLanguage();
  const [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [page, setPage] = useState(1),
    [creating, setCreating] = useState(false);
  const { data, error, mutate } = useData<Invitation[]>("onboarding_invitations", { search, status }, 30000);
  const create = useMutation("create_onboarding_invitation");
  const [invitationNotice, setInvitationNotice] = useState("");
  const assessmentTypes = useAssessmentTypes();
  const departments = session.is_admin
    ? assessmentTypes.names
    : [...new Set(session.department_memberships?.map((d) => d.department) || [])].filter((d) =>
        assessmentTypes.names.includes(d),
      );
  const [assessmentType, setAssessmentType] = useState(departments.length === 1 ? departments[0] : "");
  const [minimumSections, setMinimumSections] = useState<string[]>([]);
  function closeInvitationDraft() {
    setCreating(false);
    setAssessmentType(departments.length === 1 ? departments[0] : "");
    setMinimumSections([]);
  }
  if (!session.can_invite_customers) return <Navigate to={session.home} replace />;
  return (
    <>
      <PageTitle
        title="Customer onboarding"
        description="Follow each invitation from verification to an assigned customer."
      >
        <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
        <Button data-tour="invite-customer" onClick={() => setCreating(true)}>
          {t("Invite customer")}
        </Button>
      </PageTitle>
      <ErrorNotice error={error} />
      {invitationNotice && (
        <p className="notice" role="status">
          {t(invitationNotice)}
        </p>
      )}
      <section className="panel" data-tour="onboarding-tracker">
        <div className="toolbar">
          <SearchInput
            value={search}
            onChange={(s) => {
              setSearch(s);
              setPage(1);
            }}
          />
          <Select
            aria-label={t("Onboarding status")}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            {[
              "",
              "Active",
              "Awaiting customer",
              "Pending Invitation Approval",
              "Awaiting Approval",
              "Completed",
              "Expired",
              "Revoked",
              "Needs attention",
            ].map((s) => (
              <option key={s} value={s}>
                {t(s || "All statuses")}
              </option>
            ))}
          </Select>
        </div>
        {!data ? (
          <Loading />
        ) : !data.length ? (
          <Empty
            title={search || status ? "No matching invitations" : "No onboarding invitations"}
            text={
              search || status
                ? "No invitations match these filters. Clear the filters before creating another invitation."
                : "Invite a customer to begin tracking their onboarding."
            }
          >
            {search || status ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setSearch("");
                  setStatus("");
                  setPage(1);
                }}
              >
                {t("Clear filters")}
              </Button>
            ) : (
              <Button onClick={() => setCreating(true)}>{t("Create invitation")}</Button>
            )}
          </Empty>
        ) : (
          <>
            <Table
              headers={["Customer email", "Status", "Email delivery", "Last activity", "Next action", ""]}
            >
              {data.slice((page - 1) * 15, page * 15).map((r) => (
                <tr key={r.name}>
                  <td>
                    <Link to={session.home + "/onboarding/" + r.name}>{r.email}</Link>
                    <small>{r.name}</small>
                  </td>
                  <td>
                    <Status value={r.status} />
                    {r.needs_attention && <small className="warning-text">{t("Needs attention")}</small>}
                    {!!r.unread_owner_event && <small>{t("New update")}</small>}
                  </td>
                  <td>{t(r.delivery_status)}</td>
                  <td>{stamp(r.last_activity_on)}</td>
                  <td className="onboarding-note">
                    {t(r.next_action)}
                    {r.blocker && <small>{t(r.blocker)}</small>}
                  </td>
                  <td>
                    <Link className="button ghost" to={session.home + "/onboarding/" + r.name}>
                      {t("Open")}
                    </Link>
                  </td>
                </tr>
              ))}
            </Table>
            <Pagination page={page} total={data.length} onPage={setPage} />
          </>
        )}
      </section>
      {creating && (
        <Modal title="Invite customer" onClose={closeInvitationDraft}>
          <p>
            {t(
              "The invitation fixes the customer’s company and audit type. Included sections cannot be removed by the customer.",
            )}
          </p>
          <p className="muted">
            {t(
              "Sending invites the customer to verify their email and complete the assessment. You can cancel this draft without sending anything.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              const result = await create.execute({
                ...values,
                assessment_type: assessmentType,
                minimum_sections: assessmentType === "GRC" ? ["Awareness", ...minimumSections] : [],
              });
              setInvitationNotice(
                result.pending_approval
                  ? "Pending manager approval"
                  : "Invitation created. The customer must verify their email and continue their assessment. Open the invitation to track the next step.",
              );
              closeInvitationDraft();
              await mutate();
            }}
          >
            <Field label="Customer email">
              <input name="email" type="email" required />
            </Field>
            <Field label="Company">
              <input name="company" required maxLength={140} />
            </Field>
            <Field label="Assessment type">
              <Select
                value={assessmentType}
                onChange={(e) => {
                  setAssessmentType(e.target.value);
                  setMinimumSections([]);
                }}
                required
              >
                <option value="">{t("Choose an assessment type")}</option>
                {departments.map((d) => (
                  <option key={d} value={d}>
                    {assessmentTypes.label(d)}
                  </option>
                ))}
              </Select>
            </Field>
            {assessmentType === "GRC" && (
              <fieldset>
                <legend>{t("Included sections")}</legend>
                <p className="muted">
                  {t(
                    "Awareness is always included. Sections selected here cannot be removed by the customer. They can add more and must include at least one Risk, Compliance or Governance section.",
                  )}
                </p>
                <label className="checkbox">
                  <input type="checkbox" checked disabled />
                  {t("GRC General Maturity Awareness")}
                </label>
                {["Risk", "Compliance", "Governance"].map((section) => (
                  <label key={section} className="checkbox">
                    <input
                      type="checkbox"
                      checked={minimumSections.includes(section)}
                      onChange={(e) =>
                        setMinimumSections(
                          e.target.checked
                            ? [...minimumSections, section]
                            : minimumSections.filter((s) => s !== section),
                        )
                      }
                    />
                    {t(section)}
                  </label>
                ))}
              </fieldset>
            )}
            <Field label="Invitation language">
              <Select name="language" defaultValue="en">
                <option value="en">English</option>
                <option value="ar">العربية</option>
              </Select>
            </Field>
            <div className="row-actions">
              <Button type="submit" disabled={!assessmentType}>
                {t("Send invitation")}
              </Button>
              <Button type="button" variant="secondary" onClick={closeInvitationDraft}>
                {t("Cancel")}
              </Button>
            </div>
          </Form>
        </Modal>
      )}
    </>
  );
}

export function OnboardingDetail() {
  const { name } = useParams(),
    { session } = useSession(),
    { t } = useLanguage();
  const { data, error, mutate } = useData<Invitation>("onboarding_detail", { name }, 30000);
  const action = useMutation("onboarding_invitation_action");
  const [revoke, setRevoke] = useState(false),
    [failure, setFailure] = useState<unknown>();
  async function act(value: string, reason?: string) {
    setFailure(null);
    try {
      await action.execute({ name, action: value, reason });
      await mutate();
      setRevoke(false);
    } catch (e) {
      setFailure(e);
    }
  }
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const open = !!data.permitted_actions?.includes("revoke"),
    maySend = !!data.permitted_actions?.includes("resend");
  const steps: [string, string | undefined][] = [
    ["Invitation issued", data.last_sent_on],
    ["Customer started", data.started_on],
    ["Email verified", data.verified_on],
    ["Organization details submitted", data.profile_submitted_on],
    ["Onboarding completed", data.completed_on],
  ];
  return (
    <>
      <Link to={session.home + "/onboarding"}>{t("Customer onboarding")}</Link>
      <PageTitle title={data.email} description={data.name}>
        <Status value={data.status} />
        <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
      </PageTitle>
      <ErrorNotice error={failure} />
      <section className="panel padded" data-tour="onboarding-progress">
        <dl className="onboarding-meta">
          {[
            ["Original inviting auditor", data.invited_by],
            ["Company", data.company || "—"],
            ["Assessment type", t(data.assessment_type || "—")],
            ["Email delivery", t(data.delivery_status)],
            ["Created", stamp(data.creation)],
            ["Last sent", stamp(data.last_sent_on)],
            ["Invitation expires", stamp(data.expires_on)],
            ["Last activity", stamp(data.last_activity_on)],
          ].map(([k, v]) => (
            <div key={k}>
              <dt>{t(k)}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <div className="notice">
          <div>
            <strong>{t(data.next_action)}</strong>
            {data.blocker && <p>{t(data.blocker)}</p>}
          </div>
        </div>
        {["Pending Invitation Approval", "Awaiting Approval"].includes(data.status) && (
          <p>
            {t(
              "This request is waiting for an authorized manager. Do not send another invitation while approval is pending.",
            )}
          </p>
        )}
        {data.status === "Revoked" && (
          <p>
            {t(
              "This invitation is closed and cannot be resumed. Create a new invitation if the customer still needs access.",
            )}
          </p>
        )}
        {data.status === "Completed" && (
          <p>
            {t(
              "Onboarding is complete. Open the customer to check their assessment and team assignments. Review work starts after the customer submits.",
            )}
          </p>
        )}
        <ol className="onboarding-timeline">
          {steps.map(([label, date]) => (
            <li key={label} className={"onboarding-milestone" + (date ? " done" : "")}>
              <strong>{t(label)}</strong> <span>{stamp(date)}</span>
            </li>
          ))}
        </ol>
        <p className="muted">
          {t(
            "Email status reflects the mail system. It does not prove delivery or that the customer read the email.",
          )}
        </p>
        <div className="scope-actions" data-tour="onboarding-actions">
          {maySend && (
            <>
              <Button loading={action.loading} onClick={() => void act("remind")}>
                {t("Send reminder")}
              </Button>
              <Button variant="secondary" loading={action.loading} onClick={() => void act("resend")}>
                {t("Resend invitation")}
              </Button>
            </>
          )}
          {open && (
            <Button variant="ghost" onClick={() => setRevoke(true)}>
              {t("Revoke invitation")}
            </Button>
          )}
          {!!data.unread_owner_event && (
            <Button variant="ghost" onClick={() => void act("read")}>
              {t("Mark update read")}
            </Button>
          )}
          {data.entity && (
            <Link className="button" to={session.home + "/customers/" + encodeURIComponent(data.entity)}>
              {t("Open customer")}
            </Link>
          )}
        </div>
        {maySend && (
          <p>
            {t(
              "A reminder or resend replaces the previous link. Completed steps and the original auditor remain unchanged.",
            )}
          </p>
        )}
      </section>
      <section className="panel padded" data-tour="onboarding-history">
        <h2>{t("Onboarding timeline")}</h2>
        <ol className="onboarding-timeline">
          {data.events?.map((e, i) => (
            <li key={i}>
              <strong>{t(e.action)}</strong>
              <small>{stamp(e.at)}</small>
            </li>
          ))}
        </ol>
      </section>
      {revoke && (
        <Modal title="Revoke invitation" onClose={() => setRevoke(false)}>
          <Form
            onSubmit={async (v) => {
              await act("revoke", v.reason);
            }}
          >
            <Field label="Reason">
              <textarea name="reason" required maxLength={2000} />
            </Field>
            <Button type="submit">{t("Revoke invitation")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}

export function CustomerOnboarding() {
  const { session, refresh, withSessionMutation } = useSession(),
    { t } = useLanguage();
  const attempted = useRef(new Set<string>());
  const { data, error, mutate } = useData<Invitation[]>("customer_onboarding", undefined, 30000);
  const resume = useMutation("resume_onboarding"),
    complete = useMutation("complete_onboarding");
  const [selected, setSelected] = useState(""),
    [verification, setVerification] = useState(""),
    [sent, setSent] = useState(false),
    [failure, setFailure] = useState<unknown>();
  useEffect(() => {
    const row = data?.find((r) => r.company && r.status === "Email Verified");
    if (!row || attempted.current.has(row.name)) return;
    attempted.current.add(row.name);
    void complete
      .execute({ name: row.name })
      .then(async (result) => {
        if (result.validation_error) throw new Error(result.validation_error);
        if (result.assessment) {
          window.location.assign(session.home + "/assessments/" + encodeURIComponent(result.assessment));
          return;
        }
        await refresh();
        await mutate();
      })
      .catch(setFailure);
  }, [data, complete, refresh, mutate, session.home]);
  if (session.kind !== "Customer") return <Navigate to={session.home} replace />;
  async function open(row: Invitation) {
    setFailure(null);
    try {
      const r = await resume.execute({ name: row.name });
      if (r.verification_required) {
        setVerification(row.name);
        setSent(false);
      } else if (row.company) {
        const result = await complete.execute({ name: row.name });
        if (result.validation_error) throw new Error(result.validation_error);
        if (result.assessment) {
          window.location.assign(session.home + "/assessments/" + encodeURIComponent(result.assessment));
          return;
        }
        await refresh();
        await mutate();
      } else {
        setSelected(row.name);
        await mutate();
      }
    } catch (e) {
      setFailure(e);
    }
  }
  return (
    <>
      <PageTitle
        title="Complete your onboarding"
        description="Resume your invitation and follow the next step."
      >
        <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
      </PageTitle>
      <ErrorNotice error={error || failure} />
      {!data ? (
        <Loading />
      ) : !data.length ? (
        <Empty
          title="No onboarding invitations"
          text="There is no invitation to resume. Open your workspace to start an available assessment, or ask your department team for an invitation."
        >
          <Link className="button secondary" to={session.home}>
            {t("Open your workspace")}
          </Link>
        </Empty>
      ) : (
        <div className="onboarding-list">
          {data.map((row) => (
            <section key={row.name} className="panel padded" data-tour="customer-onboarding">
              <h2>{row.email}</h2>
              <Status value={row.status} />
              <p>{t(row.next_action)}</p>
              {row.blocker && <p className="notice">{t(row.blocker)}</p>}
              {row.status === "Completed" ? (
                <Link to={session.home} className="button">
                  {t("Open your workspace")}
                </Link>
              ) : ["Awaiting Approval", "Pending Invitation Approval"].includes(row.status) ? (
                <p>{t("Your details have been submitted. An administrator will review the request.")}</p>
              ) : row.status === "Revoked" ? (
                <p>{t("This invitation is closed. Ask the inviting team for a new invitation.")}</p>
              ) : row.status === "Expired" ? (
                <p>{t("Ask your inviting auditor to resend the invitation.")}</p>
              ) : selected === row.name ? (
                <Form
                  onSubmit={async (v) => {
                    const result = await complete.execute({
                      name: row.name,
                      organization_name: v.organization_name,
                      sector: v.sector,
                    });
                    if (result.validation_error) throw new Error(result.validation_error);
                    await mutate();
                    await refresh();
                    setSelected("");
                  }}
                  noValidate
                >
                  <Field label={row.company ? "Company" : "Organization name"}>
                    <input
                      name="organization_name"
                      maxLength={140}
                      defaultValue={row.company}
                      readOnly={!!row.company}
                    />
                  </Field>
                  {!row.company && (
                    <Field label="Sector">
                      <SectorSelect />
                    </Field>
                  )}
                  <Button type="submit">{t("Complete onboarding")}</Button>
                </Form>
              ) : (
                <Button onClick={() => void open(row)}>{t("Resume onboarding")}</Button>
              )}
            </section>
          ))}
        </div>
      )}
      {verification && (
        <Modal title="Verify your email" onClose={() => setVerification("")}>
          <Form
            onSubmit={async (v) => {
              if (!sent) {
                await rawPost("ia_maturity.grc.auth.request_code", {
                  email: session.user,
                  purpose: "Resume",
                  onboarding_invitation: verification,
                });
                setSent(true);
              } else {
                await withSessionMutation(async () => {
                  const r = await rawPost("ia_maturity.grc.auth.verify_code", {
                    email: session.user,
                    code: v.code,
                  });
                  window.location.assign(r.message.redirect);
                });
              }
            }}
          >
            {sent ? (
              <Field label="Verification code">
                <input name="code" inputMode="numeric" pattern="[0-9]{6}" required />
              </Field>
            ) : (
              <p>{t("A verification code will be sent to your account email.")}</p>
            )}
            <Button type="submit">{t(sent ? "Verify and continue" : "Send verification code")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}

export function OnboardingLink() {
  const { withSessionMutation } = useSession();
  const { t, lang, setLang } = useLanguage();
  const [token] = useState(() => new URLSearchParams(window.location.search).get("token") || "");
  const { data, error } = useData<{
    email: string;
    auditor: string;
    expires_on: string;
    language: "en" | "ar";
    company?: string;
    assessment_type?: string;
    team_label?: string;
    minimum_sections?: string[];
  }>("onboarding_link", { token });
  const [sent, setSent] = useState(false),
    [failure, setFailure] = useState<unknown>(),
    [busy, setBusy] = useState(false),
    [name, setName] = useState("");
  const [resendAt, setResendAt] = useState(0),
    [expiresAt, setExpiresAt] = useState(0),
    [clock, setClock] = useState(0);
  const waitSeconds = Math.max(0, Math.ceil((resendAt - clock) / 1000));
  useEffect(() => {
    if (!resendAt) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [resendAt]);
  async function sendCode(fullName: string, consent: number) {
    if (!data) return;
    try {
      const result = await rawPost("ia_maturity.grc.auth.request_code", {
        email: data.email,
        full_name: fullName,
        consent,
        purpose: "Start",
        language: lang,
        onboarding_token: token,
      });
      const now = Date.now();
      setClock(now);
      setResendAt(now + (result.message.resend_after_seconds || 60) * 1000);
      setExpiresAt(now + (result.message.expires_in_seconds || 900) * 1000);
      setName(fullName);
      setSent(true);
    } catch (error) {
      const seconds = Number((error as { retry_after_seconds?: number })?.retry_after_seconds);
      if (seconds > 0) {
        const now = Date.now();
        setClock(now);
        setResendAt(now + seconds * 1000);
      }
      throw error;
    }
  }
  useEffect(() => {
    window.history.replaceState({}, "", "/onboarding");
  }, []);
  useEffect(() => {
    if (data?.language) setLang(data.language);
  }, [data?.language, setLang]);
  useEffect(() => {
    document.title = data?.assessment_type ? "AlphaX " + data.assessment_type : "AlphaX";
  }, [data?.assessment_type]);
  return (
    <main className="onboarding-public">
      <div className="scope-actions">
        <a href="/">AlphaX {data?.assessment_type ? t(data.assessment_type) : ""}</a>
        <Button variant="ghost" onClick={() => setLang(lang === "en" ? "ar" : "en")}>
          {lang === "en" ? "العربية" : "English"}
        </Button>
      </div>
      <h1>{t("Your customer onboarding invitation")}</h1>
      <ErrorNotice error={error || failure} />
      {error && (
        <section className="panel padded">
          <p>
            {t(
              "This invitation could not be opened. Use the latest invitation email, or ask the inviting team to resend it. You can still sign in to an existing account.",
            )}
          </p>
          <a className="button secondary" href="/login">
            {t("Customer sign in")}
          </a>
        </section>
      )}
      {!error && !data && <Loading />}
      {data && (
        <section className="panel padded">
          <p>
            <strong>
              {/* The server phrases the team for every type, including admin-defined ones. */}
              {data.team_label && data.assessment_type
                ? data.team_label
                : t(
                    data.assessment_type === "Internal Audit"
                      ? "Invited by the Internal Audit team"
                      : data.assessment_type === "GRC"
                        ? "Invited by the GRC team"
                        : "Invited by",
                  )}
              {!data.assessment_type && ": " + data.auditor}
            </strong>
          </p>
          <Field label="Email">
            <input type="email" value={data.email} readOnly />
          </Field>
          {data.company && (
            <Field label="Company">
              <input value={data.company} readOnly />
            </Field>
          )}
          {data.assessment_type && (
            <p>
              {t("Assessment type")}: {t(data.assessment_type)}
            </p>
          )}
          {data.minimum_sections?.length && data.assessment_type === "GRC" ? (
            <p>
              {t("Included sections")}: {data.minimum_sections.map((s) => t(s)).join(" · ")}
            </p>
          ) : null}
          <p>
            {t(
              "Verify your email to start your assessment. Your company and audit type are fixed by the invitation.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              setBusy(true);
              try {
                if (!sent) {
                  await sendCode(values.full_name, values.consent ? 1 : 0);
                } else {
                  await withSessionMutation(async () => {
                    const r = await rawPost("ia_maturity.grc.auth.verify_code", {
                      email: data.email,
                      code: values.code,
                    });
                    window.location.assign(r.message.redirect);
                  });
                }
              } finally {
                setBusy(false);
              }
            }}
          >
            {!sent ? (
              <>
                <Field label="Full name">
                  <input name="full_name" required maxLength={140} />
                </Field>
                <label className="check-label">
                  <input name="consent" type="checkbox" required />{" "}
                  {t("I accept the privacy notice and terms.")}
                </label>
                <a href="/grc-site/privacy" target="_blank" rel="noreferrer">
                  {t("Privacy")}
                </a>
                <a href="/grc-site/terms" target="_blank" rel="noreferrer">
                  {t("Terms")}
                </a>
              </>
            ) : (
              <>
                <p>
                  {t("Check your email for the verification code or verification link.")}{" "}
                  {t(
                    "Check your spam folder if it has not arrived. Use Resend code when the countdown ends.",
                  )}
                </p>
                <Field label="Verification code">
                  <input
                    name="code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    required
                  />
                </Field>
              </>
            )}
            <Button
              type="submit"
              loading={busy}
              disabled={(!sent && waitSeconds > 0) || (sent && expiresAt > 0 && clock >= expiresAt)}
            >
              {t(sent ? "Verify and continue" : "Send verification code")}
            </Button>
            {!sent && waitSeconds > 0 && (
              <p role="status">
                {t("You can request another verification email in")} <span dir="ltr">{waitSeconds}s</span>
              </p>
            )}
          </Form>
          {sent && (
            <div aria-live="polite">
              <p>
                {t("Code expires in")} {Math.max(0, Math.ceil((expiresAt - clock) / 60000))} {t("minutes")}
              </p>
              {expiresAt > 0 && clock >= expiresAt && (
                <p>{t("This code has expired. Request a new code to continue.")}</p>
              )}
              <Button
                variant="ghost"
                loading={busy}
                disabled={waitSeconds > 0}
                onClick={async () => {
                  setFailure(null);
                  setBusy(true);
                  try {
                    await sendCode(name, 1);
                  } catch (e) {
                    setFailure(e);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {t("Resend verification code")}
                {waitSeconds > 0 ? " (" + waitSeconds + "s)" : ""}
              </Button>
            </div>
          )}
          <p>
            <a href="/login?next=/grc/customer/onboarding">
              {t("Already have an account? Sign in and resume your invitation.")}
            </a>
          </p>
        </section>
      )}
    </main>
  );
}
