import { useAssessmentTypes } from "./assessmentTypes";
import { Suspense, useEffect, useState } from "react";
import { Navigate, NavLink, Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  BarChart3,
  Building2,
  CheckSquare,
  History,
  Users,
  UserRoundCheck,
  Settings2,
  FileStack,
  MessageSquare,
  CalendarClock,
  LogOut,
  Menu,
  X,
  Globe2,
  ShieldCheck,
  Shapes,
  Palette,
  LayoutTemplate,
  KeyRound,
} from "lucide-react";
import { useLanguage } from "./i18n";
import { useSession } from "./session";
import { Button, ErrorNotice, Loading } from "./components";
import { rawPost } from "./http";
import GuideLink from "./GuideLink";
import PageTour from "./PageTour";
import Select from "./Select";

export default function WorkspaceShell() {
  const assessmentTypes = useAssessmentTypes();
  const { session, refresh, withSessionMutation, activeOrganization, setOrganization } = useSession(),
    navigate = useNavigate(),
    { lang, setLang, t } = useLanguage(),
    location = useLocation();
  const [approval, setApproval] = useState(""),
    [mobile, setMobile] = useState(false),
    [inviteError, setInviteError] = useState<any>();
  const [smallScreen, setSmallScreen] = useState(() => window.matchMedia("(max-width:850px)").matches);
  const auditor = session.kind === "Auditor",
    base = auditor ? "/grc/auditor" : "/grc/customer";
  const selectedTypes =
    session.audit_type_access?.[activeOrganization || session.organizations?.[0]?.name || ""] ||
    session.allowed_assessment_types;
  const staffTypes = [...new Set(session.department_memberships?.map((d) => d.department) || [])];
  const workspaceType =
    auditor && staffTypes.length === 1
      ? staffTypes[0]
      : !auditor && selectedTypes?.length === 1
        ? selectedTypes[0]
        : "GRC";
  useEffect(() => {
    document.title = "AlphaX " + workspaceType;
  }, [workspaceType]);

  useEffect(() => {
    const queued = (e: Event) => setApproval((e as CustomEvent<string>).detail);
    window.addEventListener("grc-approval-queued", queued);
    return () => window.removeEventListener("grc-approval-queued", queued);
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(max-width:850px)"),
      changed = () => setSmallScreen(media.matches);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("invitation");
    if (token && session.kind === "Customer") {
      window.history.replaceState({}, "", window.location.pathname);
      rawPost("ia_maturity.grc.api.accept_invitation", { token })
        .then(() => {
          sessionStorage.removeItem("grc-invitation");
          refresh();
        })
        .catch(setInviteError);
    }
  }, [session.kind, refresh]);
  if (session.kind === "Guest") return <Navigate to="/login" replace />;
  if (session.kind === "ERP") {
    window.location.assign(session.home);
    return null;
  }
  if (location.pathname.startsWith("/grc/auditor") && !auditor) return <Navigate to={session.home} replace />;
  if (location.pathname.startsWith("/grc/customer") && auditor) return <Navigate to={session.home} replace />;
  const links: [string, string, typeof LayoutDashboard][] = [
    ["", "Overview", LayoutDashboard],
    ["/assessments", "Assessments", ClipboardList],
    ...((auditor
      ? [
          [
            "/customers",
            session.can_manage_departments ? "Available customers" : "Assigned customers",
            Building2,
          ],
          ["/followups", "Follow-ups", CalendarClock],
          ...(session.can_view_reports ? [["/reports", "Reports", BarChart3]] : []),
        ]
      : [
          ["/scorecards", "Scorecards", BarChart3],
          ["/organization", "Organization", Building2],
        ]) as [string, string, typeof LayoutDashboard][]),
    ...(session.can_operations
      ? [["/oversight", "Customer and auditor overview", Users] as [string, string, typeof LayoutDashboard]]
      : []),
    ["/actions", "Actions", CheckSquare],
    ["/activity", auditor ? "Activity" : "Assessment dates", History],
    ["/preferences", "Notifications", Settings2],
    ...(session.can_site_content
      ? [["/site-content", "Website content", FileStack] as [string, string, typeof LayoutDashboard]]
      : []),
  ];
  if (session.can_invite_customers || !auditor) links.push(["/onboarding", "Customer onboarding", Users]);
  if (session.can_configure_scope) links.push(["/audit-packages", "Audit packages", FileStack]);
  links.push(["/audit-access", "Audit access", ShieldCheck]);
  if (session.is_admin) links.push(["/onboarding-controls", "Onboarding controls", Settings2]);
  if (auditor && (session.is_admin || session.staff_roles?.includes("GRC Manager")))
    links.push(
      ["/assessment-display", "Assessment display", Settings2],
      ["/report-colors", "Report color ranges", Settings2],
    );
  const admins = [
    ["assignments", "Customer assignments", UserRoundCheck],
    ["templates", "Questionnaire templates", FileStack],
    ["staff", "Staff", Users],
    ["security", "Account security", ShieldCheck],
    ["settings", "Settings", Settings2],
    ["assessment-types", "Assessment types", Shapes],
    ["themes", "Themes", Palette],
    ["layouts", "Screen layouts", LayoutTemplate],
    ["report-access", "Report access", KeyRound],
    ["consultations", "Consultation requests", MessageSquare],
  ] as const;
  return (
    <div className="app-shell">
      {mobile && (
        <button className="sidebar-scrim" onClick={() => setMobile(false)} aria-label={t("Close menu")} />
      )}
      <aside
        className={"sidebar " + (mobile ? "mobile-open" : "")}
        inert={smallScreen && !mobile}
        aria-hidden={smallScreen && !mobile ? true : undefined}
      >
        <a className="brand" href={base}>
          <img src="/assets/ia_maturity/images/alphax_logo.png" alt="AlphaX" />
          <span>{t(workspaceType)}</span>
        </a>
        <div className="workspace-label">
          <span className="workspace-icon">
            <ShieldCheck size={18} />
          </span>
          <div>
            <strong>{t(auditor ? "Auditor workspace" : "Customer workspace")}</strong>
            <small>
              {session.is_admin
                ? t("GRC administration")
                : workspaceType === "Internal Audit"
                  ? t("Internal Audit")
                  : workspaceType === "GRC"
                    ? t("Governance & assurance")
                    : assessmentTypes.label(workspaceType)}
            </small>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {links.map(([route, label, Icon]) => (
            <NavLink onClick={() => setMobile(false)} key={route} to={base + route} end={!route}>
              <Icon size={18} />
              <span>{t(label)}</span>
            </NavLink>
          ))}
          {session.is_admin && (
            <>
              <div className="nav-section">{t("Administration")}</div>
              {admins.map(([route, label, Icon]) => (
                <NavLink onClick={() => setMobile(false)} key={route} to={base + "/admin/" + route}>
                  <Icon size={18} />
                  <span>{t(label)}</span>
                </NavLink>
              ))}
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <Link
            to={base + "/profile"}
            className="profile-link"
            aria-label={t("My profile")}
            onClick={() => setMobile(false)}
          >
            <span className="avatar">{session.full_name?.slice(0, 1) || "G"}</span>
            <span className="profile-link-text">
              <strong>{session.full_name}</strong>
              <small>{session.user}</small>
            </span>
          </Link>
          <button
            className="icon-button"
            aria-label={t("Sign out")}
            onClick={() =>
              withSessionMutation(async () => {
                await rawPost("logout", {});
                window.location.assign("/login");
              })
            }
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-toggle"
              onClick={() => setMobile(!mobile)}
              aria-label={t("Menu")}
            >
              {mobile ? <X /> : <Menu />}
            </button>
            <span className="topbar-title">
              {t(workspaceType)} <span>/</span> {t(auditor ? "Auditor workspace" : "Customer workspace")}
            </span>
          </div>
          <div className="topbar-controls">
            {session.organizations && session.organizations.length > 0 && (
              <Select
                aria-label={t("Switch organization")}
                value={activeOrganization}
                onChange={(e) => {
                  setOrganization(e.target.value);
                  navigate(base);
                }}
              >
                <option value="">{t("All organizations")}</option>
                {session.organizations.map((o) => (
                  <option key={o.name} value={o.name}>
                    {o.entity_name}
                  </option>
                ))}
              </Select>
            )}
            {<GuideLink />}
            <PageTour />
            <Button variant="ghost" onClick={() => setLang(lang === "en" ? "ar" : "en")}>
              <Globe2 size={16} />
              {lang === "en" ? "العربية" : "English"}
            </Button>
          </div>
        </header>
        <main className="main-content">
          {!!session.onboarding_alerts && (
            <div className="notice">
              <Link to={base + "/onboarding"}>
                {t("Onboarding updates")}: {session.onboarding_alerts}
              </Link>
            </div>
          )}
          <ErrorNotice error={inviteError} />
          {approval && (
            <div className="notice" role="status">
              <span>
                {t("Submitted for approval. Access changes after final approval.")} · {approval}
              </span>
              {session.can_operations && <Link to={base + "/oversight"}>{t("Approvals")}</Link>}
              <Button variant="ghost" onClick={() => setApproval("")}>
                {t("Close")}
              </Button>
            </div>
          )}
          <Suspense fallback={<Loading />}>
            <Outlet key={activeOrganization} />
          </Suspense>
        </main>
        <footer className="workspace-footer">
          <span>AlphaX {t(workspaceType)} · IRSAA Business Solutions</span>
          <span>
            <ShieldCheck size={13} /> {t("Secure organization access")}
          </span>
        </footer>
      </div>
    </div>
  );
}
