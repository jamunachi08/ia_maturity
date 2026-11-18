import { useState } from "react";
import { UserRound, LockKeyhole, ShieldCheck } from "lucide-react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import { Button, Field, Form, PageTitle, Loading, ErrorNotice } from "../components";
import Select from "../Select";
import Authenticator from "./Authenticator";
import type { AuthenticatorStatus } from "./Authenticator";
import type { WorkspacePreferences as WorkspacePreferencesData } from "../types";

type ProfileData = {
  workspace_preferences?: WorkspacePreferencesData;
  name_repair_fields: string[];
  authenticator: AuthenticatorStatus;
  email: string;
  full_name: string;
  kind: string;
  modified: string;
  values: Record<string, string>;
  editable_fields: string[];
  fields: { fieldname: string; label: string; type: string }[];
  time_zones: string[];
};
export default function Profile() {
  const { data, error, mutate } = useData<ProfileData>("profile", undefined, 30000),
    { t } = useLanguage(),
    [tab, setTab] = useState("Personal details");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        eyebrow="Account"
        title="My profile"
        description={
          data.kind === "Customer"
            ? "Manage your personal details."
            : "Manage your personal details and password."
        }
      />
      <div className="profile-layout">
        <aside className="panel padded profile-summary">
          <div className="profile-avatar">{data.full_name.slice(0, 1)}</div>
          <h2>{data.full_name}</h2>
          <p>{data.email}</p>
          <span className="profile-role">
            <ShieldCheck size={15} />
            {t(data.kind === "Auditor" ? "Auditor workspace" : "Customer workspace")}
          </span>
          <p className="muted">
            {t("Your platform administrator controls which profile fields you can edit.")}
          </p>
        </aside>
        <div>
          <div className="tabs" role="tablist">
            {["Personal details", "Account security", "Workspace preferences"].map((label) => (
              <button
                key={label}
                role="tab"
                className={tab === label ? "active" : ""}
                aria-selected={tab === label}
                onClick={() => setTab(label)}
              >
                {t(label)}
              </button>
            ))}
          </div>
          {tab === "Personal details" ? (
            <ProfileDetails
              key={data.modified + data.editable_fields.join(",")}
              data={data}
              onSaved={() => void mutate()}
            />
          ) : tab === "Workspace preferences" ? (
            <WorkspacePreferences preferences={data.workspace_preferences} onSaved={() => void mutate()} />
          ) : data.kind === "Customer" ? (
            <section className="panel padded">
              <h2>{t("Account security")}</h2>
              <p>{t("Customers sign in with an email code every time. No password is needed.")}</p>
            </section>
          ) : (
            <>
              <Authenticator status={data.authenticator} email={data.email} />
              <PasswordForm email={data.email} />
            </>
          )}
        </div>
      </div>
    </>
  );
}
function WorkspacePreferences({
  preferences,
  onSaved,
}: {
  preferences?: WorkspacePreferencesData;
  onSaved: () => void;
}) {
  const save = useMutation("save_workspace_preferences"),
    { refresh } = useSession(),
    { t } = useLanguage();
  const [showTour, setShowTour] = useState(preferences?.show_page_tour !== false),
    [showHelp, setShowHelp] = useState(preferences?.show_help !== false);
  return (
    <section className="panel padded">
      <h2>{t("Workspace preferences")}</h2>
      <p className="muted">
        {t("Choose which help controls appear in your workspace. These settings apply only to your account.")}
      </p>
      <Form
        className="workspace-preferences-form"
        onSubmit={async () => {
          await save.execute({ data: { show_page_tour: showTour, show_help: showHelp } });
          onSaved();
          refresh();
        }}
      >
        <label className="checkbox">
          <input type="checkbox" checked={showTour} onChange={(e) => setShowTour(e.target.checked)} />
          {t("Show page tour button")}
        </label>
        <p className="muted">
          {t("Hiding the page tour also stops automatic tours. You can turn it back on here at any time.")}
        </p>
        <label className="checkbox">
          <input type="checkbox" checked={showHelp} onChange={(e) => setShowHelp(e.target.checked)} />
          {t("Show Help button")}
        </label>
        <Button type="submit">{t("Save workspace preferences")}</Button>
      </Form>
    </section>
  );
}
function ProfileDetails({ data, onSaved }: { data: ProfileData; onSaved: () => void }) {
  const save = useMutation("save_profile"),
    { refresh } = useSession(),
    { t, setLang } = useLanguage();
  return (
    <section className="panel padded">
      <h2 className="profile-section-title">
        <UserRound size={19} />
        {t("Personal details")}
      </h2>
      {data.name_repair_fields.length > 0 && (
        <p className="notice warning">
          {t(
            "Some saved name fields need correction. Enter your real name or ask your administrator to correct it.",
          )}
        </p>
      )}
      <Form
        noValidate
        onSubmit={async (values) => {
          await save.execute({ data: values });
          if (values.language && values.language !== data.values.language) setLang(values.language);
          onSaved();
          refresh();
        }}
      >
        <Field label="Email">
          <input value={data.email} readOnly type="email" />
          <small>{t("Your sign-in email and access roles are managed by an administrator.")}</small>
        </Field>
        <div className="form-grid">
          {data.fields.map((field) => {
            const editable = data.editable_fields.includes(field.fieldname);
            return (
              <Field
                key={field.fieldname}
                label={field.label}
                hint={editable ? undefined : "Managed by your platform administrator."}
              >
                {field.type === "language" ? (
                  <Select
                    name={field.fieldname}
                    defaultValue={data.values[field.fieldname] || "en"}
                    disabled={!editable}
                  >
                    <option value="en">English</option>
                    <option value="ar">العربية</option>
                  </Select>
                ) : field.type === "timezone" ? (
                  <Select
                    name={field.fieldname}
                    defaultValue={data.values[field.fieldname]}
                    disabled={!editable}
                  >
                    <option value="">{t("System default")}</option>
                    {data.time_zones.map((zone) => (
                      <option key={zone} value={zone}>
                        {zone.replaceAll("_", " ")}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <input
                    name={field.fieldname}
                    type={field.type}
                    defaultValue={data.values[field.fieldname]}
                    disabled={!editable}
                    required={field.fieldname === "first_name"}
                    maxLength={140}
                    autoComplete={
                      field.fieldname === "first_name"
                        ? "section-grc-profile given-name"
                        : field.fieldname === "middle_name"
                          ? "section-grc-profile additional-name"
                          : field.fieldname === "last_name"
                            ? "section-grc-profile family-name"
                            : field.type === "tel"
                              ? "section-grc-profile tel"
                              : "off"
                    }
                  />
                )}
              </Field>
            );
          })}
        </div>
        {data.editable_fields.length > 0 ? (
          <Button type="submit">{t("Save profile")}</Button>
        ) : (
          <p className="muted">{t("Profile editing is currently managed by your platform administrator.")}</p>
        )}
      </Form>
    </section>
  );
}
function PasswordForm({ email }: { email: string }) {
  const change = useMutation("change_password"),
    { t } = useLanguage(),
    [values, setValues] = useState({ current_password: "", new_password: "", confirm_password: "" });
  return (
    <section className="panel padded">
      <h2 className="profile-section-title">
        <LockKeyhole size={19} />
        {t("Change password")}
      </h2>
      <p className="muted profile-password-help">
        {t(
          "Enter your current password to choose a new one. You will be signed out of all sessions and asked to sign in again. MFA applies when required by policy.",
        )}
      </p>
      <Form
        noValidate
        onSubmit={async () => {
          const result = await change.execute(values);
          window.location.assign(result.redirect);
        }}
      >
        <input
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          readOnly
          value={email}
          autoComplete="username"
        />
        {(
          [
            ["current_password", "Current password"],
            ["new_password", "New password"],
            ["confirm_password", "Confirm new password"],
          ] as const
        ).map(([key, label]) => (
          <Field key={key} label={label}>
            <input
              type="password"
              name={key}
              required
              minLength={key === "current_password" ? undefined : 10}
              maxLength={1000}
              autoComplete={key === "current_password" ? "current-password" : "new-password"}
              value={values[key]}
              onChange={(e) => setValues({ ...values, [key]: e.target.value })}
            />
          </Field>
        ))}
        <Button type="submit">{t("Change password")}</Button>
      </Form>
    </section>
  );
}
