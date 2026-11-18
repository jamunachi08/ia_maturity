import { useAssessmentTypes } from "../assessmentTypes";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { useData, useMutation } from "../api";
import {
  Button,
  Empty,
  ErrorNotice,
  Field,
  Form,
  Loading,
  Modal,
  PageTitle,
  Status,
  Table,
} from "../components";
import Select from "../Select";

type AccessRequest = {
  name: string;
  entity: string;
  assessment_type: string;
  source_department?: string;
  department?: string;
  requested_by?: string;
  status: string;
  reason?: string;
  creation?: string;
  can_decide?: boolean;
};
type DepartmentMember = { name: string; user: string; department: string; role: string; active: number };

export default function DepartmentAccess() {
  const { session, activeOrganization, refresh } = useSession(),
    { t } = useLanguage();
  const customer = session.kind === "Customer";
  const entity = activeOrganization || session.organizations?.[0]?.name || "";
  const { data, error, mutate } = useData<AccessRequest[]>(
    "audit_type_requests",
    customer ? { entity } : undefined,
    30000,
  );
  const request = useMutation("request_audit_type"),
    decide = useMutation("decide_audit_type_request");
  const [current, setCurrent] = useState<AccessRequest | null>(null),
    [approval, setApproval] = useState(true),
    [requestOpen, setRequestOpen] = useState(false),
    [requested, setRequested] = useState(false);
  const granted = session.audit_type_access?.[entity] || session.allowed_assessment_types || [];
  const assessmentTypes = useAssessmentTypes();
  // Any active type the organization does not have yet can be requested.
  const requestable = granted.length ? assessmentTypes.names.filter((name) => !granted.includes(name)) : [];
  const [requestType, setRequestType] = useState("");
  const otherType =
    requestable.length === 1 ? requestable[0] : requestable.includes(requestType) ? requestType : "";
  const pending = data?.some((r) => r.entity === entity && r.status.startsWith("Pending"));
  const latest = customer ? data?.find((row) => row.entity === entity) : undefined;
  const canRequest =
    !!entity &&
    session.memberships?.some((m) => m.entity === entity && m.membership_role === "Organization Admin");
  const stageText = (status: string) =>
    status === "Pending Source Approval"
      ? "Waiting for the current department manager. Receiving department approval is still required."
      : status === "Pending Target Approval"
        ? "Current department approved. Waiting for the receiving department manager; access is not active yet."
        : status === "Approved"
          ? "Both departments approved. The customer can refresh the workspace to use the additional audit type."
          : status === "Rejected"
            ? "The request was rejected. Review the reason before submitting a new request."
            : "";
  return (
    <>
      <PageTitle
        title="Audit access"
        description={
          customer
            ? "Your selected audit type is available in your workspace. Another audit type requires department manager approval."
            : "Review audit access requests for your department."
        }
      />
      <ErrorNotice error={error || request.error || decide.error} />
      <p className="notice">
        {t(
          "Additional audit access needs two decisions: the current department manager approves first, then the receiving department manager accepts. Access stays unchanged until both approve.",
        )}
      </p>
      {customer && (
        <section className="panel padded">
          <h2>{t("Available audit types")}</h2>
          <p>
            {granted.map((kind) => assessmentTypes.label(kind)).join(" · ") ||
              t("Choose your first audit type when starting an assessment.")}
          </p>
          {requestable.length > 0 && canRequest && (
            <Button disabled={!!pending || requested} onClick={() => setRequestOpen(true)}>
              {t(pending || requested ? "Request pending" : "Request another audit type")}
            </Button>
          )}
          {!canRequest && (
            <p className="muted">
              {t(
                entity
                  ? "Only an organization administrator can request another audit type. Ask your organization administrator to send the request."
                  : "Create or join your organization before requesting another audit type.",
              )}
            </p>
          )}
          {latest && stageText(latest.status) && (
            <p className="notice" role="status">
              {t(stageText(latest.status))}
            </p>
          )}
          {requested && (
            <p className="notice" role="status">
              {t("Your request was sent. Both department approvals are required before access changes.")}
            </p>
          )}
        </section>
      )}
      {!data ? (
        <Loading />
      ) : !data.length ? (
        <Empty
          title="No audit access requests"
          text={
            customer
              ? "No request is required to continue your current assessment. Return to Overview to resume your work."
              : "Requests appear here when a customer asks for additional audit access. Only the manager responsible for the current stage can decide."
          }
        >
          <Link className="button secondary" to={session.home}>
            {t("Overview")}
          </Link>
        </Empty>
      ) : (
        <section className="panel">
          <Table
            headers={
              customer
                ? ["Organization", "Status", "Reason"]
                : ["Organization", "Assessment type", "Requested by", "Status", ""]
            }
          >
            {data.map((row) => (
              <tr key={row.name}>
                <td>{row.entity}</td>
                {!customer && (
                  <>
                    <td>{t(row.assessment_type)}</td>
                    <td>{row.requested_by || "—"}</td>
                  </>
                )}
                <td>
                  <Status value={row.status} />
                  {!customer && stageText(row.status) && <p className="muted">{t(stageText(row.status))}</p>}
                </td>
                <td>
                  {customer ? (
                    row.reason || "—"
                  ) : row.status.startsWith("Pending") && row.can_decide === true ? (
                    <>
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setCurrent(row);
                          setApproval(true);
                        }}
                      >
                        {t("Approve")}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setCurrent(row);
                          setApproval(false);
                        }}
                      >
                        {t("Reject")}
                      </Button>
                    </>
                  ) : null}
                </td>
              </tr>
            ))}
          </Table>
        </section>
      )}
      {requestOpen && (
        <Modal title="Request another audit type" onClose={() => setRequestOpen(false)}>
          <p>
            {t(
              "Sending this optional request does not change your current assessment. You may cancel and continue your existing work.",
            )}
          </p>
          {requestable.length > 1 && (
            <Field label="Audit type">
              <Select value={requestType} onChange={(e) => setRequestType(e.target.value)} required>
                <option value="">{t("Choose an assessment type")}</option>
                {requestable.map((name) => (
                  <option key={name} value={name}>
                    {assessmentTypes.label(name)}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Form
            onSubmit={async () => {
              if (!otherType) return;
              await request.execute({ entity, assessment_type: otherType });
              setRequested(true);
              setRequestOpen(false);
              await mutate();
            }}
          >
            <Button type="submit" loading={request.loading} disabled={!otherType}>
              {t("Send request")}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setRequestOpen(false)}>
              {t("Cancel")}
            </Button>
          </Form>
        </Modal>
      )}
      {current && (
        <Modal
          title={approval ? "Approve audit access" : "Reject audit access"}
          onClose={() => setCurrent(null)}
        >
          <p>
            {current.entity} · {t(current.assessment_type)}
          </p>
          <p className="notice">
            {t(
              approval
                ? current.status === "Pending Source Approval"
                  ? "This approval passes the request to the receiving department. It does not activate access yet."
                  : "This is the receiving department decision. Approval activates the additional audit access."
                : "Rejection ends this request and keeps current audit access unchanged.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              await decide.execute({ name: current.name, approve: approval, reason: values.reason });
              setCurrent(null);
              await mutate();
              refresh();
            }}
          >
            <Field label="Reason">
              <textarea name="reason" required maxLength={2000} />
            </Field>
            <Button type="submit" loading={decide.loading}>
              {t("Confirm")}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setCurrent(null)}>
              {t("Cancel")}
            </Button>
          </Form>
        </Modal>
      )}
      {!customer && session.can_manage_departments && <DepartmentStaff />}
    </>
  );
}

function DepartmentStaff() {
  const { session } = useSession(),
    { t } = useLanguage(),
    { data, error, mutate } = useData<DepartmentMember[]>("department_staff", undefined, 30000);
  const save = useMutation("save_department_staff"),
    [open, setOpen] = useState(false);
  const departmentTypes = useAssessmentTypes();
  const departments = session.is_admin
    ? departmentTypes.names
    : [
        ...new Set(
          session.department_memberships?.filter((d) => d.role === "Manager").map((d) => d.department) || [],
        ),
      ];
  return (
    <section className="panel padded">
      <div className="panel-heading">
        <h2>{t("Department staff")}</h2>
        <Button disabled={!departments.length} onClick={() => setOpen(true)}>
          {t("Add department staff")}
        </Button>
      </div>
      <p className="muted">
        {t(
          "Department membership controls which audit team a staff account belongs to. Customer access and assessment team allocation are separate steps.",
        )}
      </p>
      <p className="muted">
        {t(
          "Only app administrators can change manager memberships. Your own department access must remain active.",
        )}
      </p>
      <ErrorNotice error={error || save.error} />
      {!data ? (
        <Loading />
      ) : !data.length ? (
        <p>{t("No department staff")}</p>
      ) : (
        <Table headers={["Email", "Department", "Role", "Status", ""]}>
          {data.map((row) => (
            <tr key={row.name}>
              <td>{row.user}</td>
              <td>{t(row.department)}</td>
              <td>{t(row.role)}</td>
              <td>{t(row.active ? "Active" : "Inactive")}</td>
              <td>
                <Button
                  variant="ghost"
                  disabled={
                    (row.user === session.user && !!row.active) ||
                    (row.role === "Manager" && !session.is_admin)
                  }
                  loading={save.loading}
                  onClick={async () => {
                    await save.execute({
                      user: row.user,
                      department: row.department,
                      role: row.role,
                      active: row.active ? 0 : 1,
                    });
                    await mutate();
                  }}
                >
                  {t(row.active ? "Deactivate" : "Activate")}
                </Button>
              </td>
            </tr>
          ))}
        </Table>
      )}
      {open && (
        <Modal title="Add department staff" onClose={() => setOpen(false)}>
          <p>
            {t(
              "Use the email of an existing staff account. Ask an app administrator to create a new staff account before adding its department membership.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, active: 1 });
              setOpen(false);
              await mutate();
            }}
          >
            <Field label="Email">
              <input name="user" type="email" required />
            </Field>
            <Field label="Department">
              <Select name="department" required defaultValue={departments[0]}>
                {departments.map((d) => (
                  <option key={d} value={d}>
                    {t(d)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Role">
              <Select name="role" required defaultValue="Consultant">
                {(session.is_admin ? ["Manager", "Consultant", "Reviewer"] : ["Consultant", "Reviewer"]).map(
                  (role) => (
                    <option key={role} value={role}>
                      {t(role)}
                    </option>
                  ),
                )}
              </Select>
            </Field>
            <Button type="submit" loading={save.loading}>
              {t("Save changes")}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              {t("Cancel")}
            </Button>
          </Form>
        </Modal>
      )}
    </section>
  );
}
