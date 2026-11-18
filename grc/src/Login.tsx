import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, ShieldCheck, FileCheck2, Users, Globe2 } from "lucide-react";
import { useLanguage } from "./i18n";
import { SessionGate, useSession } from "./session";
import { Button, Field, ErrorNotice, Loading } from "./components";
import { rawPost } from "./http";

export default function Login() {
  const { lang, setLang, t } = useLanguage(),
    { session, loading: sessionLoading, error: sessionError, withSessionMutation } = useSession();
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const staffLogin = params.get("staff") === "1";
  const resetKey = params.get("key"),
    verificationKey = params.get("verify");
  const [mode, setMode] = useState(
      resetKey
        ? "reset"
        : verificationKey
          ? "verify"
          : window.location.pathname === "/signup" || params.get("signup") === "1"
            ? "email"
            : staffLogin
              ? "password"
              : "email",
    ),
    [signup, setSignup] = useState(window.location.pathname === "/signup" || params.get("signup") === "1"),
    [email, setEmail] = useState("");
  const [pwd, setPwd] = useState(""),
    [name, setName] = useState(""),
    [organization, setOrganization] = useState(""),
    [code, setCode] = useState(""),
    [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<any>(),
    [message, setMessage] = useState(
      params.get("mfa") === "1" ? "Sign in with your password and verification code." : "",
    ),
    [verification, setVerification] = useState<any>(),
    [tmpId, setTmpId] = useState("");
  const [resendAt, setResendAt] = useState(0),
    [expiresAt, setExpiresAt] = useState(0),
    [clock, setClock] = useState(0);
  const [limitedEmail, setLimitedEmail] = useState("");
  const requestPending = useRef(false);
  const waitSeconds =
    limitedEmail === email.trim().toLowerCase() ? Math.max(0, Math.ceil((resendAt - clock) / 1000)) : 0;
  useEffect(() => {
    if (mode !== "code" && mode !== "email") return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [mode]);
  async function requestCode() {
    if (requestPending.current || waitSeconds > 0) return;
    requestPending.current = true;
    try {
      const result = await rawPost("ia_maturity.grc.auth.request_code", {
        email,
        purpose: signup ? "Start" : "Resume",
        full_name: name,
        organization_name: organization,
        language: lang,
        consent: consent ? 1 : 0,
      });
      const now = Date.now();
      setClock(now);
      setLimitedEmail(email.trim().toLowerCase());
      setResendAt(now + (result.message.resend_after_seconds || 60) * 1000);
      setExpiresAt(now + (result.message.expires_in_seconds || 900) * 1000);
      setCode("");
      setMode("code");
      setMessage(
        "If eligible, you will receive a verification email. Enter the code to continue. Staff must use staff sign-in.",
      );
    } catch (error) {
      const seconds = Number((error as { retry_after_seconds?: number })?.retry_after_seconds);
      if (Number.isFinite(seconds) && seconds > 0) {
        const now = Date.now();
        setClock(now);
        setLimitedEmail(email.trim().toLowerCase());
        setResendAt(now + seconds * 1000);
      }
      throw error;
    } finally {
      requestPending.current = false;
    }
  }
  const signedInSignup = signup && !sessionLoading && session.kind !== "Guest" && !verificationKey;
  const navigationStarted = useRef(false);
  const go = useCallback(
    (home: string) => {
      if (navigationStarted.current) return;
      navigationStarted.current = true;
      const next = params.get("next");
      if (next === "/grc/customer/onboarding" && home.startsWith("/grc/customer")) {
        window.location.assign(next);
        return;
      }
      if (["/grc/demo/customer", "/grc/demo/auditor"].includes(next || "")) {
        window.location.assign(next!);
        return;
      }
      const invitation = sessionStorage.getItem("grc-invitation");
      const assessment = sessionStorage.getItem("grc-return-assessment");
      if (assessment && home.startsWith("/grc/")) {
        sessionStorage.removeItem("grc-return-assessment");
        window.location.assign(home + "/assessments/" + encodeURIComponent(assessment));
        return;
      }
      window.location.assign(
        home +
          (invitation && home.startsWith("/grc/customer")
            ? "?invitation=" + encodeURIComponent(invitation)
            : ""),
      );
    },
    [params],
  );
  useEffect(() => {
    if (params.get("assessment")) sessionStorage.setItem("grc-return-assessment", params.get("assessment")!);
    if (params.get("invitation")) sessionStorage.setItem("grc-invitation", params.get("invitation")!);
    if (verificationKey) {
      // Keep the token in component state, not browser history; GET never consumes it.
      window.history.replaceState({}, "", "/login");
    } else if (!sessionLoading && !busy && session.kind !== "Guest" && !resetKey && !signup) {
      go(session.home);
    }
  }, [params, resetKey, verificationKey, signup, sessionLoading, busy, session.kind, session.home, go]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (["code", "mfa"].includes(mode) && !/^\d{6}$/.test(code)) {
      setError(new Error(t("Enter the six-digit verification code to continue.")));
      return;
    }
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      if (mode === "verify") {
        await withSessionMutation(async () => {
          const result = await rawPost("ia_maturity.grc.auth.verify_link", { link_key: verificationKey });
          go(result.message.redirect);
        });
      } else if (mode === "password" || mode === "mfa") {
        await withSessionMutation(async (refreshSession) => {
          const result = await rawPost(
            "login",
            mode === "mfa" ? { usr: email, pwd, otp: code, tmp_id: tmpId } : { usr: email, pwd },
          );
          if (result.verification) {
            setTmpId(result.tmp_id);
            document.cookie = "tmp_id=" + encodeURIComponent(result.tmp_id) + "; path=/; SameSite=Lax";
            setVerification(result.verification);
            setMode("mfa");
          } else if (result.message === "Password Reset") {
            window.location.assign(result.redirect_to);
          } else {
            const signedIn = await refreshSession();
            if (!["ERP", "Customer", "Auditor"].includes(signedIn.kind)) {
              throw new Error(
                t("Unable to load your account. Please sign in again or contact your administrator."),
              );
            }
            // The server returns the version-correct Desk home (/app on v15, /desk on v16).
            go(signedIn.home || "/app/home");
          }
        });
      } else if (mode === "email") {
        await requestCode();
      } else if (mode === "code") {
        await withSessionMutation(async () => {
          const result = await rawPost("ia_maturity.grc.auth.verify_code", { email, code });
          go(result.message.redirect);
        });
      } else if (mode === "forgot") {
        await rawPost("frappe.core.doctype.user.user.reset_password", {
          user: email,
        });
        setMessage("If the account is eligible, recovery instructions have been sent.");
      } else if (mode === "reset") {
        await withSessionMutation(async () => {
          await rawPost("frappe.core.doctype.user.user.update_password", {
            key: resetKey,
            new_password: pwd,
            logout_all_sessions: 1,
          });
          window.location.assign("/login");
        });
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  // Signup must retain the explicit sign-out requirement for existing sessions.
  // The ordinary login form can paint early, but unknown auth is not new-account proof.
  if (signup && (sessionLoading || sessionError))
    return (
      <SessionGate>
        <Loading />
      </SessionGate>
    );
  return (
    <div className="login-layout">
      <aside className="login-story">
        <a className="brand brand-light" href="/">
          <img src="/assets/ia_maturity/images/alphax_logo_white.png" alt="AlphaX" />
          <span>GRC</span>
        </a>
        <div>
          <span className="eyebrow light">GOVERNANCE · RISK · COMPLIANCE</span>
          <h1>{t("Start with a clear picture.")}</h1>
          <p>{t("A dedicated workspace for assessments, evidence, and accountable review.")}</p>
          <ul className="login-benefits">
            <li>
              <ShieldCheck />
              {t("Secure organization access")}
            </li>
            <li>
              <FileCheck2 />
              {t("Guided assessments")}
            </li>
            <li>
              <Users />
              {t("Reviewed, controlled reports")}
            </li>
          </ul>
        </div>
        <footer>
          IRSAA Business Solutions <span>·</span> AlphaX GRC
        </footer>
      </aside>
      <main className="login-panel">
        <div className="login-language">
          <Button variant="ghost" onClick={() => setLang(lang === "en" ? "ar" : "en")}>
            <Globe2 size={16} />
            {lang === "en" ? "العربية" : "English"}
          </Button>
        </div>
        <div className="login-form">
          <span className="eyebrow">ALPHAX GRC</span>
          <h2>
            {t(
              mode === "verify"
                ? "Verify your email"
                : mode === "mfa"
                  ? "Two-factor authentication"
                  : mode === "forgot"
                    ? "Password recovery"
                    : mode === "code"
                      ? "Check your email"
                      : signup
                        ? "Create an account"
                        : "Welcome back",
            )}
          </h2>
          <p className="muted">{t("Assess maturity. Prioritize action.")}</p>
          {!staffLogin && !signup && mode === "email" && (
            <p className="notice">
              {t("Customers sign in with an email code every time. No password is needed.")}
            </p>
          )}
          {signedInSignup && (
            <div className="notice">
              <p>{t("You are already signed in. Sign out before creating another account.")}</p>
              <Button
                type="button"
                onClick={() =>
                  withSessionMutation(async () => {
                    await rawPost("logout", {});
                    window.location.assign("/signup");
                  })
                }
              >
                {t("Sign out to create an account")}
              </Button>
            </div>
          )}
          {!signedInSignup && (
            <form noValidate className="form" onSubmit={submit}>
              <fieldset disabled={busy}>
                {mode === "verify" && (
                  <p>
                    {t(
                      "Confirm your email to continue. The verification link is single-use and expires after 15 minutes.",
                    )}
                  </p>
                )}
                {["password", "email", "forgot"].includes(mode) && (
                  <Field label={mode === "password" ? "Email or username" : "Email"}>
                    <input
                      type={mode === "password" ? "text" : "email"}
                      inputMode={mode === "password" ? "text" : "email"}
                      autoComplete={mode === "password" ? "username" : "email"}
                      autoCapitalize="none"
                      spellCheck={false}
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </Field>
                )}
                {signup && mode === "email" && (
                  <>
                    <Field label="Full name">
                      <input
                        required
                        autoComplete="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                      />
                    </Field>
                    <Field label="Company">
                      <input
                        required
                        autoComplete="organization"
                        maxLength={140}
                        value={organization}
                        onChange={(e) => setOrganization(e.target.value)}
                      />
                    </Field>
                    <p className="muted">
                      {t(
                        "Your verified email will be the organization contact email. Joining an existing organization requires an invitation.",
                      )}
                    </p>
                    <p>
                      {t(
                        "After verifying your email, choose Internal Audit or GRC. If a team invited you, use its invitation link to keep the assigned company and audit type.",
                      )}
                    </p>
                    <label className="check-label">
                      <input
                        type="checkbox"
                        required
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                      />
                      <span>{t("I accept the privacy notice and terms of use.")}</span>
                    </label>
                  </>
                )}
                {["password", "reset"].includes(mode) && (
                  <Field label="Password">
                    <input
                      type="password"
                      required
                      minLength={mode === "reset" ? 10 : undefined}
                      autoComplete={mode === "reset" ? "new-password" : "current-password"}
                      value={pwd}
                      onChange={(e) => setPwd(e.target.value)}
                    />
                  </Field>
                )}
                {mode === "mfa" && verification?.prompt && (
                  <div className="notice">
                    <p>{verification.prompt}</p>
                    {verification.qrcode && (
                      <img
                        className="qr-code"
                        src={"data:image/png;base64," + verification.qrcode}
                        alt="Authenticator setup QR code"
                      />
                    )}
                  </div>
                )}
                {["code", "mfa"].includes(mode) && (
                  <>
                    {mode === "code" && (
                      <p>
                        {t("Enter the code sent to")} <strong dir="ltr">{email}</strong>.{" "}
                        {t(
                          "Check your spam folder if it has not arrived. Use Resend code when the countdown ends.",
                        )}
                      </p>
                    )}
                    <Field
                      label={
                        mode === "mfa" && verification?.method !== "Email"
                          ? "Authenticator code"
                          : "Verification code"
                      }
                    >
                      <input
                        required
                        autoFocus
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        pattern="[0-9]{6}"
                        maxLength={6}
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                      />
                    </Field>
                  </>
                )}
                <Button
                  type="submit"
                  loading={busy}
                  disabled={
                    (mode === "email" && waitSeconds > 0) ||
                    (mode === "code" && expiresAt > 0 && clock >= expiresAt)
                  }
                  className="full-width"
                >
                  {t(
                    mode === "verify"
                      ? "Verify email and continue"
                      : mode === "forgot"
                        ? "Send recovery email"
                        : mode === "email"
                          ? signup
                            ? "Send verification email"
                            : "Send code"
                          : ["code", "mfa"].includes(mode)
                            ? "Verify and continue"
                            : mode === "reset"
                              ? "Save changes"
                              : "Sign in",
                  )}
                  <ArrowRight size={16} />
                </Button>
              </fieldset>
              <ErrorNotice error={error} />
              {message && <div className="notice">{t(message)}</div>}
            </form>
          )}
          {mode === "email" && waitSeconds > 0 && (
            <div className="notice">
              {t("You can request another verification email in")}{" "}
              <span role="timer" dir="ltr">
                {Math.floor(waitSeconds / 60)}:{String(waitSeconds % 60).padStart(2, "0")}
              </span>
            </div>
          )}
          {mode === "code" && (
            <div className="notice" aria-live="polite">
              <p>
                {t("Code expires in")} {Math.max(0, Math.ceil((expiresAt - clock) / 60000))} {t("minutes")}
              </p>
              {expiresAt > 0 && clock >= expiresAt && (
                <p>{t("This code has expired. Request a new code to continue.")}</p>
              )}
              <Button
                variant="secondary"
                disabled={busy || waitSeconds > 0}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  try {
                    await requestCode();
                  } catch (err) {
                    setError(err);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {t("Resend code")}
                {waitSeconds > 0 ? " (" + waitSeconds + "s)" : ""}
              </Button>
            </div>
          )}
          <div className="login-links">
            {staffLogin && ["password", "mfa"].includes(mode) && (
              <button
                onClick={() => {
                  setSignup(false);
                  setMode("forgot");
                  setError(null);
                  setMessage("");
                }}
              >
                {t("Forgot password?")}
              </button>
            )}
            {signup && mode === "email" ? (
              <a href="/login">{t("Already registered? Sign in")}</a>
            ) : !staffLogin && ["password", "email"].includes(mode) ? (
              <button
                onClick={() => {
                  setSignup(!signup);
                  setMode("email");
                }}
              >
                {t(signup ? "Already registered? Sign in" : "Create an account")}
              </button>
            ) : (
              <button
                onClick={() => {
                  setSignup(false);
                  setMode(staffLogin ? "password" : "email");
                  setCode("");
                  setError(null);
                  setMessage("");
                }}
              >
                {t("Back to sign in")}
              </button>
            )}
          </div>
          <p>
            <a href={staffLogin ? "/login" : "/login?staff=1"}>
              {t(staffLogin ? "Customer sign in" : "Staff sign in")}
            </a>
          </p>
          {params.get("staff") === "1" && (
            <p className="notice">
              {t(
                "Internal staff use their assigned Manager, Consultant or Reviewer account. Customer testing requires a separate email address.",
              )}
            </p>
          )}
          <div className="legal-links">
            <a href="/grc-site">{lang === "ar" ? "الرئيسية" : "Home"}</a>
            <span>·</span>
            <a href="/grc-site/privacy">{t("Privacy notice")}</a>
            <span>·</span>
            <a href="/grc-site/terms">{t("Terms of use")}</a>
          </div>
        </div>
        <div className="login-footer">
          <ShieldCheck size={15} /> AlphaX GRC · IRSAA
        </div>
      </main>
    </div>
  );
}
