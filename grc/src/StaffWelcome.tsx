import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, X } from "lucide-react";
import { useLanguage } from "./i18n";
import { useSession } from "./session";

export default function StaffWelcome({ empty }: { empty: boolean }) {
  const { session } = useSession(),
    { t } = useLanguage(),
    reopen = useRef<HTMLButtonElement>(null);
  const key = "grc-staff-welcome:v1:" + encodeURIComponent(session.user || "");
  const [open, setOpen] = useState(() => {
    try {
      return empty && localStorage.getItem(key) !== "dismissed";
    } catch {
      return empty;
    }
  });
  const departments = [...new Set(session.department_memberships?.map((row) => row.department) || [])];
  const department = departments.length === 1 ? departments[0] : "";
  const managementScope = !!session.can_manage_departments;
  function close() {
    try {
      localStorage.setItem(key, "dismissed");
    } catch {
      /* Dismissal still works for this visit. */
    }
    setOpen(false);
    requestAnimationFrame(() => reopen.current?.focus());
  }
  return (
    <div data-testid="staff-getting-started" style={{ marginBottom: 24 }}>
      {!open ? (
        <button type="button" ref={reopen} className="button secondary" onClick={() => setOpen(true)}>
          <BookOpen size={17} />
          {t("Getting started")}
        </button>
      ) : (
        <section
          className="panel padded"
          aria-label={t("Getting started")}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              close();
            }
          }}
        >
          <div className="row-actions">
            <h2 style={{ margin: 0 }}>
              {t("Getting started")}
              {department && <> · {t(department)}</>}
            </h2>
            <button
              type="button"
              className="icon-button"
              style={{ marginInlineStart: "auto" }}
              aria-label={t("Dismiss getting started")}
              onClick={close}
            >
              <X size={20} />
            </button>
          </div>
          <p>
            {t(
              empty
                ? managementScope
                  ? "No customer organizations are available in your management scope yet."
                  : "Your workspace is ready. No customer organizations are assigned to you yet."
                : managementScope
                  ? "Use this workspace to follow customers and assessments in your management scope."
                  : "Use this workspace to follow your assigned customers and assessments.",
            )}
          </p>
          <p className="muted">
            {t(
              "This guidance is optional. You can close it and reopen Getting started at any time. No organization or assessment selection is required to enter your workspace.",
            )}
          </p>
          <ol>
            {session.can_invite_customers && (
              <li>
                <strong>{t("Invite a customer")}</strong>
                <p>
                  {t(
                    "Open Customer onboarding to invite a customer for your department. The invitation fixes the company and audit type. Track their verification and assessment there.",
                  )}
                </p>
              </li>
            )}
            {session.is_admin ? (
              <li>
                <strong>{t("Assign customer")}</strong>
                <p>
                  {t(
                    "Assign customer organizations and the assessment team so the right consultant and reviewer can see the work.",
                  )}
                </p>
              </li>
            ) : session.can_operations ? (
              <li>
                <strong>{t("Manage customer assignments")}</strong>
                <p>
                  {t(
                    "Open Customer and auditor overview to review the customers you manage and assign staff when your permissions allow it.",
                  )}
                </p>
              </li>
            ) : (
              <li>
                <strong>{t("Find your assigned work")}</strong>
                <p>
                  {t(
                    "Customers and assessments appear after a department manager assigns you. If you are waiting for an assignment, contact your department manager.",
                  )}
                </p>
              </li>
            )}
            <li>
              <strong>{t("Follow the assessment")}</strong>
              <p>
                {t(
                  "The customer answers and submits the assessment. Assigned reviewers then review, approve and release the official report. Customers can see preliminary results immediately after submission.",
                )}
              </p>
            </li>
          </ol>
          <div className="row-actions">
            {session.can_invite_customers && (
              <Link className="button primary" to={session.home + "/onboarding"}>
                {t("Open Customer onboarding")}
              </Link>
            )}
            {session.is_admin ? (
              <Link className="button secondary" to={session.home + "/admin/assignments"}>
                {t("Assign customer")}
              </Link>
            ) : (
              session.can_operations && (
                <Link className="button secondary" to={session.home + "/oversight"}>
                  {t("Manage customer assignments")}
                </Link>
              )
            )}
            {session.can_manage_departments && (
              <Link className="button secondary" to={session.home + "/audit-access"}>
                {t("Manage department access")}
              </Link>
            )}
            <Link className="button ghost" to={session.home + "/guide"}>
              {t("Help & guides")}
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
