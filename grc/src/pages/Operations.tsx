import Select from "../Select";
import { assessmentMilestones } from "../assessmentMilestones";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Paperclip, Clock3 } from "lucide-react";
import { useData, useMutation, upload } from "../api";
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

export function ActionsPage() {
  const { session, activeOrganization } = useSession(),
    { t } = useLanguage(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState<any>();
  const { data, error, mutate } = useData<any>("actions", {
      search,
      page,
      entity: activeOrganization || undefined,
    }),
    save = useMutation("update_action"),
    remove = useMutation("delete_evidence");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        title="Improvement actions"
        description="Track ownership, completion evidence, and independently verified closure."
      />
      <p className="notice">
        {t(
          "Open an assigned action, record progress and attach completion evidence. Submit Pending Verification when ready; an authorized verifier confirms closure.",
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
        {!data.items.length ? (
          <Empty
            title={search ? "No matching actions" : "No improvement actions yet"}
            text={
              search
                ? "Clear the search to see all actions available to you."
                : "Actions appear when assessment findings create work for your organization. You can continue assessments without creating an action here."
            }
          >
            <Link className="button secondary" to={session.home + "/assessments"}>
              {t("Assessments")}
            </Link>
          </Empty>
        ) : (
          <Table headers={["Action", "Organization", "Status", "Owner", "Due date", ""]}>
            {data.items.map((a: any) => (
              <tr key={a.name}>
                <td>
                  <strong>{a.finding_title}</strong>
                  <small>{a.priority}</small>
                </td>
                <td>{a.entity}</td>
                <td>
                  <Status value={a.status} />
                </td>
                <td>{a.assigned_to || "—"}</td>
                <td>{a.due_date || "—"}</td>
                <td>
                  <Button variant="ghost" onClick={() => setSelected(a)}>
                    {t("Open")}
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
        <Pagination page={page} total={data.total} onPage={setPage} />
      </section>
      {selected && (
        <Modal title="Improvement action" onClose={() => setSelected(undefined)}>
          <p>
            <strong>{selected.finding_title}</strong>
          </p>
          <p className="muted">{selected.recommended_action}</p>
          <p className="notice">
            {t(
              !selected.can_edit
                ? "This action is read-only for your account. Ask the assigned owner or an authorized verifier to update it."
                : selected.can_verify
                  ? "You can verify completion. Check the notes and evidence before choosing Completed."
                  : "Record your progress and evidence, then choose Pending Verification. Only an authorized verifier can mark it Completed.",
            )}
          </p>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, name: selected.name, evidence: selected.evidence });
              mutate();
              setSelected(undefined);
            }}
          >
            <fieldset disabled={!selected.can_edit}>
              <div className="form-grid">
                <Field label="Status">
                  <Select name="status" defaultValue={selected.status}>
                    {[
                      "Open",
                      "In Progress",
                      "Pending Verification",
                      ...(selected.can_verify || selected.status === "Completed" ? ["Completed"] : []),
                    ].map((s) => (
                      <option key={s} value={s}>
                        {t(s)}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Due date">
                  <input
                    type="date"
                    name="due_date"
                    disabled={!selected.can_assign}
                    defaultValue={selected.due_date || ""}
                  />
                </Field>
              </div>
              <Field label="Owner">
                <input
                  type="email"
                  name="assigned_to"
                  disabled={!selected.can_assign}
                  defaultValue={selected.assigned_to || ""}
                />
              </Field>
              <Field label="Completion notes">
                <textarea name="completion_notes" defaultValue={selected.completion_notes} />
              </Field>
              <div className="evidence-row">
                {selected.evidence && (
                  <a href={selected.evidence} target="_blank" rel="noreferrer">
                    {t("View evidence")}
                  </a>
                )}
                {selected.evidence &&
                  selected.can_edit &&
                  !["Completed", "Cancelled"].includes(selected.status) && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={async () => {
                        try {
                          await remove.execute({
                            name: selected.name,
                            file_url: selected.evidence,
                            doctype: "IA Maturity Action",
                          });
                          setSelected({ ...selected, evidence: "", uploadError: null });
                          mutate();
                        } catch (err) {
                          setSelected({ ...selected, uploadError: err });
                        }
                      }}
                    >
                      {t("Delete evidence")}
                    </Button>
                  )}
                <label className="button secondary upload-button">
                  <Paperclip size={16} />
                  {t("Attach evidence")}
                  <input
                    type="file"
                    onChange={async (e) => {
                      if (e.target.files?.[0]) {
                        try {
                          const result = await upload(selected.name, e.target.files[0], "IA Maturity Action");
                          setSelected({ ...selected, evidence: result.file_url, uploadError: null });
                        } catch (err) {
                          setSelected({ ...selected, uploadError: err });
                        }
                      }
                    }}
                  />
                </label>
              </div>
              <ErrorNotice error={selected.uploadError} />
              {selected.can_edit && <Button type="submit">{t("Save changes")}</Button>}
            </fieldset>
          </Form>
        </Modal>
      )}
    </>
  );
}
export function ActivityPage({ assignment }: { assignment?: string }) {
  const { session, activeOrganization } = useSession(),
    { t } = useLanguage(),
    [entity, setEntity] = useState(activeOrganization),
    [page, setPage] = useState(1);
  const { data: events, error } = useData<any[]>("activity", { entity: entity || undefined, assignment });
  const customer = session.kind === "Customer",
    data = events ? (customer ? assessmentMilestones(events) : events) : undefined;
  return (
    <>
      {!assignment && (
        <PageTitle
          title={customer ? "Assessment dates" : "Activity"}
          description={
            customer
              ? "When your assessments were started and finished."
              : "A traceable history of assessment progress and authorized changes."
          }
        />
      )}
      <section className="panel">
        <div className="toolbar">
          {!!session.organizations?.length && (
            <Select
              aria-label={t("Organization")}
              value={entity}
              onChange={(e) => {
                setEntity(e.target.value);
                setPage(1);
              }}
            >
              <option value="">{t("All organizations")}</option>
              {session.organizations?.map((o) => (
                <option key={o.name}>{o.name}</option>
              ))}
            </Select>
          )}
        </div>
        <p className="muted">
          {t(
            "This history is read-only. The organization filter is optional; continue assessments from the Assessments page.",
          )}
        </p>
        <ErrorNotice error={error} />
        {!data ? (
          <Loading />
        ) : !data.length ? (
          <Empty
            title={customer ? "No assessment dates yet" : "No activity yet"}
            text={
              customer
                ? "Start an assessment to record its start date. Its finish date appears after submission."
                : "Activity appears as assigned customers and assessments progress. No selection or entry is required here."
            }
          >
            <Link className="button secondary" to={session.home + "/assessments"}>
              {t("Assessments")}
            </Link>
          </Empty>
        ) : (
          <ol className="timeline">
            {data.slice((page - 1) * 15, page * 15).map((a) => (
              <li key={a.name}>
                <div className="timeline-icon">
                  <Clock3 size={17} />
                </div>
                <div>
                  <strong>{t(a.action)}</strong>
                  <p>
                    {a.entity}
                    {!customer && <> · {a.actor}</>}
                  </p>
                  {a.assessment && (
                    <Link to={session.home + "/assessments/" + a.assessment}>{a.assessment}</Link>
                  )}
                  <time>{new Date(a.creation).toLocaleString()}</time>
                  {!customer && a.details && a.details !== "{}" && (
                    <details>
                      <summary>{t("Details")}</summary>
                      <pre>{JSON.stringify(JSON.parse(a.details), null, 2)}</pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        <Pagination page={page} total={data?.length || 0} onPage={setPage} />
      </section>
    </>
  );
}
export function FollowupsPage() {
  const { session, activeOrganization } = useSession(),
    { t } = useLanguage(),
    { data, error, mutate } = useData<any[]>("followups", { entity: activeOrganization || undefined }),
    save = useMutation("save_followup");
  const [selected, setSelected] = useState<any>(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const manageable =
    session.organizations?.filter((o) =>
      session.managed_entities !== undefined
        ? session.managed_entities.includes(o.name)
        : session.is_admin ||
          session.assignments?.some(
            (a) => a.entity === o.name && ["Manager", "Consultant"].includes(a.responsibility),
          ),
    ) || [];
  const canEdit = (row: any) => row.can_edit ?? manageable.some((o) => o.name === row.entity);
  const rows =
    data?.filter((a) => (a.note + " " + a.entity).toLowerCase().includes(search.toLowerCase())) || [];
  return (
    <>
      <PageTitle
        title="Customer follow-ups"
        description="Record customer contact, next steps, and accountable deadlines."
      >
        <Button disabled={!manageable.length} onClick={() => setSelected({})}>
          <Plus size={16} />
          {t("Add follow-up")}
        </Button>
      </PageTitle>
      <p className="notice">
        {t(
          manageable.length
            ? "Follow-ups are optional contact notes. Choose a customer you manage, record the next action and set an owner; they do not replace assessment submission."
            : "You can view follow-ups for assigned customers. Creating or editing a follow-up requires customer management access; ask your department manager if you need it.",
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
        <ErrorNotice error={error} />
        {!data ? (
          <Loading />
        ) : !rows.length ? (
          <Empty
            title={search ? "No matching follow-ups" : "No customer follow-ups yet"}
            text={
              search
                ? "Clear the search to see all follow-ups available to you."
                : manageable.length
                  ? "Use Add follow-up when you need to record customer contact. You can close the form without saving."
                  : "Follow-ups will appear when authorized staff record customer contact. Continue your assigned assessments in the meantime."
            }
          />
        ) : (
          <Table headers={["Organization", "Note", "Owner", "Due date", "Status", ""]}>
            {rows.slice((page - 1) * 15, page * 15).map((a) => (
              <tr key={a.name}>
                <td>{a.entity}</td>
                <td>{a.note}</td>
                <td>{a.assigned_to}</td>
                <td>{a.due_date || "—"}</td>
                <td>
                  <Status value={a.status} />
                </td>
                <td>
                  {canEdit(a) ? (
                    <Button variant="ghost" onClick={() => setSelected(a)}>
                      {t("Edit")}
                    </Button>
                  ) : (
                    <span className="muted">{t("Read-only")}</span>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        )}
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
      {selected && (
        <Modal title="Follow-up" onClose={() => setSelected(undefined)}>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, name: selected.name });
              mutate();
              setSelected(undefined);
            }}
          >
            <Field label="Organization">
              <Select
                name="entity"
                required
                defaultValue={selected.entity || activeOrganization || manageable[0]?.name}
              >
                {manageable.map((o) => (
                  <option key={o.name}>{o.name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Note">
              <textarea name="note" defaultValue={selected.note} required />
            </Field>
            <div className="form-grid">
              <Field label="Due date">
                <input type="date" name="due_date" defaultValue={selected.due_date || ""} />
              </Field>
              <Field label="Status">
                <Select name="status" defaultValue={selected.status || "Open"}>
                  <option>Open</option>
                  <option>Completed</option>
                </Select>
              </Field>
            </div>
            <Field label="Owner">
              <input
                type="email"
                name="assigned_to"
                defaultValue={selected.assigned_to || session.user}
                required
              />
            </Field>
            <Button type="submit">{t("Save changes")}</Button>
            <Button type="button" variant="secondary" onClick={() => setSelected(undefined)}>
              {t("Cancel")}
            </Button>
          </Form>
        </Modal>
      )}
    </>
  );
}
export function ConsultationsPage() {
  const { t } = useLanguage(),
    { data, error, mutate } = useData<any[]>("consultations"),
    save = useMutation("update_consultation");
  const [selected, setSelected] = useState<any>(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const rows =
    data?.filter((a) =>
      (a.full_name + " " + a.organization + " " + a.email).toLowerCase().includes(search.toLowerCase()),
    ) || [];
  return (
    <>
      <PageTitle title="Consultation requests" />
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
        <Table headers={["Name", "Organization", "Email", "Status", ""]}>
          {rows.slice((page - 1) * 15, page * 15).map((a) => (
            <tr key={a.name}>
              <td>{a.full_name}</td>
              <td>{a.organization}</td>
              <td>{a.email}</td>
              <td>
                <Status value={a.status} />
              </td>
              <td>
                <Button variant="ghost" onClick={() => setSelected(a)}>
                  {t("Open")}
                </Button>
              </td>
            </tr>
          ))}
        </Table>
        <Pagination page={page} total={rows.length} onPage={setPage} />
      </section>
      {selected && (
        <Modal title="Consultation request" onClose={() => setSelected(undefined)}>
          <p>{selected.service}</p>
          <p>{selected.message}</p>
          <Form
            onSubmit={async (values) => {
              await save.execute({ ...values, name: selected.name });
              mutate();
              setSelected(undefined);
            }}
          >
            <Field label="Status">
              <Select name="status" defaultValue={selected.status}>
                {["New", "Contacted", "Closed"].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </Select>
            </Field>
            <Button type="submit">{t("Save changes")}</Button>
          </Form>
        </Modal>
      )}
    </>
  );
}
