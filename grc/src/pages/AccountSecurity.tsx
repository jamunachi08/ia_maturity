import { useState } from "react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import {
  Button,
  ErrorNotice,
  Field,
  Form,
  Loading,
  Modal,
  PageTitle,
  SearchInput,
  Table,
} from "../components";
import Select from "../Select";

type Settings = {
  policy: "Enabled" | "Disabled" | "Enforced" | null;
  method: "OTP App" | "Email";
  email_ready: boolean;
  blanket_mfa: boolean;
  centralized: boolean;
};
type Override = "Default" | "Required" | "Disabled";
type Account = {
  name: string;
  full_name: string;
  kind: string;
  policy: string;
  effective_policy?: string;
  roles?: string[];
  required: boolean;
  enrolled: boolean;
  email_verified: boolean;
};
type RolePolicy = { role: string; policy: Override };
type PolicyEditor = { kind: "user" | "role"; name: string; policy: Override };

export default function AccountSecurity() {
  const { t } = useLanguage(),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1),
    [editor, setEditor] = useState<PolicyEditor>();
  const {
    data: settings,
    error: settingsError,
    mutate: refreshSettings,
  } = useData<Settings>("security_mfa_settings");
  const {
    data,
    error,
    mutate: refreshAccounts,
  } = useData<{ rows: Account[]; has_more: boolean }>("security_accounts", { search, page });
  const {
    data: roles,
    error: rolesError,
    mutate: refreshRoles,
  } = useData<RolePolicy[]>("security_role_policies");
  const save = useMutation("save_mfa_settings"),
    saveUser = useMutation("set_mfa_policy"),
    saveRole = useMutation("set_role_mfa_policy");
  return (
    <>
      <PageTitle
        eyebrow="Administration"
        title="Account security"
        description="Staff use the configured MFA policy. Customers always use email OTP."
      />
      <section className="panel padded">
        <h2>{t("Central MFA settings")}</h2>
        <ErrorNotice error={settingsError} />
        {!settings ? (
          <Loading />
        ) : (
          <Form
            key={String(settings.policy) + settings.method}
            onSubmit={async (values) => {
              const result = await save.execute(values);
              if (result.reauthenticate) window.location.assign("/login");
              else {
                void refreshSettings();
                void refreshAccounts();
              }
            }}
          >
            <Field label="MFA policy">
              <Select name="policy" defaultValue={settings.policy || "Disabled"}>
                <option value="Enabled">{t("Enabled")}</option>
                <option value="Disabled">{t("Disabled")}</option>
                <option value="Enforced">{t("Enforced")}</option>
              </Select>
            </Field>
            <p className="muted">
              {t(
                "Staff MFA is disabled by default. Enabled allows staff to opt in; Enforced requires MFA by default. Role and individual policies can override this default. Customer email OTP remains required.",
              )}
            </p>
            <Field label="Verification method">
              <Select name="method" defaultValue={settings.method}>
                <option value="OTP App">{t("Authenticator app")}</option>
                <option value="Email">{t("Email code")}</option>
              </Select>
            </Field>
            <p className="muted">
              {t("The selected method also applies to other Frappe accounts that require MFA.")}
            </p>
            {!settings.email_ready && (
              <p className="notice warning">
                {t(
                  "Email codes need an active default outgoing email account. Configure and test email delivery before selecting Email code.",
                )}
              </p>
            )}
            {settings.blanket_mfa && (
              <p className="notice">
                {t(
                  "Saving replaces the inherited requirement for all users with this GRC policy. Existing MFA coverage for accounts outside GRC is preserved.",
                )}
              </p>
            )}
            <p>
              {t(
                "Changing staff MFA settings signs affected staff out. Staff without a password must use password recovery. Customer email OTP sign-in is unchanged.",
              )}
            </p>
            <Field label="Your current password">
              <input type="password" name="current_password" autoComplete="current-password" required />
            </Field>
            <Button type="submit">{t("Save central MFA settings")}</Button>
          </Form>
        )}
      </section>
      <section className="panel padded">
        <h2>{t("Staff role policies")}</h2>
        <p className="muted">
          {t(
            "Default follows the central staff policy. If a user has several roles, Required takes precedence over Disabled. An individual policy overrides all role policies.",
          )}
        </p>
        <ErrorNotice error={rolesError} />
        {!roles ? (
          <Loading />
        ) : (
          <Table headers={["Role", "MFA policy", "Actions"]}>
            {roles.map((row) => (
              <tr key={row.role}>
                <td>{t(row.role)}</td>
                <td>{t(row.policy)}</td>
                <td>
                  <Button
                    variant="secondary"
                    onClick={() => setEditor({ kind: "role", name: row.role, policy: row.policy })}
                  >
                    {t("Edit role policy")}
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </section>
      <section className="panel padded account-security-status">
        <h2>{t("Individual staff policies")}</h2>
        <p className="muted">
          {t(
            "Search by name or email. Required enables staff MFA; Disabled turns it off for that user; Default inherits the role and central policies. Customers always use email OTP.",
          )}
        </p>
        <div className="toolbar">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
          />
        </div>
        <ErrorNotice error={error} />
        {!data ? (
          <Loading />
        ) : (
          <>
            <Table
              headers={[
                "Name",
                "Email",
                "Account type",
                "Roles",
                "Email verified",
                "MFA policy",
                "MFA required",
                "Actions",
              ]}
            >
              {data.rows.map((row) => (
                <tr key={row.name}>
                  <td>{row.full_name}</td>
                  <td>{row.name}</td>
                  <td>{t(row.kind)}</td>
                  <td>{row.roles?.map((role) => t(role)).join(", ") || "—"}</td>
                  <td>{t(row.email_verified ? "Verified" : "Not recorded")}</td>
                  <td>{t(row.kind === "Customer" ? "Email OTP" : row.policy)}</td>
                  <td>{row.kind === "Customer" ? t("Email OTP") : t(row.required ? "Yes" : "No")}</td>
                  <td>
                    {row.kind !== "Customer" && (
                      <Button
                        variant="secondary"
                        onClick={() =>
                          setEditor({ kind: "user", name: row.name, policy: row.policy as Override })
                        }
                      >
                        {t("Edit security")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
            <div className="pagination">
              <Button variant="secondary" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
                {t("Previous")}
              </Button>
              <span>{page}</span>
              <Button variant="secondary" disabled={!data.has_more} onClick={() => setPage((p) => p + 1)}>
                {t("Next")}
              </Button>
            </div>
          </>
        )}
      </section>
      {editor && (
        <Modal
          title={editor.kind === "role" ? "MFA role policy" : "Individual MFA policy"}
          onClose={() => setEditor(undefined)}
        >
          <p>{editor.kind === "role" ? t(editor.name) : editor.name}</p>
          <Form
            key={editor.kind + editor.name}
            onSubmit={async (values) => {
              const result = await (editor.kind === "role" ? saveRole : saveUser).execute({
                ...values,
                [editor.kind === "role" ? "role" : "user"]: editor.name,
              });
              if (result.reauthenticate) {
                window.location.assign("/login");
                return;
              }
              setEditor(undefined);
              void refreshAccounts();
              void refreshRoles();
            }}
          >
            <Field label="MFA policy">
              <Select name="policy" defaultValue={editor.policy}>
                <option value="Default">{t("Default")}</option>
                <option value="Required">{t("Required")}</option>
                <option value="Disabled">{t("Disabled")}</option>
              </Select>
            </Field>
            <p className="muted">
              {t("Changes sign affected staff out. Other platform role security requirements still apply.")}
            </p>
            <Field label="Your current password">
              <input type="password" name="current_password" autoComplete="current-password" required />
            </Field>
            <div className="row-actions">
              <Button type="submit">{t("Save policy")}</Button>
              <Button type="button" variant="secondary" onClick={() => setEditor(undefined)}>
                {t("Cancel")}
              </Button>
            </div>
          </Form>
        </Modal>
      )}
    </>
  );
}
