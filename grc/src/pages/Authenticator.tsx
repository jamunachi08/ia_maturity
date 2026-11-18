import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useMutation } from "../api";
import { useLanguage } from "../i18n";
import { Button, Field, Form } from "../components";

export type AuthenticatorStatus = {
  available: boolean;
  required: boolean;
  enrolled: boolean;
  can_enroll: boolean;
  policy: string;
  method?: string;
  centralized?: boolean;
  optional_enrolled?: boolean;
};
export default function Authenticator({ status, email }: { status: AuthenticatorStatus; email: string }) {
  const { t } = useLanguage(),
    begin = useMutation("begin_authenticator"),
    confirm = useMutation("confirm_authenticator"),
    optional = useMutation("set_optional_mfa");
  const [pending, setPending] = useState<{ qr_code: string; setup_token: string }>(),
    [password, setPassword] = useState(""),
    [code, setCode] = useState("");
  const optionalControl = status.centralized && status.policy === "Enabled" && (
    <Form
      onSubmit={async (values) => {
        const result = await optional.execute({ enabled: status.optional_enrolled ? 0 : 1, ...values });
        window.location.assign(result.redirect);
      }}
    >
      <Field label="Current password">
        <input type="password" name="current_password" autoComplete="current-password" required />
      </Field>
      <Button type="submit">
        {t(status.optional_enrolled ? "Turn off optional MFA" : "Enable email codes")}
      </Button>
    </Form>
  );
  if (status.method === "Email")
    return (
      <section className="panel padded">
        <h2 className="profile-section-title">
          <ShieldCheck size={19} />
          {t("Email verification codes")}
        </h2>
        <p>
          {t(
            status.policy === "Disabled"
              ? "MFA is disabled by your GRC administrator."
              : status.required
                ? "Sign in with your password, then enter the code sent to your registered email."
                : "You can add an email verification code after your password at sign-in.",
          )}
        </p>
        {status.policy === "Enabled" && optionalControl}
      </section>
    );
  return (
    <section className="panel padded">
      <h2 className="profile-section-title">
        <ShieldCheck size={19} />
        {t("Authenticator app")}
      </h2>
      <p>
        {t(
          status.required
            ? "Two-factor authentication is required for this account."
            : status.policy === "Disabled"
              ? "Staff two-factor authentication is off for this account. Sign in with your password. Your administrator manages role and username requirements."
              : "You can add an authenticator to your staff password sign-in when allowed by your administrator.",
        )}
      </p>
      {status.required ? (
        <p className="muted">
          {t(
            status.enrolled
              ? "Your authenticator is enrolled. Contact your administrator if you lose access."
              : "Complete your authenticator setup at sign-in. Contact your administrator if you need help.",
          )}
        </p>
      ) : status.policy === "Disabled" ? (
        <p className="notice">{t("Authenticator setup is disabled by your GRC administrator.")}</p>
      ) : !status.available ? (
        <p className="notice warning">
          {t("Ask your administrator to enable OTP App authentication in System Settings.")}
        </p>
      ) : (
        status.can_enroll && (
          <>
            <p className="muted">
              {t(
                "After activation, sign in with your staff password and authenticator code. You can cancel setup before activation without changing your sign-in requirements.",
              )}
            </p>
            {!pending ? (
              <Form
                noValidate
                onSubmit={async () => {
                  const result = await begin.execute({ current_password: password });
                  setPassword("");
                  setPending(result);
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
                <Field label="Current password">
                  <input
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
                <Button type="submit">{t("Set up authenticator")}</Button>
              </Form>
            ) : (
              <Form
                noValidate
                onSubmit={async () => {
                  const result = await confirm.execute({ setup_token: pending.setup_token, code });
                  setPending(undefined);
                  setCode("");
                  window.location.assign(result.redirect);
                }}
              >
                <img className="qr-code" src={pending.qr_code} alt={t("Authenticator setup QR code")} />
                <p>{t("Scan this QR code in your authenticator app, then enter its code.")}</p>
                <p className="muted">
                  {t("Setup expires after 10 minutes. Activation signs out all sessions.")}
                </p>
                <Field label="Authenticator code">
                  <input
                    required
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </Field>
                <div className="row-actions">
                  <Button type="submit">{t("Activate authenticator")}</Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setPending(undefined);
                      setCode("");
                    }}
                  >
                    {t("Cancel")}
                  </Button>
                </div>
              </Form>
            )}
          </>
        )
      )}
      {status.method !== "Email" && status.optional_enrolled && optionalControl}
    </section>
  );
}
