import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LanguageProvider } from "./i18n";
import { SessionProvider, SessionGate, useSession } from "./session";
import { Loading } from "./components";
import Login from "./Login";
const PortalProvider = lazy(() => import("./PortalProvider"));
const Shell = lazy(() => import("./WorkspaceShell"));
const OnboardingLink = lazy(() => import("./pages/Onboarding").then((m) => ({ default: m.OnboardingLink })));
const OnboardingInvitations = lazy(() =>
  import("./pages/Onboarding").then((m) => ({ default: m.OnboardingInvitations })),
);
const OnboardingDetail = lazy(() =>
  import("./pages/Onboarding").then((m) => ({ default: m.OnboardingDetail })),
);
const CustomerOnboarding = lazy(() =>
  import("./pages/Onboarding").then((m) => ({ default: m.CustomerOnboarding })),
);
const AuditPackages = lazy(() => import("./pages/AuditPackages"));
const OwnershipSettings = lazy(() => import("./pages/Ownership"));
const Guide = lazy(() => import("./Guide"));
const PublicPage = lazy(() => import("./pages/Public"));
const DemoPage = lazy(() => import("./pages/Demo"));
const Preferences = lazy(() => import("./pages/Preferences"));
const Profile = lazy(() => import("./pages/Profile"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AssessmentPage = lazy(() => import("./pages/Assessment"));
const OrganizationsPage = lazy(() =>
  import("./pages/Organizations").then((m) => ({ default: m.OrganizationsPage })),
);
const OrganizationPage = lazy(() =>
  import("./pages/Organizations").then((m) => ({ default: m.OrganizationPage })),
);
const ActionsPage = lazy(() => import("./pages/Operations").then((m) => ({ default: m.ActionsPage })));
const ActivityPage = lazy(() => import("./pages/Operations").then((m) => ({ default: m.ActivityPage })));
const FollowupsPage = lazy(() => import("./pages/Operations").then((m) => ({ default: m.FollowupsPage })));
const ConsultationsPage = lazy(() =>
  import("./pages/Operations").then((m) => ({ default: m.ConsultationsPage })),
);
const AssignmentsPage = lazy(() => import("./pages/Admin").then((m) => ({ default: m.AssignmentsPage })));
const StaffPage = lazy(() => import("./pages/Admin").then((m) => ({ default: m.StaffPage })));
const TemplatesPage = lazy(() => import("./pages/Templates").then((m) => ({ default: m.TemplatesPage })));
const TemplateNewPage = lazy(() => import("./pages/Templates").then((m) => ({ default: m.TemplateNewPage })));
const TemplateEditPage = lazy(() =>
  import("./pages/Templates").then((m) => ({ default: m.TemplateEditPage })),
);
const TemplatePreviewPage = lazy(() =>
  import("./pages/Templates").then((m) => ({ default: m.TemplatePreviewPage })),
);
const Oversight = lazy(() => import("./pages/Oversight"));
const SiteEditor = lazy(() => import("./pages/SiteEditor"));
const AccountSecurity = lazy(() => import("./pages/AccountSecurity"));
const MaturityVisibilityPage = lazy(() => import("./pages/MaturityVisibility"));
const ColorRangesPage = lazy(() => import("./pages/ColorRanges"));
const SettingsPage = lazy(() => import("./pages/Admin").then((m) => ({ default: m.SettingsPage })));
const DepartmentAccess = lazy(() => import("./pages/DepartmentAccess"));
const ReportsPage = lazy(() => import("./pages/Reports").then((m) => ({ default: m.ReportsPage })));
const ReportViewPage = lazy(() => import("./pages/Reports").then((m) => ({ default: m.ReportViewPage })));
const ThemesPage = lazy(() => import("./pages/Configuration").then((m) => ({ default: m.ThemesPage })));
const ScreenLayoutsPage = lazy(() =>
  import("./pages/Configuration").then((m) => ({ default: m.ScreenLayoutsPage })),
);
const AssessmentTypesPage = lazy(() =>
  import("./pages/Configuration").then((m) => ({ default: m.AssessmentTypesPage })),
);
const ReportAccessPage = lazy(() =>
  import("./pages/Configuration").then((m) => ({ default: m.ReportAccessPage })),
);

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { session } = useSession();
  return session.is_admin ? children : <Navigate to={session.home} replace />;
}
function ApplicationRoutes() {
  return (
    <Routes>
      <Route path="/" element={<PublicPage />} />
      <Route
        path="/grc/demo/:kind"
        element={
          <SessionGate>
            <DemoPage />
          </SessionGate>
        }
      />
      <Route
        path="/onboarding"
        element={
          <SessionGate>
            <PortalProvider>
              <OnboardingLink />
            </PortalProvider>
          </SessionGate>
        }
      />
      <Route path="/signup" element={<Login />} />
      <Route path="/grc-site/*" element={<PublicPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/update-password" element={<Login />} />
      <Route
        element={
          <SessionGate>
            <PortalProvider>
              <Shell />
            </PortalProvider>
          </SessionGate>
        }
      >
        <Route path="/grc/customer" element={<Dashboard />} />
        <Route path="/grc/auditor" element={<Dashboard />} />
        {["customer", "auditor"].map((kind) => (
          <Route key={kind} path={"/grc/" + kind}>
            <Route
              path="onboarding"
              element={kind === "auditor" ? <OnboardingInvitations /> : <CustomerOnboarding />}
            />
            <Route path="onboarding/:name" element={<OnboardingDetail />} />
            <Route path="audit-access" element={<DepartmentAccess />} />
            <Route path="audit-packages" element={<AuditPackages />} />
            <Route
              path="onboarding-controls"
              element={
                <AdminOnly>
                  <OwnershipSettings />
                </AdminOnly>
              }
            />
            <Route path="assessments" element={<Dashboard listOnly />} />
            <Route path="assessments/:name" element={<AssessmentPage />} />
            <Route path="assessments/:name/scope" element={<AssessmentPage scopeOnly />} />
            <Route path="assessments/:name/report" element={<ReportViewPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="oversight" element={<Oversight />} />
            <Route path="site-content" element={<SiteEditor />} />
            <Route path="guide" element={<Guide />} />
            <Route path="profile" element={<Profile />} />
            <Route path="preferences" element={<Preferences />} />
            <Route path="actions" element={<ActionsPage />} />
            <Route path="activity" element={<ActivityPage />} />
            <Route path="customers" element={<OrganizationsPage />} />
            <Route path="customers/:name" element={<OrganizationPage />} />
            <Route path="organization" element={<OrganizationsPage />} />
            <Route path="organization/:name" element={<OrganizationPage />} />
            <Route path="scorecards" element={<Dashboard reports />} />
            <Route path="followups" element={<FollowupsPage />} />
            <Route
              path="admin/assignments"
              element={
                <AdminOnly>
                  <AssignmentsPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/staff"
              element={
                <AdminOnly>
                  <StaffPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/templates"
              element={
                <AdminOnly>
                  <TemplatesPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/templates/new"
              element={
                <AdminOnly>
                  <TemplateNewPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/templates/:id/preview"
              element={
                <AdminOnly>
                  <TemplatePreviewPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/templates/:id"
              element={
                <AdminOnly>
                  <TemplateEditPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/security"
              element={
                <AdminOnly>
                  <AccountSecurity />
                </AdminOnly>
              }
            />
            {(
              [
                ["themes", ThemesPage],
                ["layouts", ScreenLayoutsPage],
                ["assessment-types", AssessmentTypesPage],
                ["report-access", ReportAccessPage],
              ] as const
            ).map(([path, Page]) => (
              <Route
                key={path}
                path={"admin/" + path}
                element={
                  <AdminOnly>
                    <Page />
                  </AdminOnly>
                }
              />
            ))}
            <Route path="assessment-display" element={<MaturityVisibilityPage />} />
            <Route path="report-colors" element={<ColorRangesPage />} />
            <Route
              path="admin/settings"
              element={
                <AdminOnly>
                  <SettingsPage />
                </AdminOnly>
              }
            />
            <Route
              path="admin/consultations"
              element={
                <AdminOnly>
                  <ConsultationsPage />
                </AdminOnly>
              }
            />
          </Route>
        ))}
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
function Home() {
  const { session } = useSession();
  return (
    <SessionGate>
      <Navigate to={session.home} replace />
    </SessionGate>
  );
}
export default function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <SessionProvider>
          <Suspense fallback={<Loading />}>
            <ApplicationRoutes />
          </Suspense>
        </SessionProvider>
      </BrowserRouter>
    </LanguageProvider>
  );
}
