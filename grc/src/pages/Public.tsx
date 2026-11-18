import { getLayout } from "../siteLayout";
import { ExtraCards, ExtraSections } from "./SiteBlocks";
import { siteCopy, type SiteContent } from "../siteContent";
import Select from "../Select";
import { lazy, useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, ShieldCheck, Globe2, Menu, X } from "lucide-react";
import { useLanguage } from "../i18n";
import { rawPost } from "../http";
import { usePublishedContent } from "../publicContent";
import { Button, Field, Form, Loading } from "../components";
const pages: Record<
  string,
  {
    title: string;
    ar: string;
    intro: string;
    introAr: string;
    items?: [string, string, string, string][];
  }
> = {
  services: {
    title: "Services built around accountable assurance",
    ar: "خدمات تدعم ضماناً مسؤولاً",
    intro:
      "Understand your current position, organize evidence, and move improvements forward with a dedicated review team.",
    introAr: "افهم وضعك الحالي ونظم الأدلة وادفع التحسينات إلى الأمام مع فريق مراجعة متخصص.",
    items: [
      [
        "Maturity assessment",
        "تقييم النضج",
        "A structured questionnaire covering internal audit capability, governance, and performance.",
        "استبيان منظم يغطي قدرات التدقيق الداخلي والحوكمة والأداء.",
      ],
      [
        "Evidence-led review",
        "مراجعة تستند إلى الأدلة",
        "Assigned consultants and reviewers examine submissions, request clarification, and approve results.",
        "يفحص المستشارون والمراجعون المسندون الإجابات ويطلبون التوضيح ويعتمدون النتائج.",
      ],
      [
        "Improvement planning",
        "تخطيط التحسين",
        "Turn findings into actions with owners, deadlines, evidence, and verified closure.",
        "حوّل النتائج إلى إجراءات لها مسؤولون ومواعيد وأدلة وإغلاق معتمد.",
      ],
    ],
  },
  catalogue: {
    title: "Assessment catalogue",
    ar: "دليل التقييمات",
    intro:
      "Start with the internal audit maturity assessment. Published questionnaire versions keep the scoring basis consistent.",
    introAr:
      "ابدأ بتقييم نضج التدقيق الداخلي. تحافظ إصدارات الاستبيانات المنشورة على اتساق أسس احتساب النتائج.",
    items: [
      [
        "Internal audit maturity · 20 questions",
        "نضج التدقيق الداخلي · 20 سؤالاً",
        "A bilingual guided assessment with evidence, review, a maturity scorecard, and an approved report.",
        "تقييم إرشادي ثنائي اللغة مع أدلة ومراجعة وبطاقة نتائج النضج وتقرير معتمد.",
      ],
    ],
  },
  frameworks: {
    title: "Framework and sector context",
    ar: "الأطر والسياق القطاعي",
    intro:
      "The reference questionnaire is based on internal audit maturity concepts and the IIA Global Internal Audit Standards. Framework mappings and bilingual content require owner review before production use.",
    introAr:
      "يستند الاستبيان المرجعي إلى مفاهيم نضج التدقيق الداخلي والمعايير العالمية للتدقيق الداخلي. تتطلب مواءمات الأطر والمحتوى ثنائي اللغة مراجعة المسؤول قبل الاستخدام الإنتاجي.",
    items: [
      [
        "Use the right context",
        "استخدم السياق المناسب",
        "Record your sector and regulators in your organization profile so reviewers understand the operating environment.",
        "سجل القطاع والجهات التنظيمية في ملف المنظمة ليتمكن المراجعون من فهم بيئة العمل.",
      ],
      [
        "Maturity, not certification",
        "النضج وليس الاعتماد",
        "Results describe maturity. They do not establish regulatory compliance or provide certification.",
        "تصف النتائج مستوى النضج ولا تثبت الامتثال التنظيمي ولا تمنح اعتماداً.",
      ],
    ],
  },
  about: {
    title: "Clarity for every stage of assurance",
    ar: "وضوح في كل مرحلة من مراحل الضمان",
    intro:
      "AlphaX GRC by IRSAA Business Solutions brings customers and assigned auditors into one structured assessment process, from verified onboarding to controlled report release.",
    introAr:
      "تجمع منصة ألفا إكس من إرساء لحلول الأعمال العملاء والمدققين المسندين ضمن عملية تقييم منظمة، من التحقق عند الانضمام إلى إصدار التقرير بصورة محكومة.",
  },
  resources: {
    title: "Resources for a prepared assessment",
    ar: "موارد للاستعداد للتقييم",
    intro: "Bring the right people and evidence together before you begin.",
    introAr: "اجمع الأشخاص المناسبين والأدلة اللازمة قبل البدء.",
    items: [
      [
        "Before you start",
        "قبل البدء",
        "Confirm your organization details, nominate an assessment owner, and collect relevant policies and evidence.",
        "تحقق من بيانات المنظمة وحدد مسؤول التقييم واجمع السياسات والأدلة ذات الصلة.",
      ],
      [
        "During assessment",
        "أثناء التقييم",
        "Use the question guidance, save supporting evidence, and answer according to your current practice.",
        "استخدم إرشادات الأسئلة وأرفق الأدلة وأجب وفق الممارسات الحالية.",
      ],
      [
        "After submission",
        "بعد الإرسال",
        "Follow the review timeline, respond to clarification requests, and track agreed improvement actions.",
        "تابع مراحل المراجعة واستجب لطلبات التوضيح وتابع إجراءات التحسين المتفق عليها.",
      ],
    ],
  },
  faq: {
    title: "Frequently asked questions",
    ar: "الأسئلة الشائعة",
    intro: "A clear path from your first sign-in to your released report.",
    introAr: "مسار واضح من تسجيل الدخول الأول إلى إصدار تقريرك.",
    items: [
      [
        "Who can see my organization?",
        "من يمكنه رؤية منظمتي؟",
        "Active organization members, explicitly assigned auditors, and GRC administrators, according to their responsibilities.",
        "الأعضاء النشطون في المنظمة والمدققون المسندون صراحة ومديرو المنصة، وفق مسؤولياتهم.",
      ],
      [
        "When are results available?",
        "متى تتوفر النتائج؟",
        "Depending on the administrator setting, preliminary scores appear after submission or remain hidden until release. Final PDFs are available only after release.",
        "وفق إعداد المدير تظهر النتائج الأولية بعد الإرسال أو تبقى مخفية حتى الإصدار. يتوفر ملف التقرير النهائي بعد الإصدار فقط.",
      ],
      [
        "Can I change a submitted assessment?",
        "هل يمكنني تعديل تقييم مرسل؟",
        "Your reviewer can request clarification. The correction creates a new revision and preserves earlier submissions.",
        "يمكن للمراجع طلب توضيح. ينشئ التصحيح إصداراً جديداً ويحافظ على الإرسالات السابقة.",
      ],
      [
        "Can GRC users access ERP?",
        "هل يستطيع مستخدمو المنصة الوصول إلى تخطيط الموارد؟",
        "GRC customer and staff accounts are restricted to the GRC workspace. Separate accounts are required for ERP access.",
        "تقتصر حسابات العملاء والفريق على مساحة المنصة. يلزم حساب مستقل للوصول إلى نظام تخطيط الموارد.",
      ],
    ],
  },
};
import LandingHome from "./LandingHome";
import { SessionGate, useSession } from "../session";
const copyrightYear = new Date().getFullYear();
const PublicPreview = lazy(() => import("./PublicPreview"));
export default function PublicPage() {
  const { search } = useLocation();
  const preview = new URLSearchParams(search).get("preview");
  return preview ? (
    <SessionGate>
      <PublicPreview name={preview} />
    </SessionGate>
  ) : (
    <PublicSite />
  );
}
export function PublicSite({
  previewContent,
  previewName,
  pageOverride,
}: {
  previewContent?: SiteContent;
  previewName?: string;
  pageOverride?: string;
}) {
  const { lang, setLang } = useLanguage(),
    location = useLocation(),
    [mobile, setMobile] = useState(false),
    [sent, setSent] = useState(false),
    { session } = useSession();
  const { data: publishedContent, error: contentError } = usePublishedContent(!previewContent);
  const siteContent = previewContent || publishedContent;
  const layout = getLayout(siteContent || {});
  const siteUrl = (path: string) =>
    previewName ? path + "?preview=" + encodeURIComponent(previewName) : path;
  const copy = (en: string, arabic: string) => siteCopy(siteContent || {}, lang, en, arabic);
  const key = pageOverride ?? (location.pathname.split("/")[2] || ""),
    page = pages[key],
    ar = lang === "ar";
  const nav = [
    ["", "Home", "الرئيسية"],
    ["services", "Services", "الخدمات"],
    ["catalogue", "Assessments", "التقييمات"],
    ["about", "About", "عن المنصة"],
    ["resources", "Resources", "الموارد"],
    ["contact", "Contact", "تواصل معنا"],
  ];
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  useEffect(() => {
    document.title = page
      ? siteCopy(siteContent || {}, lang, page.title, page.ar)
      : siteCopy(
          siteContent || {},
          lang,
          "AlphaX | Governance, Risk & Compliance",
          "ألفا إكس | الحوكمة والمخاطر والامتثال",
        );
  }, [location.pathname, lang, page, siteContent]);
  if (contentError)
    return (
      <div className="standalone" role="alert">
        {ar
          ? "الموقع غير متاح مؤقتاً. يرجى المحاولة لاحقاً."
          : "The site is temporarily unavailable. Please try again later."}
      </div>
    );
  if (!siteContent) return <Loading />;
  return (
    <div
      className="public-site saudi-site"
      onClick={(event) => {
        if ((event.target as HTMLElement).closest("a")) {
          setMobile(false);
          setSent(false);
        }
      }}
    >
      {previewName && (
        <div className="site-preview-banner" role="status">
          {lang === "ar" ? "معاينة غير منشورة" : "Unpublished preview"} · {previewName}{" "}
          <a href={(session.kind === "Auditor" ? "/grc/auditor" : "/grc/customer") + "/site-content"}>
            {lang === "ar" ? "العودة للمحرر" : "Back to editor"}
          </a>
        </div>
      )}
      <a className="skip-link" href="#public-main">
        {copy("Skip to content", "انتقل إلى المحتوى")}
      </a>
      <div className="public-utility">
        <span>{copy("AlphaX by IRSAA Business Solutions", "ألفا إكس من إرساء لحلول الأعمال")}</span>
        <div>
          <Link to={siteUrl("/grc-site/faq")}>{copy("Help & FAQs", "الأسئلة الشائعة")}</Link>
          <button onClick={() => setLang(ar ? "en" : "ar")} lang={ar ? "en" : "ar"}>
            <Globe2 size={16} />
            {ar ? "English" : "العربية"}
          </button>
        </div>
      </div>
      <header className="public-header">
        <Link
          className="brand"
          to={siteUrl("/grc-site")}
          aria-label={copy("AlphaX home", "ألفا إكس - الرئيسية")}
        >
          <img src="/assets/ia_maturity/images/alphax_logo.png" alt={copy("AlphaX", "AlphaX")} />
          <span>{copy("GRC", "GRC")}</span>
        </Link>
        <button
          className="icon-button public-menu"
          aria-label={copy("Menu", "القائمة")}
          aria-expanded={mobile}
          aria-controls="public-navigation"
          onClick={() => setMobile(!mobile)}
        >
          {mobile ? <X /> : <Menu />}
        </button>
        <nav
          id="public-navigation"
          className={mobile ? "open" : ""}
          aria-label={copy("Main navigation", "التنقل الرئيسي")}
        >
          {nav.map(([path, en, arabic]) => (
            <Link
              key={path}
              aria-current={key === path ? "page" : undefined}
              to={siteUrl("/grc-site" + (path ? "/" + path : ""))}
            >
              {copy(en, arabic)}
            </Link>
          ))}
        </nav>
        <div className="public-header-actions">
          {session.kind === "Guest" ? (
            <>
              <Link className="button ghost" to="/login">
                {copy("Sign in", "تسجيل الدخول")}
              </Link>
              <Link className="button primary" to="/signup">
                {copy("Sign up", "إنشاء حساب")}
                <ArrowRight size={16} />
              </Link>
            </>
          ) : (
            <a className="button primary" href={session.home}>
              {copy("My workspace", "مساحة العمل")}
              <ArrowRight size={16} />
            </a>
          )}
        </div>
      </header>
      <main id="public-main" tabIndex={-1}>
        {!key ? (
          <LandingHome content={siteContent || {}} previewName={previewName} />
        ) : (
          <>
            <div className="page-breadcrumb">
              <Link to={siteUrl("/grc-site")}>{copy("Home", "الرئيسية")}</Link>
              <span>/</span>
              <span>
                {page
                  ? copy(page.title, page.ar)
                  : key === "contact"
                    ? copy("Contact", "تواصل معنا")
                    : key === "privacy"
                      ? copy("Privacy notice", "إشعار الخصوصية")
                      : key === "terms"
                        ? copy("Terms of use", "شروط الاستخدام")
                        : copy("Page", "الصفحة")}
              </span>
            </div>
            {key === "contact" ? (
              <section className="public-content narrow">
                <span className="eyebrow">{copy("LET’S TALK", "نحن هنا لمساعدتك")}</span>
                <h1>{copy("Your next step starts with a conversation.", "خطوتك التالية تبدأ بمحادثة.")}</h1>
                <p>
                  {copy(
                    "Ask about the assessment or request a consultation with the IRSAA team.",
                    "أرسل استفسارك حول التقييم أو اطلب استشارة من فريق إرساء.",
                  )}
                </p>
                <div className="panel padded">
                  {sent ? (
                    <div className="notice" role="status">
                      <ShieldCheck size={25} />
                      <h2>{copy("Your request has been received", "تم استلام طلبك")}</h2>
                      <p>
                        {copy(
                          "Our team will follow up using the contact details you provided.",
                          "سيتابع فريقنا طلبك باستخدام بيانات التواصل التي قدمتها.",
                        )}
                      </p>
                      <Link to={siteUrl("/grc-site")}>{copy("Return home", "العودة للرئيسية")}</Link>
                    </div>
                  ) : (
                    <Form
                      onSubmit={async (values) => {
                        if (previewContent) return;
                        await rawPost("ia_maturity.grc.public.consultation", values);
                        setSent(true);
                      }}
                    >
                      <div className="form-grid">
                        <Field label={copy("Full name", "الاسم الكامل")}>
                          <input name="full_name" autoComplete="name" required />
                        </Field>
                        <Field label={copy("Work email", "البريد الإلكتروني للعمل")}>
                          <input name="email" type="email" autoComplete="email" required />
                        </Field>
                      </div>
                      <Field label={copy("Organization", "المنظمة")}>
                        <input name="organization" autoComplete="organization" />
                      </Field>
                      <Field label={copy("Service", "الخدمة")}>
                        <Select name="service">
                          <option>
                            {copy("Internal audit maturity assessment", "تقييم نضج التدقيق الداخلي")}
                          </option>
                          <option>{copy("GRC consultation", "استشارة الحوكمة والمخاطر والامتثال")}</option>
                        </Select>
                      </Field>
                      <Field label={copy("Message", "الرسالة")}>
                        <textarea name="message" required maxLength={5000} rows={5} />
                      </Field>
                      <label className="check-label">
                        <input type="checkbox" required />
                        <span>
                          {copy(
                            "I accept the privacy notice and terms of use.",
                            "أوافق على إشعار الخصوصية وشروط الاستخدام.",
                          )}{" "}
                          <Link to={siteUrl("/grc-site/privacy")}>
                            {copy("Privacy notice", "إشعار الخصوصية")}
                          </Link>{" "}
                          ·{" "}
                          <Link to={siteUrl("/grc-site/terms")}>
                            {copy("Terms of use", "شروط الاستخدام")}
                          </Link>
                        </span>
                      </label>
                      <Button type="submit">
                        {copy("Submit request", "إرسال الطلب")}
                        <ArrowRight size={16} />
                      </Button>
                    </Form>
                  )}
                </div>
              </section>
            ) : ["privacy", "terms"].includes(key) ? (
              <section className="public-content narrow">
                <h1>
                  {key === "privacy"
                    ? copy("Privacy notice", "إشعار الخصوصية")
                    : copy("Terms of use", "شروط الاستخدام")}
                </h1>
                <p className="legal-copy" data-site-key={"legal." + key}>
                  {siteContent?.["legal." + key]?.[lang] ||
                    copy(
                      "Approved text has not been published. Contact the GRC administrator before production use.",
                      "لم يتم نشر النص المعتمد بعد. يرجى التواصل مع مدير المنصة قبل الاستخدام الإنتاجي.",
                    )}
                </p>
                <Link to={siteUrl("/grc-site/contact")}>{copy("Contact the team", "تواصل مع الفريق")}</Link>
              </section>
            ) : page ? (
              !layout.hidden.includes(key + ".main") && (
                <section className="public-content" data-site-section={key + ".main"}>
                  <span className="eyebrow">{copy("ALPHAX GRC", "ALPHAX GRC")}</span>
                  <h1>{copy(page.title, page.ar)}</h1>
                  <p className="public-intro">{copy(page.intro, page.introAr)}</p>
                  {(page.items || (layout.cards[key + ".main"] || []).length > 0) && (
                    <div className={"public-cards " + (key === "faq" ? "faq-list" : "")}>
                      {(page.items || []).map(([en, arabic, desc, descAr], i) =>
                        layout.removedCards[key + ".main"]?.includes(i) ? null : (
                          <article key={en} data-site-card={i}>
                            <h2>{copy(en, arabic)}</h2>
                            <p>{copy(desc, descAr)}</p>
                          </article>
                        ),
                      )}
                      <ExtraCards content={siteContent || {}} container={key + ".main"} lang={lang} />
                    </div>
                  )}
                  <Link className="button primary" to="/signup">
                    {copy("Start assessment", "ابدأ التقييم")}
                    <ArrowRight size={16} />
                  </Link>
                </section>
              )
            ) : (
              <section className="public-content">
                <h1>{copy("Page not found", "الصفحة غير موجودة")}</h1>
                <Link to={siteUrl("/grc-site")}>{copy("Return home", "العودة للرئيسية")}</Link>
              </section>
            )}
          </>
        )}
        <ExtraSections content={siteContent || {}} page={key || "home"} lang={lang} />
      </main>
      <footer className="public-footer">
        <div>
          <Link className="brand" to={siteUrl("/grc-site")}>
            <img src="/assets/ia_maturity/images/alphax_logo_white.png" alt={copy("AlphaX", "AlphaX")} />
            <span>{copy("GRC", "GRC")}</span>
          </Link>
          <p>{copy("Clarity in assessment. Confidence in decisions.", "وضوح في التقييم. ثقة في القرار.")}</p>
          <span>{copy("IRSAA Business Solutions", "إرساء لحلول الأعمال")}</span>
        </div>
        <div>
          <h2>{copy("Explore", "اكتشف")}</h2>
          {[
            ["catalogue", "Assessments", "التقييمات"],
            ["frameworks", "Frameworks & sectors", "الأطر والقطاعات"],
            ["resources", "Resources", "الموارد"],
            ["faq", "FAQs", "الأسئلة الشائعة"],
          ].map(([k, en, arabic]) => (
            <Link key={k} to={siteUrl("/grc-site/" + k)}>
              {copy(en, arabic)}
            </Link>
          ))}
        </div>
        <div>
          <h2>{copy("Support & contact", "الدعم والتواصل")}</h2>
          <Link to={siteUrl("/grc-site/contact")}>{copy("Contact us", "تواصل معنا")}</Link>
          <Link to={siteUrl("/grc-site/privacy")}>{copy("Privacy notice", "إشعار الخصوصية")}</Link>
          <Link to={siteUrl("/grc-site/terms")}>{copy("Terms of use", "شروط الاستخدام")}</Link>
          {(session.kind === "ERP" || session.is_admin) && (
            <>
              <Link to="/grc/demo/customer">{copy("Customer demo", "عرض تجريبي للعميل")}</Link>
              <Link to="/grc/demo/auditor">{copy("Auditor demo", "عرض تجريبي للمدقق")}</Link>
            </>
          )}
        </div>
        <p className="footer-bottom">
          <span>
            © {copyrightYear} {copy("IRSAA · AlphaX", "IRSAA · AlphaX")}
          </span>
          <span>
            {copy(
              "Maturity results do not establish regulatory compliance or certification.",
              "تقيس النتائج النضج ولا تمنح شهادة امتثال أو اعتماداً تنظيمياً.",
            )}
          </span>
        </p>
      </footer>
    </div>
  );
}
