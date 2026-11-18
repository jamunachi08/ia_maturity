import { useId, useState } from "react";
import type { FormEvent } from "react";
import Select from "./Select";
import { Button, ErrorNotice, Field, Loading } from "./components";
import { useData, useMutation } from "./api";
import { useSession } from "./session";
import { useNavigate } from "react-router-dom";
import { useLanguage } from "./i18n";
import "./organization-profile.css";

export type LicenseRow = { license_name: string; valid: string; expiry_date: string };
export type CompanyProfile = {
  organization: string;
  industry_type: string;
  industry_sector: string;
  other_sector: string;
  company_nationality: string;
  cr_number: string;
  ksa_license_type: string;
  ksa_license_na: boolean | number;
  ksa_license_rows: LicenseRow[];
  regulators: { name: string; answer: string }[];
  other_regulator: string;
};
export type ProfileResult = {
  profile: CompanyProfile;
  modified: string;
  can_edit: boolean;
  complete: boolean;
};
/** Screen layout chosen by the GRC App Admin (GRC Screen Layout). Presentation only. */
export type ProfileLayout = {
  name?: string;
  style: "Standard" | "Compact";
  columns: 1 | 2;
  yes_no_display: "Dropdown" | "Buttons";
  show_intro: boolean;
  show_report_lookup: boolean;
  show_saved_assessments: boolean;
  continue_label?: string;
  continue_label_ar?: string;
};
const STANDARD_LAYOUT: ProfileLayout = {
  style: "Standard",
  columns: 2,
  yes_no_display: "Dropdown",
  show_intro: true,
  show_report_lookup: false,
  show_saved_assessments: false,
};
export type Catalog = {
  server_today?: string;
  layout?: ProfileLayout;
  organization_yes_no_display?: "Dropdown" | "Buttons";
  industries: { name: string; sectors: string[] }[];
  nationalities: { name: string; ask_cr: boolean | number; add_misa: boolean | number }[];
  general_regulators: string[];
  industry_regulators: Record<string, string[]>;
  sector_regulators: Record<string, string[]>;
};

function YesNo({
  label,
  value,
  onChange,
  buttons,
  required = false,
  ar,
  row = false,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  buttons: boolean;
  required?: boolean;
  ar: boolean;
  row?: boolean;
  /** Text of the empty option in dropdown mode (the Compact license row shows "Valid?"). */
  placeholder?: string;
}) {
  const id = useId(),
    l = (en: string, arabic: string) => (ar ? arabic : en);
  if (buttons && row)
    // One line per question: the label, then Yes / No pills. Clicking the selected pill clears an optional answer.
    return (
      <div className="company-yes-no-row" role="radiogroup" aria-labelledby={id + "-label"}>
        <span id={id + "-label"}>{label}</span>
        <div className="company-yes-no-options">
          {[
            ["Yes", l("Yes", "نعم")],
            ["No", l("No", "لا")],
          ].map(([option, text]) => (
            <label key={option} className={"company-yes-no-pill" + (value === option ? " selected" : "")}>
              <input
                type="radio"
                name={id}
                value={option}
                checked={value === option}
                required={required}
                onChange={() => onChange(option)}
                onClick={() => !required && value === option && onChange("")}
              />
              <span>{text}</span>
            </label>
          ))}
        </div>
      </div>
    );
  if (!buttons)
    return (
      <Field label={label}>
        <Select required={required} value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="">
            {placeholder || (required ? l("Select", "اختر") : l("Not answered", "لم تتم الإجابة"))}
          </option>
          <option value="Yes">{l("Yes", "نعم")}</option>
          <option value="No">{l("No", "لا")}</option>
        </Select>
      </Field>
    );
  return (
    <fieldset className="company-yes-no">
      <legend>{label}</legend>
      <div className="company-yes-no-options">
        {[
          ...(!required ? [["", l("Not answered", "لم تتم الإجابة")]] : []),
          ["Yes", l("Yes", "نعم")],
          ["No", l("No", "لا")],
        ].map(([option, text]) => (
          <label key={option} className={"company-yes-no-option" + (value === option ? " selected" : "")}>
            <input
              type="radio"
              name={id}
              value={option}
              checked={value === option}
              required={required}
              onChange={() => onChange(option)}
            />
            <span>{text}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function OrganizationProfile({
  entity,
  onDone,
  requiredForAssessment = false,
}: {
  entity: string;
  onDone?: () => void;
  requiredForAssessment?: boolean;
}) {
  const profile = useData<ProfileResult>("organization_profile", { entity }),
    catalog = useData<Catalog>("profile_catalog");
  if (profile.error || catalog.error) return <ErrorNotice error={profile.error || catalog.error} />;
  if (!profile.data || !catalog.data) return <Loading />;
  return (
    <ProfileEditor
      key={entity}
      entity={entity}
      initial={profile.data}
      catalog={catalog.data}
      layout={catalog.data.layout}
      requiredForAssessment={requiredForAssessment}
      onSaved={async () => {
        await profile.mutate();
        onDone?.();
      }}
    />
  );
}

export function ProfileEditor({
  entity,
  initial,
  catalog,
  onSaved,
  requiredForAssessment,
  layout: chosenLayout,
  preview = false,
}: {
  entity: string;
  initial: ProfileResult;
  catalog: Catalog;
  onSaved: () => Promise<void>;
  requiredForAssessment: boolean;
  layout?: ProfileLayout;
  /** Admin layout preview: fully interactive, never saved. */
  preview?: boolean;
}) {
  const layout: ProfileLayout = {
    ...STANDARD_LAYOUT,
    yes_no_display: catalog.organization_yes_no_display || "Dropdown",
    ...chosenLayout,
  };
  const compact = layout.style === "Compact",
    buttons = layout.yes_no_display === "Buttons";
  const { lang } = useLanguage(),
    ar = lang === "ar";
  const l = (en: string, arabic: string) => (ar ? arabic : en);
  const [p, setP] = useState<CompanyProfile>({
    ...initial.profile,
    ksa_license_rows: initial.profile.ksa_license_rows || [],
    regulators: initial.profile.regulators || [],
  });
  const [modified, setModified] = useState(initial.modified),
    [error, setError] = useState<unknown>(),
    [busy, setBusy] = useState(false),
    [saved, setSaved] = useState(false);
  const save = useMutation("save_organization_profile");
  const change = (patch: Partial<CompanyProfile>) => {
    setP((old) => ({ ...old, ...patch }));
    setSaved(false);
    setError(undefined);
  };
  const national = catalog.nationalities.find((n) => n.name === p.company_nationality);
  const sectors = catalog.industries.find((i) => i.name === p.industry_type)?.sectors || [];
  const sectorKey = p.industry_type + "|" + p.industry_sector;
  const specific = Object.prototype.hasOwnProperty.call(catalog.sector_regulators, sectorKey)
    ? catalog.sector_regulators[sectorKey]
    : catalog.industry_regulators[p.industry_type] || [];
  const regulatorNames = [
    ...new Set([
      ...catalog.general_regulators,
      ...specific,
      ...(national?.add_misa ? ["MISA (Ministry of Investment)"] : []),
    ]),
  ];
  const generalAnswers = p.regulators.filter(
    (r) => catalog.general_regulators.includes(r.name) || r.name === "MISA (Ministry of Investment)",
  );
  const field = (name: keyof CompanyProfile) => String(p[name] || "");
  const rowChange = (index: number, patch: Partial<LicenseRow>) =>
    change({ ksa_license_rows: p.ksa_license_rows.map((r, i) => (i === index ? { ...r, ...patch } : r)) });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    setSaved(false);
    try {
      if (!p.organization.trim()) throw new Error(l("Enter the organization name.", "أدخل اسم المنشأة."));
      if (!p.industry_type) throw new Error(l("Select the industry type.", "اختر نوع النشاط."));
      if (!p.industry_sector) throw new Error(l("Select the industry sector.", "اختر قطاع النشاط."));
      if (p.industry_sector === "Other" && !p.other_sector.trim())
        throw new Error(l("Name the sector.", "أدخل اسم القطاع."));
      if (!p.company_nationality)
        throw new Error(l("Select the company nationality.", "اختر جنسية المنشأة."));
      if (national?.ask_cr && p.cr_number && !/^[0-9]{10}$/.test(p.cr_number))
        throw new Error(
          l(
            "The CR number must be 10 digits, or leave it empty.",
            "يجب أن يتكون رقم السجل التجاري من 10 أرقام، أو اتركه فارغاً.",
          ),
        );
      if (!p.ksa_license_na && !p.ksa_license_type.trim())
        throw new Error(
          l("Enter the KSA license type, or tick N/A.", "أدخل نوع الترخيص السعودي، أو حدد لا ينطبق."),
        );
      if (!p.ksa_license_na) {
        const now = new Date(),
          today =
            catalog.server_today ||
            [
              now.getFullYear(),
              String(now.getMonth() + 1).padStart(2, "0"),
              String(now.getDate()).padStart(2, "0"),
            ].join("-");
        for (const row of p.ksa_license_rows) {
          if (!row.license_name && !row.valid && !row.expiry_date) continue;
          if (!row.license_name.trim() || !row.valid || !row.expiry_date)
            throw new Error(
              l(
                "Complete each license row (name, valid, expiry date), or remove it.",
                "أكمل كل صف ترخيص (الاسم، السريان، تاريخ الانتهاء)، أو احذفه.",
              ),
            );
          if (row.valid === "Yes" && row.expiry_date < today)
            throw new Error(
              l(
                "A license with a past expiry date cannot be marked valid.",
                "لا يمكن اعتبار ترخيص منتهي الصلاحية سارياً.",
              ),
            );
        }
      }
      const payload = {
        ...p,
        regulators: regulatorNames.map((name) => ({
          name,
          answer: p.regulators.find((r) => r.name === name)?.answer || "",
        })),
      };
      if (preview) {
        setSaved(true);
        return;
      }
      const result: ProfileResult = await save.execute({ entity, data: payload, modified });
      setP({
        ...result.profile,
        ksa_license_rows: result.profile.ksa_license_rows || [],
        regulators: result.profile.regulators || [],
      });
      setModified(result.modified);
      setSaved(true);
      await onSaved();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  const continueLabel =
    (ar ? layout.continue_label_ar : layout.continue_label) ||
    (compact && requiredForAssessment ? l("Continue to questions", "المتابعة إلى الأسئلة") : "");
  const yesNoProps = { buttons, ar, row: compact };
  return (
    <section
      className={
        "panel padded company-profile" +
        (compact ? " company-profile-compact" : "") +
        (layout.columns === 1 ? " company-profile-one-column" : "")
      }
      dir={ar ? "rtl" : "ltr"}
      data-testid="organization-profile"
      data-layout={layout.name || layout.style}
    >
      <h2>{compact ? l("Organization profile", "ملف المنشأة") : l("Company profile", "ملف المنشأة")}</h2>
      {compact && (
        <p className="muted company-profile-subtitle">
          {l("Not scored. It appears in your report.", "لا يدخل في التقييم، ويظهر في تقريرك.")}
        </p>
      )}
      {layout.show_intro && requiredForAssessment && (
        <p className="notice">
          {l(
            "Complete and save this company profile before choosing GRC sections or answering questions. You can return to assessments without completing it now; the assessment stays blocked until the profile is valid.",
            "أكمل ملف المنشأة واحفظه قبل اختيار أقسام GRC أو الإجابة عن الأسئلة. يمكنك العودة إلى التقييمات الآن؛ ويظل التقييم متوقفاً حتى يصبح الملف صالحاً.",
          )}
        </p>
      )}
      {layout.show_intro && (
        <p className="muted">
          {l(
            "This information is not scored. It is reused for your organization; submitted assessments retain their own profile snapshot.",
            "هذه المعلومات لا تدخل في التقييم. تُستخدم مجدداً للمنشأة، ويحتفظ كل تقييم مقدم بنسخة من بياناته.",
          )}
        </p>
      )}
      {!initial.can_edit && (
        <p className="notice">
          {l(
            "This profile is read-only. Ask an organization administrator to complete or update it.",
            "هذا الملف للقراءة فقط. اطلب من مسؤول المنشأة إكماله أو تحديثه.",
          )}
        </p>
      )}
      <form onSubmit={submit} className="form" noValidate>
        <fieldset disabled={!initial.can_edit || busy}>
          <div className="form-grid">
            <Field label={l("Organization name", "اسم المنشأة")}>
              <input
                name="organization"
                required
                maxLength={140}
                value={field("organization")}
                onChange={(e) => change({ organization: e.target.value })}
              />
            </Field>
            <Field label={l("Industry type", "نوع النشاط")}>
              <Select
                required
                value={p.industry_type || ""}
                onChange={(e) =>
                  change({
                    industry_type: e.target.value,
                    industry_sector: "",
                    other_sector: "",
                    regulators: generalAnswers,
                  })
                }
              >
                <option value="">
                  {compact ? l("Select", "اختر") : l("Select the industry type.", "اختر نوع النشاط.")}
                </option>
                {catalog.industries.map((i) => (
                  <option key={i.name}>{i.name}</option>
                ))}
              </Select>
            </Field>
            <Field label={l("Industry sector", "قطاع النشاط")}>
              <Select
                required
                value={p.industry_sector || ""}
                disabled={!p.industry_type}
                onChange={(e) =>
                  change({ industry_sector: e.target.value, other_sector: "", regulators: generalAnswers })
                }
              >
                <option value="">
                  {compact ? l("Select", "اختر") : l("Select the industry sector.", "اختر قطاع النشاط.")}
                </option>
                {sectors.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </Select>
            </Field>
            {p.industry_sector === "Other" && (
              <Field label={l("Name the sector", "اسم القطاع الآخر")}>
                <input
                  required
                  name="other_sector"
                  value={field("other_sector")}
                  onChange={(e) => change({ other_sector: e.target.value })}
                />
              </Field>
            )}
            <Field label={l("Company nationality", "جنسية المنشأة")}>
              <Select
                required
                value={p.company_nationality || ""}
                onChange={(e) => {
                  const next = catalog.nationalities.find((n) => n.name === e.target.value);
                  change({
                    company_nationality: e.target.value,
                    cr_number: next?.ask_cr ? p.cr_number : "",
                    regulators: p.regulators.filter(
                      (r) => next?.add_misa || r.name !== "MISA (Ministry of Investment)",
                    ),
                  });
                }}
              >
                <option value="">
                  {compact
                    ? l("Select", "اختر")
                    : l("Select the company nationality.", "اختر جنسية المنشأة.")}
                </option>
                {catalog.nationalities.map((n) => (
                  <option key={n.name}>{n.name}</option>
                ))}
              </Select>
            </Field>
            {!!national?.ask_cr && (
              <Field
                label={l("Saudi CR number (optional)", "رقم السجل التجاري السعودي (اختياري)")}
                hint={l("Exactly 10 digits, or leave empty.", "عشرة أرقام بالضبط، أو اتركه فارغاً.")}
              >
                <input
                  name="cr_number"
                  inputMode="numeric"
                  pattern="[0-9]{10}"
                  maxLength={10}
                  value={field("cr_number")}
                  onChange={(e) => change({ cr_number: e.target.value })}
                />
              </Field>
            )}
          </div>
          <h3>{l("KSA licenses", "التراخيص السعودية")}</h3>
          {compact && !p.ksa_license_na && (
            <Field
              label={l(
                "What type of KSA license does the entity have? (e.g., investment license, SAMA license, CST license)",
                "ما نوع الترخيص السعودي لدى المنشأة؟ (مثل: ترخيص استثمار، ترخيص ساما، ترخيص هيئة الاتصالات)",
              )}
            >
              <input
                required
                name="ksa_license_type"
                placeholder={l("Type the license types", "اكتب أنواع التراخيص")}
                value={field("ksa_license_type")}
                onChange={(e) => change({ ksa_license_type: e.target.value })}
              />
            </Field>
          )}
          <label className="company-profile-check">
            <input
              type="checkbox"
              checked={!!p.ksa_license_na}
              onChange={(e) => change({ ksa_license_na: e.target.checked })}
            />
            {compact
              ? l("N/A (no KSA license)", "لا ينطبق (لا يوجد ترخيص سعودي)")
              : l("Not applicable — no KSA license", "لا ينطبق — لا يوجد ترخيص سعودي")}
          </label>
          {!p.ksa_license_na && (
            <>
              {!compact && (
                <Field label={l("KSA license types", "أنواع التراخيص السعودية")}>
                  <input
                    required
                    name="ksa_license_type"
                    value={field("ksa_license_type")}
                    onChange={(e) => change({ ksa_license_type: e.target.value })}
                  />
                </Field>
              )}
              <p className="muted">
                {compact
                  ? l(
                      "Is each license still valid, and what is its expiry date? (optional, one row per license)",
                      "هل كل ترخيص ما زال سارياً، وما تاريخ انتهائه؟ (اختياري، صف لكل ترخيص)",
                    )
                  : l(
                      "License details are optional. Complete every field in any row you add, or remove the row.",
                      "تفاصيل التراخيص اختيارية. أكمل جميع حقول كل صف تضيفه، أو احذف الصف.",
                    )}
              </p>
              {p.ksa_license_rows.map((row, index) => (
                <div className="company-license-row" key={index}>
                  <Field label={l("License name", "اسم الترخيص")}>
                    <input
                      required
                      placeholder={
                        compact
                          ? l("License " + (index + 1) + " name", "اسم الترخيص " + (index + 1))
                          : undefined
                      }
                      value={row.license_name}
                      onChange={(e) => rowChange(index, { license_name: e.target.value })}
                    />
                  </Field>
                  <YesNo
                    label={compact ? l("Valid?", "ساري؟") : l("Still valid?", "هل ما زال سارياً؟")}
                    required
                    value={row.valid}
                    onChange={(value) => rowChange(index, { valid: value })}
                    buttons={buttons && !compact}
                    placeholder={compact ? l("Valid?", "ساري؟") : undefined}
                    ar={ar}
                  />
                  <Field label={l("Expiry date", "تاريخ الانتهاء")}>
                    <input
                      type="date"
                      required
                      value={row.expiry_date}
                      onChange={(e) => rowChange(index, { expiry_date: e.target.value })}
                    />
                  </Field>
                  <Button
                    type="button"
                    variant="ghost"
                    aria-label={l("Remove license row " + (index + 1), "حذف صف الترخيص " + (index + 1))}
                    onClick={() =>
                      change({ ksa_license_rows: p.ksa_license_rows.filter((_, i) => i !== index) })
                    }
                  >
                    {compact ? "×" : l("Remove", "حذف")}
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  change({
                    ksa_license_rows: [
                      ...p.ksa_license_rows,
                      { license_name: "", valid: "", expiry_date: "" },
                    ],
                  })
                }
              >
                {compact ? "+ " + l("Add license", "إضافة ترخيص") : l("Add license", "إضافة ترخيص")}
              </Button>
            </>
          )}
          <h3>
            {compact
              ? l(
                  "Regulators: is the entity regulated by each of these?",
                  "الجهات التنظيمية: هل تخضع المنشأة لتنظيم كل منها؟",
                )
              : l("Regulators", "الجهات التنظيمية")}
          </h3>
          {!compact && (
            <p className="muted">
              {l(
                "Optional: is your organization regulated by each of these? These answers do not change the questions or score.",
                "اختياري: هل تخضع منشأتك لتنظيم هذه الجهات؟ هذه الإجابات لا تغير الأسئلة أو الدرجة.",
              )}
            </p>
          )}
          <div className={compact ? "company-regulators" : "form-grid"}>
            {regulatorNames.map((name) => (
              <YesNo
                key={name}
                label={name}
                value={p.regulators.find((r) => r.name === name)?.answer || ""}
                onChange={(value) =>
                  change({
                    regulators: [...p.regulators.filter((r) => r.name !== name), { name, answer: value }],
                  })
                }
                {...yesNoProps}
              />
            ))}
          </div>
          <Field label={l("Other regulator (optional)", "جهة تنظيمية أخرى (اختياري)")}>
            <input
              name="other_regulator"
              placeholder={compact ? l("Type a name", "اكتب الاسم") : undefined}
              value={field("other_regulator")}
              onChange={(e) => change({ other_regulator: e.target.value })}
            />
          </Field>
          {initial.can_edit && (
            <div className={compact ? "company-profile-continue" : undefined}>
              <Button type="submit" loading={busy}>
                {continueLabel || l("Save profile", "حفظ الملف")}
                {compact && continueLabel ? " ▸" : ""}
              </Button>
            </div>
          )}
        </fieldset>
        <ErrorNotice error={error} />
        {saved && (
          <p role="status" className="form-state success">
            {preview
              ? l("Preview only: nothing was saved.", "معاينة فقط: لم يُحفظ شيء.")
              : l("Profile saved.", "تم حفظ الملف.")}
          </p>
        )}
      </form>
    </section>
  );
}

/** Compact-layout extras under the profile: open a report by its ID and reopen saved assessments.
 *  Both lists come from the server and contain only assessments this user can already open. */
export function ProfileExtras({ entity }: { entity: string }) {
  const catalog = useData<Catalog>("profile_catalog"),
    { lang } = useLanguage(),
    { session } = useSession(),
    navigate = useNavigate(),
    find = useMutation("find_report");
  const layout = catalog.data?.layout;
  const [reportId, setReportId] = useState(""),
    [error, setError] = useState<unknown>();
  if (!layout || (!layout.show_report_lookup && !layout.show_saved_assessments)) return null;
  const ar = lang === "ar",
    l = (en: string, arabic: string) => (ar ? arabic : en);
  const open = (name: string, report = false) =>
    navigate(session.home + "/assessments/" + encodeURIComponent(name) + (report ? "/report" : ""));
  return (
    <div className="profile-extras" dir={ar ? "rtl" : "ltr"}>
      {layout.show_report_lookup && (
        <form
          className="profile-lookup"
          onSubmit={async (event) => {
            event.preventDefault();
            setError(undefined);
            try {
              const result = await find.execute({ report_id: reportId.trim() });
              open(result.name, true);
            } catch (failure) {
              setError(failure);
            }
          }}
        >
          <label htmlFor="report-lookup-id">{l("View report by ID:", "عرض التقرير برقمه:")}</label>
          <input
            id="report-lookup-id"
            value={reportId}
            maxLength={80}
            placeholder={l("e.g. GRC-20261117-...", "مثال: GRC-20261117-...")}
            onChange={(e) => setReportId(e.target.value)}
          />
          <Button type="submit" variant="secondary" disabled={!reportId.trim()} loading={find.loading}>
            {l("Load", "فتح")}
          </Button>
          <ErrorNotice error={error} />
        </form>
      )}
      {layout.show_saved_assessments && <SavedAssessments entity={entity} open={open} ar={ar} />}
    </div>
  );
}
function SavedAssessments({
  entity,
  open,
  ar,
}: {
  entity: string;
  open: (name: string) => void;
  ar: boolean;
}) {
  const saved = useData<SavedAssessment[]>("saved_assessments", { entity }),
    { t } = useLanguage(),
    l = (en: string, arabic: string) => (ar ? arabic : en);
  return (
    <section className="saved-assessments">
      <strong>{l("Saved assessments", "التقييمات المحفوظة")}</strong>
      {saved.error ? (
        <ErrorNotice error={saved.error} />
      ) : !saved.data ? (
        <Loading />
      ) : !saved.data.length ? (
        <p className="muted">{l("No saved assessments yet.", "لا توجد تقييمات محفوظة بعد.")}</p>
      ) : (
        <ul>
          {saved.data.map((row) => (
            <li key={row.name}>
              <code>{row.report_id}</code>
              <span className="muted">
                {row.submitted ? t("Submitted") : `${row.answered || 0}/${row.questions || 0}`}
              </span>
              <Button type="button" variant="ghost" onClick={() => open(row.name)}>
                {l("Load", "فتح")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
type SavedAssessment = {
  name: string;
  report_id: string;
  submitted: boolean;
  answered?: number;
  questions?: number;
};
