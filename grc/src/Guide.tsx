import Select from "./Select";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Map, X } from "lucide-react";
import { useLanguage } from "./i18n";
import { useSession } from "./session";
import content from "./guide-content.json";
import "./guide.css";

type Role = "customer" | "auditor" | "manager" | "admin";
const labels = {
  en: {
    help: "Help & guides",
    tour: "Start guided tour",
    close: "Close",
    next: "Next",
    previous: "Previous",
    finish: "Finish",
    open: "Open this page",
    download: "Download bilingual PDF",
    step: "Step",
    of: "of",
    note: "Features and actions depend on your role, assignment and administrator settings.",
    choose: "Choose a guide",
  },
  ar: {
    help: "المساعدة والأدلة",
    tour: "بدء الجولة الإرشادية",
    close: "إغلاق",
    next: "التالي",
    previous: "السابق",
    finish: "إنهاء",
    open: "فتح هذه الصفحة",
    download: "تنزيل الدليل باللغتين PDF",
    step: "الخطوة",
    of: "من",
    note: "تعتمد الميزات والإجراءات على دورك وإسنادك وإعدادات المدير.",
    choose: "اختر دليلاً",
  },
};
function customerJourneyGuide(types: string[] | undefined, lang: "en" | "ar") {
  const ar = lang === "ar",
    grc = types?.includes("GRC");
  const sections = [
    {
      title: ar ? "تسجيل الدخول" : "Sign in",
      body: ar
        ? "أدخل بريدك الإلكتروني واستخدم رمز التحقق المرسل إليك في كل مرة. لا تحتاج إلى كلمة مرور. تحدد الدعوة المنشأة ونوع التقييم ولا يمكنك تغييرهما."
        : "Enter your email and use the emailed verification code every time. No password is needed. An invitation fixes your company and audit type.",
      path: "",
    },
    {
      title: ar ? "بدء التقييم" : "Start your assessment",
      body: ar
        ? "اختر ابدأ التقييم وحدد المنشأة إذا كنت تنتمي إلى أكثر من منشأة. يظهر نوع التقييم المصرح به فقط."
        : "Choose Start assessment and select your company if you belong to more than one. Only your authorized audit type is available.",
      path: "/assessments",
    },
    ...(grc
      ? [
          {
            title: ar ? "ملف المنشأة والأقسام" : "Company profile and sections",
            body: ar
              ? "أكمل ملف المنشأة الإلزامي. يحفظ للاستخدام لاحقاً. قسم الوعي مشمول دائماً؛ اختر قسماً آخر على الأقل. لا يمكنك إزالة أقسام الدعوة. يتاح تغيير الأقسام حتى حفظ أول إجابة."
              : "Complete the mandatory company profile; it is saved for reuse. Awareness is always included; choose at least one other section. Invitation sections cannot be removed. Sections can change until your first answer is saved.",
            path: "/assessments",
          },
        ]
      : []),
    {
      title: ar ? "الإجابة والحفظ" : "Answer and save",
      body: ar
        ? "أجب عن كل سؤال ظاهر. اختر غير منطبق عند إتاحته. تحفظ الإجابات أثناء العمل ويمكنك العودة لاحقاً. لا يمكن الإرسال مع إجابات ناقصة."
        : "Answer every shown question. Choose Not applicable where offered. Answers save as you work and you can return later. Submission requires every shown question to be answered.",
      path: "/assessments",
    },
    {
      title: ar ? "النتائج والتقرير" : "Results and report",
      body: ar
        ? "تظهر النتائج بعد الإرسال وتغطي الأقسام المختارة فقط. نزّل ملف PDF أو أرسله كمرفق إلى بريدك المسجل. تظل النتائج أولية إلى أن يراجع الفريق التقييم ويصدر التقرير المعتمد."
        : "After submission, results cover the selected sections only. Download the PDF or email it as an attachment to your registered address. Results remain preliminary until staff review and release the approved report.",
      path: "/assessments",
    },
    {
      title: ar ? "صلاحيات إضافية" : "Additional access",
      body: ar
        ? "لطلب نوع تقييم آخر افتح صلاحية التقييم. لا تتغير الصلاحية حتى تكتمل موافقات مديري الأقسام."
        : "To request another audit type, open Audit access. Access remains unchanged until department managers complete approval.",
      path: "/audit-access",
    },
  ];
  return {
    title: ar ? "دليل العميل" : "Customer guide",
    intro: ar ? "دليل رحلتك من التحقق إلى التقرير." : "Your journey from verification to report.",
    sections,
  };
}
export { default as GuideLink } from "./GuideLink";
export default function Guide() {
  const { lang } = useLanguage(),
    { session, activeOrganization } = useSession(),
    navigate = useNavigate();
  const manager =
    session.can_manage_departments ||
    session.staff_roles?.some((r) => ["GRC Manager", "IA Maturity Manager"].includes(r));
  const defaultRole: Role = session.is_admin
    ? "admin"
    : manager
      ? "manager"
      : session.kind === "Auditor"
        ? "auditor"
        : "customer";
  const allowedRoles: Role[] = session.is_admin
    ? ["admin", "manager", "auditor", "customer"]
    : manager
      ? ["manager", "auditor"]
      : [defaultRole];
  const canOpen = (path: string) =>
    !(path.startsWith("/admin") && !session.is_admin) &&
    !(path === "/audit-packages" && !session.can_configure_scope) &&
    !(path === "/onboarding-controls" && !session.is_admin) &&
    !(path === "/onboarding" && session.kind === "Auditor" && !session.can_invite_customers) &&
    !(path === "/oversight" && !session.can_operations) &&
    !(path === "/site-content" && !session.can_site_content) &&
    !(path === "/organization" && session.kind === "Auditor") &&
    !(path === "/customers" && session.kind !== "Auditor");
  const [role, setRole] = useState<Role>(defaultRole),
    [step, setStep] = useState<number | null>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const launchRef = useRef<HTMLButtonElement>(null);
  const selectedTypes =
    session.audit_type_access?.[activeOrganization || session.organizations?.[0]?.name || ""] ||
    session.allowed_assessment_types;
  const base = session.kind === "Auditor" ? "/grc/auditor" : "/grc/customer",
    guide = session.kind === "Customer" ? customerJourneyGuide(selectedTypes, lang) : content[role][lang],
    l = labels[lang];
  const staffTypes = [...new Set(session.department_memberships?.map((d) => d.department) || [])];
  useEffect(() => {
    if (step === null) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setStep(null);
        launchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step]);
  const close = () => {
    setStep(null);
    launchRef.current?.focus();
  };
  return (
    <div className="guide-page">
      <header className="guide-hero">
        <div>
          <span className="guide-kicker">
            {session.kind === "Customer"
              ? "ALPHAX"
              : staffTypes.length === 1 && staffTypes[0] === "Internal Audit"
                ? "ALPHAX INTERNAL AUDIT"
                : "ALPHAX GRC"}
          </span>
          <h1>{l.help}</h1>
          <p>{l.note}</p>
        </div>
        <button ref={launchRef} className="button" onClick={() => setStep(0)}>
          <Map size={17} />
          {l.tour}
        </button>
      </header>
      {allowedRoles.length > 1 && (
        <div className="guide-picker">
          <label htmlFor="guide-role">{l.choose}</label>
          <Select id="guide-role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {allowedRoles.map((r) => (
              <option key={r} value={r}>
                {content[r][lang].title}
              </option>
            ))}
          </Select>
        </div>
      )}
      <div className="guide-intro">
        <div>
          <h2>{guide.title}</h2>
          <p>{guide.intro}</p>
        </div>
        {session.kind !== "Customer" && (
          <a className="button secondary" href={"/assets/ia_maturity/guides/" + role + "-guide.pdf"} download>
            {l.download}
          </a>
        )}
      </div>
      <ol className="guide-sections">
        {guide.sections.map((s, i) => (
          <li key={i}>
            <span className="guide-number">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
              {canOpen(s.path) && <Link to={base + s.path}>{l.open} →</Link>}
            </div>
          </li>
        ))}
      </ol>
      {step !== null && (
        <div className="guide-overlay" onClick={close}>
          <section
            ref={dialogRef}
            className="guide-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="tour-title"
            onKeyDown={(e) => {
              if (e.key !== "Tab") return;
              const nodes = Array.from(
                dialogRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled),a[href]") || [],
              );
              const first = nodes[0],
                last = nodes[nodes.length - 1];
              if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last?.focus();
              } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first?.focus();
              }
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="guide-dialog-top">
              <span>
                {l.step} {step + 1} {l.of} {guide.sections.length}
              </span>
              <button ref={closeRef} className="icon-button" onClick={close} aria-label={l.close}>
                <X size={20} />
              </button>
            </div>
            <div className="guide-progress">
              <span style={{ width: ((step + 1) / guide.sections.length) * 100 + "%" }} />
            </div>
            <h2 id="tour-title">{guide.sections[step].title}</h2>
            <p>{guide.sections[step].body}</p>
            <div className="guide-dialog-actions">
              <button className="button secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>
                {l.previous}
              </button>
              {canOpen(guide.sections[step].path) && (
                <button
                  className="button secondary"
                  onClick={() => {
                    navigate(base + guide.sections[step].path);
                    close();
                  }}
                >
                  {l.open}
                </button>
              )}
              <button
                className="button"
                onClick={() => (step + 1 === guide.sections.length ? close() : setStep(step + 1))}
              >
                {step + 1 === guide.sections.length ? l.finish : l.next}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
