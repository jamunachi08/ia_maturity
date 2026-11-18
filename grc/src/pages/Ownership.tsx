import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useData, useMutation } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { Button, ErrorNotice, Field, Form, Loading, PageTitle } from "../components";
import Select from "../Select";
import "../audit-packages.css";
import "../template-controls.css";

type OwnershipData = {
  entity: string;
  auditor: string;
  locked: boolean;
  modified: string;
  exceptions: { auditor: string; responsibility: string }[];
};
export function CustomerOwnership({ entity }: { entity: string }) {
  const { data, error, mutate } = useData<OwnershipData>("customer_ownership", { entity });
  const { data: staff } = useData<{ name: string; full_name: string; enabled: number }[]>("staff");
  if (error) return <ErrorNotice error={error} />;
  if (!data || !staff) return <Loading />;
  return (
    <OwnershipEditor
      key={data.modified}
      data={data}
      staff={staff.filter((s) => s.enabled)}
      reload={() => mutate()}
    />
  );
}
function OwnershipEditor({
  data,
  staff,
  reload,
}: {
  data: OwnershipData;
  staff: { name: string; full_name: string }[];
  reload: () => Promise<unknown>;
}) {
  const { t } = useLanguage(),
    save = useMutation("set_customer_ownership");
  const [exceptions, setExceptions] = useState(data.exceptions);
  return (
    <section className="panel padded ownership-panel" data-tour="customer-ownership">
      <h2>{t("Auditor ownership and access")}</h2>
      <p>
        {t(
          "Locked customers are visible to their owner and GRC administrators. Add named exceptions for reviewers or managers.",
        )}
      </p>
      <Form
        onSubmit={async (v) => {
          await save.execute({
            entity: data.entity,
            auditor: v.auditor,
            locked: v.locked ? 1 : 0,
            exceptions,
            reason: v.reason,
            modified: data.modified,
          });
          await reload();
        }}
      >
        <Field label="Owning auditor">
          <Select name="auditor" required defaultValue={data.auditor || ""}>
            <option value="">{t("No selection")}</option>
            {staff.map((s) => (
              <option key={s.name} value={s.name}>
                {s.full_name} · {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <label className="settings-check">
          <input type="checkbox" name="locked" defaultChecked={data.locked} />{" "}
          {t("Lock staff visibility to the owner and named exceptions")}
        </label>
        <h3>{t("Named staff exceptions")}</h3>
        <p>{t("A transfer removes the former owner unless you explicitly add them as an exception.")}</p>
        {exceptions.map((row, i) => (
          <div className="ownership-exception" key={i}>
            <Field label="Staff member">
              <Select
                value={row.auditor}
                onChange={(e) =>
                  setExceptions((rows) =>
                    rows.map((r, j) => (i === j ? { ...r, auditor: e.target.value } : r)),
                  )
                }
              >
                <option value="">{t("No selection")}</option>
                {staff.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.full_name} · {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Responsibility">
              <Select
                value={row.responsibility}
                onChange={(e) =>
                  setExceptions((rows) =>
                    rows.map((r, j) => (i === j ? { ...r, responsibility: e.target.value } : r)),
                  )
                }
              >
                {["Consultant", "Reviewer", "Manager"].map((r) => (
                  <option key={r} value={r}>
                    {t(r)}
                  </option>
                ))}
              </Select>
            </Field>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setExceptions((rows) => rows.filter((_, j) => j !== i))}
            >
              {t("Remove")}
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="secondary"
          onClick={() => setExceptions((rows) => [...rows, { auditor: "", responsibility: "Reviewer" }])}
        >
          {t("Add staff exception")}
        </Button>
        <Field label="Reason">
          <textarea name="reason" maxLength={2000} required />
        </Field>
        <Button type="submit">{t("Save ownership controls")}</Button>
      </Form>
    </section>
  );
}
export default function OwnershipSettings() {
  const { session } = useSession(),
    { t } = useLanguage();
  const { data, error, mutate } = useData<{ auto_lock: boolean; attention_hours: number }>(
    "ownership_settings",
  );
  const save = useMutation("save_ownership_settings");
  if (!session.is_admin) return <Navigate to={session.home} replace />;
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        title="Onboarding controls"
        description="Set defaults for new invitations and stalled onboarding."
      >
        <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
      </PageTitle>
      <section className="panel padded" data-tour="onboarding-controls">
        <Form
          onSubmit={async (v) => {
            await save.execute({ ...v, auto_lock: v.auto_lock ? 1 : 0 });
            await mutate();
          }}
        >
          <label className="settings-check">
            <input type="checkbox" name="auto_lock" defaultChecked={data.auto_lock} />{" "}
            {t("Automatically lock invited customers to the inviting auditor")}
          </label>
          <p>
            {t(
              "This default is saved with each invitation. Existing invitations and customers are unchanged.",
            )}
          </p>
          <Field label="Needs attention after hours">
            <input
              name="attention_hours"
              type="number"
              min={1}
              max={720}
              defaultValue={data.attention_hours}
              required
            />
          </Field>
          <Field label="Reason">
            <textarea name="reason" required maxLength={2000} />
          </Field>
          <Button type="submit">{t("Save controls")}</Button>
        </Form>
      </section>
    </>
  );
}
