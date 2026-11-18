import { getLayout } from "../siteLayout";
import { ExtraCards } from "./SiteBlocks";
import { siteCopy, type SiteContent } from "../siteContent";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  ShieldCheck,
  Languages,
  Save,
  CheckCircle2,
  FileCheck2,
} from "lucide-react";
import { useLanguage } from "../i18n";

export default function LandingHome({
  content,
  previewName,
}: {
  content: SiteContent;
  previewName?: string;
}) {
  const { lang } = useLanguage();
  const layout = getLayout(content);
  const siteUrl = (path: string) =>
    previewName ? path + "?preview=" + encodeURIComponent(previewName) : path;
  const copy = (en: string, arabic: string) => siteCopy(content, lang, en, arabic);
  const example = (key: string, fallback: string) => siteCopy(content, lang, fallback, fallback, key);
  const meter = (key: string, fallback: string) => {
    const n = Number(siteCopy(content, "en", fallback, fallback, key));
    return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : Number(fallback);
  };
  const rawSample = meter("sample.overall", "75");
  const sampleScore = Number.isFinite(rawSample) ? Math.max(0, Math.min(100, rawSample)) : 75;
  const steps = [
    [
      "Register & verify",
      "التسجيل والتحقق",
      "Verify your work email with a single-use code.",
      "تحقق من بريد العمل باستخدام رمز لمرة واحدة.",
    ],
    [
      "Set up your organization",
      "إعداد المنظمة",
      "Add your organization, sector and assessment owner.",
      "أضف المنظمة والقطاع ومسؤول التقييم.",
    ],
    [
      "Answer 20 questions",
      "الإجابة عن 20 سؤالاً",
      "Assess current practice across six sections.",
      "قيّم الممارسات الحالية عبر ستة محاور.",
    ],
    [
      "Save & resume",
      "الحفظ والمتابعة",
      "Save your progress and return when you are ready.",
      "احفظ تقدمك وعد لاستكماله عندما تكون مستعداً.",
    ],
    [
      "Submit for review",
      "الإرسال للمراجعة",
      "Check your answers and supporting evidence.",
      "راجع إجاباتك والأدلة الداعمة قبل الإرسال.",
    ],
    [
      "Assigned team review",
      "مراجعة الفريق المسند",
      "Your assigned team reviews and requests clarification.",
      "يراجع الفريق المسند التقييم ويطلب التوضيحات اللازمة.",
    ],
    [
      "Receive your report",
      "استلام التقرير",
      "Access the approved scorecard and released PDF.",
      "اطلع على بطاقة النتائج المعتمدة والتقرير الصادر.",
    ],
  ];
  return (
    <>
      {!layout.hidden.includes("home.hero") && (
        <section data-site-section="home.hero" className="saudi-hero">
          <div className="hero-copy">
            <span className="eyebrow">
              {copy("CLEAR METHODS. CONFIDENT DECISIONS.", "منهجية واضحة. قرارات بثقة.")}
            </span>
            <h1>
              {copy("Stronger governance.", "حوكمة راسخة.")}
              <br />
              <em>{copy("Measurable maturity.", "نضج قابل للقياس.")}</em>
            </h1>
            <p>
              {copy(
                "From the first question to an approved report: a complete internal audit maturity journey that connects your team, evidence and assigned reviewers.",
                "من أول سؤال إلى تقرير معتمد: رحلة متكاملة لتقييم نضج التدقيق الداخلي، تجمع فريقك والأدلة والمراجعين في مساحة واحدة.",
              )}
            </p>
            <div className="hero-buttons">
              <Link className="button primary" to="/signup">
                {copy("Start your assessment", "ابدأ تقييم منظمتك")}
                <ArrowUpRight size={19} />
              </Link>
              <Link className="button secondary" to={siteUrl("/grc-site/catalogue")}>
                {copy("Explore the assessment", "استكشف التقييم")}
                <ArrowRight size={18} />
              </Link>
            </div>
            <p className="hero-resume">
              {copy("Already started?", "بدأت التقييم بالفعل؟")}{" "}
              <Link to="/login">{copy("Sign in to continue", "سجّل الدخول للمتابعة")}</Link>
            </p>
            <div className="hero-assurances">
              <span>
                <Languages size={17} />
                {copy("Arabic & English", "العربية والإنجليزية")}
              </span>
              <span>
                <Save size={17} />
                {copy("Save your progress", "حفظ التقدم")}
              </span>
              <span>
                <ShieldCheck size={17} />
                {copy("Access by responsibility", "وصول حسب المسؤولية")}
              </span>
            </div>
          </div>
          <div
            className="assessment-preview"
            aria-label={copy("Illustrative scorecard example", "مثال توضيحي لبطاقة النتائج")}
          >
            <div className="preview-top">
              <span>
                {copy("ALPHAX", "ALPHAX")} <b>{copy("GRC", "GRC")}</b>
              </span>
              <span className="sample-label">{copy("ILLUSTRATIVE SAMPLE", "مثال توضيحي")}</span>
            </div>
            <div className="preview-content">
              <span className="eyebrow">{copy("INTERNAL AUDIT MATURITY", "نضج التدقيق الداخلي")}</span>
              <h2>{copy("A clearer picture. A focused next step.", "صورة أوضح. أولويات أدق.")}</h2>
              <div className="preview-score">
                <svg viewBox="0 0 160 160" aria-hidden="true">
                  <circle cx="80" cy="80" r="65" fill="none" stroke="#e8ede6" strokeWidth="10" />
                  <circle
                    cx="80"
                    cy="80"
                    r="65"
                    fill="none"
                    stroke="#17674f"
                    strokeWidth="10"
                    strokeDasharray={sampleScore * 4.09 + " 409"}
                    strokeLinecap="round"
                    transform="rotate(-90 80 80)"
                  />
                </svg>
                <div>
                  <strong data-site-key="sample.overall">
                    {example("sample.overall", "75")}
                    <span>%</span>
                  </strong>
                  <small>{copy("Sample score", "نتيجة نموذجية")}</small>
                </div>
              </div>
              <div className="preview-bars">
                {[
                  [
                    copy("Governance & independence", "الحوكمة والاستقلالية"),
                    example("sample.governance", "80"),
                    meter("sample.governance", "80"),
                    "sample.governance",
                  ],
                  [
                    copy("Audit execution", "تنفيذ التدقيق"),
                    example("sample.execution", "70"),
                    meter("sample.execution", "70"),
                    "sample.execution",
                  ],
                  [
                    copy("Quality & performance", "الجودة والأداء"),
                    example("sample.quality", "75"),
                    meter("sample.quality", "75"),
                    "sample.quality",
                  ],
                ].map(([label, value, width, key]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <b data-site-key={key}>{value}%</b>
                    <div>
                      <i style={{ width: width + "%" }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="preview-status">
                <CheckCircle2 size={18} />
                <span>
                  {copy("Final results follow review and release", "النتائج النهائية بعد المراجعة والإصدار")}
                </span>
              </div>
            </div>
            <div className="preview-foot">
              <FileCheck2 size={18} />
              {copy("Scorecard + PDF report", "بطاقة نتائج + تقرير PDF")}
            </div>
          </div>
        </section>
      )}
      {!layout.hidden.includes("home.facts") && (
        <section
          data-site-section="home.facts"
          className="assessment-facts"
          aria-label={copy("About the assessment", "عن التقييم")}
        >
          {[
            [copy("20", "20"), copy("guided questions", "سؤالاً إرشادياً")],
            [copy("6", "6"), copy("assessment sections", "محاور للتقييم")],
            [copy("2", "2"), copy("working languages", "لغتان للعمل")],
            [copy("One journey", "مسار واحد"), copy("from assessment to report", "من التقييم إلى التقرير")],
          ].map(([n, label]) => (
            <div key={label}>
              <strong>{n}</strong>
              <span>{label}</span>
            </div>
          ))}
        </section>
      )}
      {!layout.hidden.includes("home.journey") && (
        <section data-site-section="home.journey" className="public-content journey-section" id="journey">
          <div className="section-heading">
            <div>
              <span className="eyebrow">{copy("YOUR JOURNEY, STEP BY STEP", "رحلتك خطوة بخطوة")}</span>
              <h2>{copy("Know where to start. See what comes next.", "ابدأ بوضوح. وتقدم بثقة.")}</h2>
            </div>
            <p>
              {copy(
                "Each stage has a clear purpose and owner. Save and return to your work while keeping a traceable review and revision history.",
                "لكل مرحلة هدف ومسؤول واضح. يمكنك حفظ العمل ومتابعته، مع الاحتفاظ بسجل المراجعة والإصدارات.",
              )}
            </p>
          </div>
          <ol className="journey-steps">
            {steps.map(([en, arabic, desc, descAr], i) =>
              layout.removedCards["home.journey"]?.includes(i) ? null : (
                <li key={en} data-site-card={i}>
                  <span className="step-count">{String(i + 1).padStart(2, "0")}</span>
                  <h3>{copy(en, arabic)}</h3>
                  <p>{copy(desc, descAr)}</p>
                </li>
              ),
            )}
            <ExtraCards
              content={content}
              container="home.journey"
              lang={lang}
              journey
              start={steps.length - (layout.removedCards["home.journey"]?.length || 0)}
            />
          </ol>
        </section>
      )}
      {!layout.hidden.includes("home.assurance") && (
        <section data-site-section="home.assurance" className="assurance-band">
          <div>
            <span className="eyebrow">{copy("DESIGNED FOR ACCOUNTABLE WORK", "مصمم للعمل المسؤول")}</span>
            <h2>
              {copy(
                "Evidence in place. Responsibilities made clear.",
                "الأدلة في مكانها. والمسؤوليات واضحة.",
              )}
            </h2>
            <p>
              {copy(
                "Auditors see only their assigned customers. Evidence stays private, and results are reviewed before the final report is released.",
                "يرى المدققون العملاء المسندين إليهم فقط، وتبقى ملفات الأدلة خاصة. تُراجع النتائج قبل إصدار التقرير النهائي.",
              )}
            </p>
            <Link to={siteUrl("/grc-site/about")}>
              {copy("Discover the platform", "تعرّف على المنصة")}
              <ArrowRight size={17} />
            </Link>
          </div>
          <div className="assurance-points">
            {[
              [ShieldCheck, copy("Clear organization permissions", "صلاحيات واضحة لكل منظمة")],
              [CheckCircle2, copy("Traceable review decisions", "مراجعة قابلة للتتبع")],
              [FileCheck2, copy("Preserved versions and approved reports", "إصدارات محفوظة وتقارير معتمدة")],
            ].map(([Icon, label]: any) => (
              <p key={label}>
                <Icon size={25} />
                <span>{label}</span>
              </p>
            ))}
          </div>
        </section>
      )}
      {!layout.hidden.includes("home.readiness") && (
        <section data-site-section="home.readiness" className="public-content readiness">
          <div>
            <span className="eyebrow">{copy("BEFORE YOU BEGIN", "قبل أن تبدأ")}</span>
            <h2>{copy("Bring your team and your supporting evidence.", "اجمع فريقك وأدلتك الأساسية.")}</h2>
            <p>
              {copy(
                "Have your work email, organization details, relevant policies and supporting documents ready. Answer for current practice, not future plans.",
                "جهّز بريد العمل وبيانات المنظمة والسياسات والمستندات ذات الصلة. أجب وفق الممارسات الحالية، وليس الخطط المستقبلية.",
              )}
            </p>
          </div>
          <div>
            <Link className="button primary" to="/signup">
              {copy("Create an account", "إنشاء حساب والبدء")}
              <ArrowUpRight size={18} />
            </Link>
            <Link to={siteUrl("/grc-site/resources")}>
              {copy("Read the preparation guide", "دليل الاستعداد للتقييم")}
            </Link>
          </div>
        </section>
      )}
    </>
  );
}
