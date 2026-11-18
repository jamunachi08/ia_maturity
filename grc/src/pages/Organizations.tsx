import { useAssessmentTypes } from "../assessmentTypes";
import Select from "../Select";
import OrganizationProfile from "../OrganizationProfile";
import { CustomerOwnership } from "./Ownership";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Plus, ArrowUpRight, Building2 } from "lucide-react";
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
  SearchInput,
  Table,
  Pagination,
  Status,
} from "../components";
import { SectorSelect } from "../components";
import { OrganizationSetup } from "./Dashboard";

export function OrganizationsPage() {
  const { session } = useSession(),
    { t } = useLanguage(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1),
    [creating, setCreating] = useState(false);
  const { data, error } = useData<any[]>("organizations");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  if (creating)
    return (
      <>
        <Button variant="ghost" onClick={() => setCreating(false)}>
          {t("Back")}
        </Button>
        <OrganizationSetup />
      </>
    );
  if (!data.length && session.kind === "Customer") return <OrganizationSetup />;
  const rows = data.filter((o) =>
    (o.entity_name + " " + o.sector).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        title={session.kind === "Auditor" ? "Assigned customers" : "Organization"}
        description="Your authorized organizations and department access determine which records appear here."
      >
        {(session.kind === "Customer" ||
          session.is_admin ||
          (session.department_memberships?.length === 1 &&
            session.staff_roles?.some((r) =>
              ["GRC Auditor", "GRC Consultant", "GRC Manager", "IA Maturity Manager"].includes(r),
            ))) && <Button onClick={() => setCreating(true)}>{t("Create organization")}</Button>}
      </PageTitle>
      <p className="notice">
        {t(
          session.kind === "Auditor"
            ? "Open a customer to view the organization and permitted management controls. To invite a new customer, use Customer onboarding; a manager assigns existing customers."
            : "Open your organization to manage permitted details and members. Return to Assessments to continue the customer journey.",
        )}
      </p>
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
        {!rows.length ? (
          <Empty
            title={search ? "No matching organizations" : "No customers assigned"}
            text={
              search
                ? "Clear the search to see every organization available to you."
                : "Invite a customer through Customer onboarding if permitted, or ask your department manager to assign an existing customer."
            }
          >
            {search ? (
              <Button variant="secondary" onClick={() => setSearch("")}>
                {t("Clear filter")}
              </Button>
            ) : (
              session.can_invite_customers && (
                <Link className="button secondary" to={session.home + "/onboarding"}>
                  {t("Customer onboarding")}
                </Link>
              )
            )}
          </Empty>
        ) : (
          <Table headers={["Organization", "Sector", "Contact email", ""]}>
            {rows.slice((page - 1) * 15, page * 15).map((o) => (
              <tr key={o.name}>
                <td>
                  <span className="owner-cell">
                    <Building2 size={18} />
                    <strong>{o.entity_name}</strong>
                  </span>
                </td>
                <td>{o.sector || "—"}</td>
                <td>{o.contact_email || "—"}</td>
                <td>
                  <Link
                    className="button ghost"
                    to={
                      session.home +
                      (session.kind === "Auditor" ? "/customers/" : "/organization/") +
                      encodeURIComponent(o.name)
                    }
                  >
                    {t("Open")}
                    <ArrowUpRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
    </>
  );
}
export function OrganizationPage() {
  const assessmentTypes = useAssessmentTypes();
  const { name } = useParams(),
    { session } = useSession(),
    { t, lang } = useLanguage();
  const { data, error, mutate } = useData<any>("organization_detail", { name });
  const save = useMutation("save_organization"),
    unit = useMutation("save_unit"),
    invite = useMutation("invite_member"),
    member = useMutation("update_membership"),
    revoke = useMutation("revoke_invitation");
  const [tab, setTab] = useState("Profile"),
    [dialog, setDialog] = useState(""),
    [selected, setSelected] = useState<any>(null);
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const types = session.audit_type_access?.[name!] || session.allowed_assessment_types;
  const tabs = [
    "Profile",
    ...(data.can_view_company_profile !== false &&
    (session.is_admin || !types || types.some((name) => assessmentTypes.requiresProfile(name)))
      ? ["Company profile"]
      : []),
    "Departments & branches",
    ...(data.can_manage || session.kind === "Auditor" ? ["Members"] : []),
    ...(data.can_manage ? ["Invitations"] : []),
    ...((data.can_manage || session.kind === "Auditor") &&
    (session.is_admin || !types || types.some((name) => assessmentTypes.behaviour(name) === "Internal Audit"))
      ? ["Audit issues"]
      : []),
  ];
  return (
    <>
      <PageTitle eyebrow="Organization" title={data.entity_name} description={data.sector}>
        {data.can_manage && (
          <Button
            onClick={() => {
              setSelected({ membership_role: "Organization Admin" });
              setDialog("invite");
            }}
          >
            {t("Invite Customer Admin")}
          </Button>
        )}
      </PageTitle>
      {!data.can_manage && !data.read_only && (
        <p className="notice">
          {t(
            "Organization details are read-only for your account. An authorized organization administrator or customer manager can update them.",
          )}
        </p>
      )}
      {data.can_assign_staff && data.ownership_locked && (
        <p className="notice">
          {t(
            "Customer ownership is locked. Ask an app administrator to review ownership controls or grant a staff access exception before changing assignments.",
          )}
        </p>
      )}
      {data.read_only && (
        <p className="notice">
          {t("Holding company access is read-only. Editing requires direct organization authorization.")}
        </p>
      )}
      <div className="tabs" role="tablist">
        {tabs.map((item) => (
          <button
            role="tab"
            aria-selected={tab === item}
            key={item}
            className={tab === item ? "active" : ""}
            onClick={() => setTab(item)}
          >
            {item === "Company profile" && lang === "ar" ? "ملف المنشأة" : t(item)}
          </button>
        ))}
      </div>
      {tab === "Profile" && (
        <section className="panel padded">
          <Form
            onSubmit={async (values) => {
              await save.execute({ name, data: values });
              mutate();
            }}
          >
            <div className="form-grid">
              <Field label="Organization name">
                <input value={data.entity_name} readOnly />
              </Field>
              <Field label="Sector">
                <SectorSelect defaultValue={data.sector} disabled={!data.can_manage} />
              </Field>
              <Field label="Contact email">
                <input
                  type="email"
                  name="contact_email"
                  defaultValue={data.contact_email}
                  disabled={!data.can_manage}
                />
              </Field>
              <Field label="Listed company">
                <Select name="listed_company" defaultValue={data.listed_company} disabled={!data.can_manage}>
                  <option value="0">{t("No")}</option>
                  <option value="1">{t("Yes")}</option>
                </Select>
              </Field>
            </div>
            <Field label="Parent organization">
              <Select
                name="parent_organization"
                defaultValue={data.parent_organization || ""}
                disabled={!session.is_admin}
              >
                <option value="">{t("No selection")}</option>
                {session.organizations
                  ?.filter((o) => o.name !== name)
                  .map((o) => (
                    <option key={o.name}>{o.name}</option>
                  ))}
              </Select>
            </Field>
            <Field label="Regulators">
              <input name="regulators" defaultValue={data.regulators} disabled={!data.can_manage} />
            </Field>
            <Field label="Notes">
              <textarea name="notes" defaultValue={data.notes} disabled={!data.can_manage} />
            </Field>
            {data.can_manage && (
              <>
                <h3>{t("Optional organization emails")}</h3>
                <p className="muted">
                  {t(
                    "Optional emails require both organization and individual permission. Verification, security, invitations and clarification requests are mandatory.",
                  )}
                </p>
                {[
                  ["grc_optional_reminders", "Optional reminders"],
                  ["grc_optional_status_updates", "Optional status updates"],
                ].map(([key, label]) => (
                  <Field key={key} label={label}>
                    <Select name={key} defaultValue={data[key] ?? 1}>
                      <option value="1">{t("Enabled")}</option>
                      <option value="0">{t("Disabled")}</option>
                    </Select>
                  </Field>
                ))}
              </>
            )}
            {data.can_manage && <Button type="submit">{t("Save changes")}</Button>}
          </Form>
        </section>
      )}
      {tab === "Company profile" && <OrganizationProfile entity={name!} onDone={() => void mutate()} />}
      {tab === "Departments & branches" && (
        <section className="panel">
          <div className="panel-heading">
            <h2>{t(tab)}</h2>
            {data.can_manage && (
              <Button
                onClick={() => {
                  setSelected(null);
                  setDialog("unit");
                }}
              >
                <Plus size={16} />
                {t("Add unit")}
              </Button>
            )}
          </div>
          {!data.units.length ? (
            <Empty
              title="No departments or branches"
              text="Organization units are optional. An authorized organization manager can add them when needed."
            />
          ) : (
            <Table headers={["Name", "Type", "Responsibilities", ""]}>
              {data.units.map((u: any) => (
                <tr key={u.name}>
                  <td>{u.unit_name}</td>
                  <td>{t(u.unit_type)}</td>
                  <td>{u.responsibilities}</td>
                  <td>
                    {data.can_manage && (
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setSelected(u);
                          setDialog("unit");
                        }}
                      >
                        {t("Edit")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </section>
      )}
      {session.is_admin && <CustomerOwnership entity={name!} />}
      {data.can_assign_staff && !data.ownership_locked && (
        <OrganizationStaffAssignments entity={name!} auditors={data.auditors} onDone={() => void mutate()} />
      )}
      {tab === "Members" && (
        <section className="panel">
          <Table headers={["Member", "Role", "Status", ""]}>
            {data.members.map((m: any) => (
              <tr key={m.name}>
                <td>{m.user}</td>
                <td>{t(m.membership_role)}</td>
                <td>
                  <Status value={m.active ? "Active" : "Inactive"} />
                </td>
                <td>
                  {data.can_manage && (
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setSelected(m);
                        setDialog("member");
                      }}
                    >
                      {t("Edit")}
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </section>
      )}
      {tab === "Invitations" && (
        <section className="panel">
          <div className="panel-heading">
            <h2>{t(tab)}</h2>
            <Button onClick={() => setDialog("invite")}>
              <Plus size={16} />
              {t("Invite member")}
            </Button>
          </div>
          <Table headers={["Email", "Role", "Status", "Expires", ""]}>
            {data.invitations.map((i: any) => (
              <tr key={i.name}>
                <td>{i.email}</td>
                <td>{t(i.membership_role)}</td>
                <td>
                  <Status value={i.status} />
                </td>
                <td>{i.expires_on?.slice(0, 10)}</td>
                <td>
                  {i.status === "Pending" && (
                    <Form
                      onSubmit={async () => {
                        await revoke.execute({ name: i.name });
                        mutate();
                      }}
                    >
                      <Button type="submit" variant="ghost">
                        {t("Revoke")}
                      </Button>
                    </Form>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </section>
      )}
      {tab === "Audit issues" && <Issues entity={name!} canManage={!!data.can_manage} />}
      {dialog && (
        <Modal
          title={
            dialog === "unit"
              ? "Departments & branches"
              : dialog === "invite"
                ? "Invite member"
                : "Edit membership"
          }
          onClose={() => setDialog("")}
        >
          <Form
            onSubmit={async (values) => {
              if (dialog === "unit") await unit.execute({ ...values, entity: name, name: selected?.name });
              else if (dialog === "invite") await invite.execute({ ...values, entity: name });
              else await member.execute({ ...values, name: selected.name });
              await mutate();
              setDialog("");
            }}
          >
            {dialog === "unit" ? (
              <>
                <Field label="Name">
                  <input name="unit_name" defaultValue={selected?.unit_name} required />
                </Field>
                <Field label="Type">
                  <Select name="unit_type" defaultValue={selected?.unit_type || "Department"}>
                    <option>Department</option>
                    <option>Branch</option>
                  </Select>
                </Field>
                <Field label="Responsibilities">
                  <textarea name="responsibilities" defaultValue={selected?.responsibilities} />
                </Field>
              </>
            ) : (
              <>
                {dialog === "invite" && (
                  <Field label="Email">
                    <input type="email" name="email" required />
                  </Field>
                )}
                <Field label="Role">
                  <Select name="membership_role" defaultValue={selected?.membership_role || "Contributor"}>
                    {["Organization Admin", "Contributor", "Viewer"].map((r) => (
                      <option key={r} value={r}>
                        {t(r)}
                      </option>
                    ))}
                  </Select>
                </Field>
                {dialog === "member" && (
                  <Field label="Status">
                    <Select name="active" defaultValue={selected.active}>
                      <option value="1">{t("Active")}</option>
                      <option value="0">{t("Inactive")}</option>
                    </Select>
                  </Field>
                )}
              </>
            )}
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}
function Issues({ entity, canManage }: { entity: string; canManage: boolean }) {
  const { t } = useLanguage(),
    { data, error, mutate } = useData<any[]>("issues", { entity }),
    save = useMutation("save_issue"),
    [selected, setSelected] = useState<any>();
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{t("Audit issues")}</h2>
          <p className="muted">{t("Validated issue records support the Q13 closure calculation.")}</p>
        </div>
        {canManage && (
          <Button onClick={() => setSelected({})}>
            <Plus size={16} />
            {t("Add issue")}
          </Button>
        )}
      </div>
      <ErrorNotice error={error} />
      <Table headers={["Name", "Status", "Rating", "Due date", ""]}>
        {data?.map((i) => (
          <tr key={i.name}>
            <td>{i.title}</td>
            <td>
              <Status value={i.status} />
            </td>
            <td>{i.rating}</td>
            <td>{i.due_date}</td>
            <td>
              {canManage ? (
                <Button variant="ghost" onClick={() => setSelected(i)}>
                  {t("Edit")}
                </Button>
              ) : (
                <span className="muted">{t("Read-only")}</span>
              )}
            </td>
          </tr>
        ))}
      </Table>
      {!canManage && (
        <p className="notice">
          {t(
            "Issue records are read-only for your account. Ask the customer manager to record or update an issue.",
          )}
        </p>
      )}
      {selected && canManage && (
        <Modal title="Audit issue" onClose={() => setSelected(undefined)}>
          <Form
            onSubmit={async (values) => {
              await save.execute({ entity, name: selected.name, data: values });
              mutate();
              setSelected(undefined);
            }}
          >
            <Field label="Name">
              <input name="title" defaultValue={selected.title} required />
            </Field>
            <div className="form-grid">
              <Field label="Status">
                <Select name="status" defaultValue={selected.status || "Open"}>
                  {["Open", "In Progress", "Closed"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Rating">
                <Select name="rating" defaultValue={selected.rating || "Medium"}>
                  {["Low", "Medium", "High"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </Select>
              </Field>
              {["raised_on", "due_date", "closed_on"].map((k) => (
                <Field key={k} label={k.replaceAll("_", " ")}>
                  <input
                    type="date"
                    name={k}
                    defaultValue={selected[k] || undefined}
                    required={k === "raised_on"}
                  />
                </Field>
              ))}
            </div>
            <Field label="Description">
              <textarea name="description" defaultValue={selected.description} />
            </Field>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </section>
  );
}

function OrganizationStaffAssignments({
  entity,
  auditors,
  onDone,
}: {
  entity: string;
  auditors: any[];
  onDone: () => void;
}) {
  const { t } = useLanguage(),
    { session } = useSession(),
    { data: staff } = useData<any[]>("staff", { entity }),
    save = useMutation("assign_customer");
  const [selected, setSelected] = useState<any>();
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{t("Customer assignments")}</h2>
        <Button disabled={!staff?.some((s) => s.enabled)} onClick={() => setSelected({})}>
          {t("Assign customer")}
        </Button>
      </div>
      <p className="muted">
        {t(
          "Assign customer access first, then allocate the consultant and reviewer on the assessment. Customer access alone does not allocate a review task.",
        )}
      </p>
      <Table headers={["Auditor", "Responsibility", "Status", ""]}>
        {auditors.map((a) => (
          <tr key={a.name}>
            <td>{a.auditor}</td>
            <td>{t(a.responsibility)}</td>
            <td>
              <Status value={a.active ? "Active" : "Revoked"} />
            </td>
            <td>
              {(session.is_admin || a.responsibility !== "Manager") && (
                <Button variant="ghost" onClick={() => setSelected(a)}>
                  {t("Edit")}
                </Button>
              )}
            </td>
          </tr>
        ))}
      </Table>
      {staff && !staff.some((s) => s.enabled) && (
        <p className="notice">
          {t(
            "No eligible active staff are available. Ask an app administrator to configure staff department membership before assigning this customer.",
          )}
        </p>
      )}
      {selected && (
        <Modal title="Customer assignment" onClose={() => setSelected(undefined)}>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, entity });
              onDone();
              setSelected(undefined);
            }}
          >
            <Field label="Auditor">
              <Select name="auditor" defaultValue={selected.auditor} required>
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
              <Select name="responsibility" defaultValue={selected.responsibility || "Consultant"}>
                {["Consultant", "Reviewer", ...(session.is_admin ? ["Manager"] : [])].map((r) => (
                  <option key={r} value={r}>
                    {t(r)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Status">
              <Select name="active" defaultValue={selected.active ?? 1}>
                <option value="1">{t("Active")}</option>
                <option value="0">{t("Revoked")}</option>
              </Select>
            </Field>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </section>
  );
}
