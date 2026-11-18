import { useState } from "react";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { Button, ErrorNotice, Field, Form, Modal, Table } from "../components";
import Select from "../Select";

export default function VerificationLimits() {
  const { t } = useLanguage(),
    inspect = useMutation("verification_limit_status"),
    clear = useMutation("clear_verification_limits"),
    policy = useData<{ email: boolean; ip: boolean }>("verification_limit_policy"),
    savePolicy = useMutation("set_verification_limit_policy");
  const [kind, setKind] = useState("email"),
    [target, setTarget] = useState(""),
    [result, setResult] = useState<any>(),
    [error, setError] = useState<any>(),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState(false),
    [message, setMessage] = useState("");
  function change() {
    setResult(undefined);
    setMessage("");
    setError(undefined);
  }
  async function check() {
    setBusy(true);
    setError(undefined);
    setMessage("");
    try {
      setResult(await inspect.execute({ kind, target }));
    } catch (e) {
      setResult(undefined);
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel padded">
      <h2>{t("Verification attempt limits")}</h2>
      <ErrorNotice error={policy.error} />
      {policy.data && (
        <>
          <h3>{t("Global verification protection")}</h3>
          <p>
            {t("Email request limit")}: <strong>{t(policy.data.email ? "Enabled" : "Disabled")}</strong> ·{" "}
            {t("IP attempt limit")}: <strong>{t(policy.data.ip ? "Enabled" : "Disabled")}</strong>
          </p>
          {(!policy.data.email || !policy.data.ip) && (
            <p className="notice warning" role="status">
              {t(
                "Verification attempt protection is disabled for at least one limit. This increases the risk of abuse.",
              )}
            </p>
          )}
          <Form
            key={String(policy.data.email) + String(policy.data.ip)}
            onSubmit={async (values) => {
              await savePolicy.execute({
                email_enabled: values.email_enabled,
                ip_enabled: values.ip_enabled,
                reason: values.reason,
              });
              await policy.mutate();
            }}
          >
            <div className="form-grid">
              <Field label="Email request limit">
                <Select name="email_enabled" defaultValue={policy.data.email ? "1" : "0"}>
                  <option value="1">{t("Enabled")}</option>
                  <option value="0">{t("Disabled")}</option>
                </Select>
              </Field>
              <Field label="IP attempt limit">
                <Select name="ip_enabled" defaultValue={policy.data.ip ? "1" : "0"}>
                  <option value="1">{t("Enabled")}</option>
                  <option value="0">{t("Disabled")}</option>
                </Select>
              </Field>
            </div>
            <p className="muted">
              {t(
                "Disabling a limit affects all customer verification attempts and increases the risk of abuse. Other security controls and mail-provider blocks remain in place.",
              )}
            </p>
            <Field label="Reason">
              <textarea name="reason" required minLength={3} maxLength={500} rows={2} />
            </Field>
            <Button type="submit">{t("Save verification protection")}</Button>
          </Form>
          <hr />
        </>
      )}
      <p className="muted">
        {t(
          "Inspect or reset temporary customer verification limits for one email address or IP. An IP reset affects everyone sharing that address. Other security controls and mail-provider blocks are not changed.",
        )}
      </p>
      <div className="form-grid">
        <Field label="Limit type">
          <Select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              change();
            }}
          >
            <option value="email">{t("Email address")}</option>
            <option value="ip">{t("IP address")}</option>
          </Select>
        </Field>
        <Field label={kind === "email" ? "Email address" : "IP address"}>
          <input
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              change();
            }}
            placeholder={kind === "email" ? "name@example.com" : "192.0.2.1"}
          />
        </Field>
      </div>
      <Button type="button" disabled={!target.trim() || busy} onClick={check}>
        {t("Check limits")}
      </Button>
      <ErrorNotice error={error} />
      {message && <p role="status">{t(message)}</p>}
      {result && (
        <>
          <p>
            {t("Target")}: <strong>{result.target}</strong>
          </p>
          <Table headers={["Limit", "Attempts", "Time remaining (seconds)"]}>
            {result.limits.map((v: any) => (
              <tr key={v.kind}>
                <td>{v.kind}</td>
                <td>{v.count}</td>
                <td>{v.active ? v.remaining_seconds : t("None")}</td>
              </tr>
            ))}
          </Table>
          <p className="muted">
            {t(
              "Counters can exist before the limit is reached. Resetting permits new attempts and is recorded in the activity log.",
            )}
          </p>
          <Button type="button" variant="secondary" onClick={() => setConfirm(true)}>
            {t("Reset limits")}
          </Button>
        </>
      )}
      {confirm && result && (
        <Modal title="Reset verification limits" onClose={() => setConfirm(false)}>
          <p>
            {t("Reset the temporary verification counters for")} <strong>{result.target}</strong>?
          </p>
          {kind === "ip" && <p>{t("This affects everyone using this IP address.")}</p>}
          <Form
            onSubmit={async (values) => {
              await clear.execute({ kind: result.kind, target: result.target, reason: values.reason });
              setConfirm(false);
              setResult(undefined);
              setMessage("Verification limits reset.");
            }}
          >
            <Field label="Reason">
              <textarea name="reason" required minLength={3} maxLength={500} rows={3} />
            </Field>
            <Button type="submit">{t("Confirm reset")}</Button>
          </Form>
        </Modal>
      )}
    </section>
  );
}
