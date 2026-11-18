import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, ErrorNotice, Field, Form, PageTitle } from "./components";
import { useLanguage } from "./i18n";
import { useSession } from "./session";
import { useMutation } from "./api";
import type { Assessment } from "./types";
import "./audit-packages.css";

export type AuditPackage = {
  code: string;
  label: string;
  label_ar: string;
  description: string;
  description_ar: string;
  sections: string[];
};
export type ScopeSection = {
  code: string;
  title: string;
  title_ar?: string;
  question_count: number;
  included?: boolean;
};
export type ScopeConfiguration = {
  required_sections: string[];
  packages: AuditPackage[];
  minimum_optional_sections?: number;
  invited_sections?: string[];
  minimum_packages?: string[];
};
export type AssessmentScope = ScopeConfiguration & {
  configuration: string;
  version: number;
  sections: ScopeSection[];
  selected_packages: string[];
  selected_sections: string[];
  confirmed: boolean;
  acknowledgement_required: boolean;
  can_correct: boolean;
  can_change?: boolean;
};

export function PackageChoices({
  configuration,
  sections,
  selected,
  onChange,
  disabled = false,
}: {
  configuration: ScopeConfiguration;
  sections: ScopeSection[];
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled?: boolean;
}) {
  const { t, lang } = useLanguage();
  const included = new Set([
    ...configuration.required_sections,
    ...configuration.packages.filter((p) => selected.includes(p.code)).flatMap((p) => p.sections),
  ]);
  const title = (s: ScopeSection) => (lang === "ar" ? s.title_ar || s.title : s.title);
  const required = sections.filter((s) => configuration.required_sections.includes(s.code));
  const optionalPackages = configuration.packages.filter((p) =>
    p.sections.some((code) => !configuration.required_sections.includes(code)),
  );
  return (
    <div className="audit-package-choices" data-tour="scope-choices">
      {required.length > 0 && (
        <section aria-label={t("Always included")}>
          <strong>{t("Always included")}</strong>
          <div className="audit-package-grid">
            {required.map((s) => (
              <label key={s.code} className="audit-package-card mandatory-section">
                <input type="checkbox" checked disabled />
                <span>
                  <strong>{title(s)}</strong>
                  <small>{t("Mandatory section")}</small>
                  <span className="package-description">
                    {t("Questions")}: {s.question_count}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </section>
      )}
      <div className="audit-package-grid">
        {optionalPackages.map((p) => (
          <label
            key={p.code}
            className={"audit-package-card" + (selected.includes(p.code) ? " selected" : "")}
          >
            <input
              type="checkbox"
              checked={selected.includes(p.code)}
              disabled={disabled || configuration.minimum_packages?.includes(p.code)}
              onChange={(e) =>
                onChange(e.target.checked ? [...selected, p.code] : selected.filter((c) => c !== p.code))
              }
            />
            <span>
              <strong>{lang === "ar" ? p.label_ar || p.label : p.label}</strong>
              {configuration.minimum_packages?.includes(p.code) && (
                <small>{t("Included by your inviting team")}</small>
              )}
              <span className="package-description">
                {lang === "ar" ? p.description_ar || p.description : p.description}
              </span>
              <span className="package-section-breakdown">
                {sections
                  .filter((s) => p.sections.includes(s.code))
                  .map((s) => (
                    <small key={s.code}>
                      {title(s)} · {t("Questions")}: {s.question_count}
                      {configuration.required_sections.includes(s.code) ? ` · ${t("Mandatory section")}` : ""}
                    </small>
                  ))}
              </span>
            </span>
          </label>
        ))}
      </div>
      <section className="scope-breakdown" aria-label={t("Question breakdown")}>
        <strong>{t("Question breakdown")}</strong>
        <ul>
          {sections
            .filter((s) => included.has(s.code))
            .map((s) => (
              <li key={s.code}>
                <span>
                  {title(s)}
                  {configuration.required_sections.includes(s.code) ? ` · ${t("Mandatory section")}` : ""}
                </span>
                <span>
                  {t("Questions")}: {s.question_count}
                </span>
              </li>
            ))}
        </ul>
        <p className="scope-total" aria-live="polite">
          {t("Included sections")}: {included.size} · {t("Questions")}:{" "}
          {sections.filter((s) => included.has(s.code)).reduce((n, s) => n + s.question_count, 0)}
        </p>
      </section>
    </div>
  );
}

export function ScopeSummary({ scope }: { scope: AssessmentScope }) {
  const { lang, t } = useLanguage();
  return (
    <section className="panel padded" data-tour="scope-summary">
      <h2>{t("Assessment scope")}</h2>
      <p>
        {scope.packages
          .filter((p) => scope.selected_packages.includes(p.code))
          .map((p) => (lang === "ar" ? p.label_ar || p.label : p.label))
          .join(" · ") || t("Required sections only")}
      </p>
      <ul>
        {scope.sections.map((s) => (
          <li key={s.code}>
            {lang === "ar" ? s.title_ar || s.title : s.title} — {t(s.included ? "Included" : "Not assessed")}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function AuditScope({
  doc,
  onDone,
  correction = false,
}: {
  doc: Assessment;
  onDone: (doc: Assessment) => void;
  correction?: boolean;
}) {
  const { t } = useLanguage(),
    { session } = useSession();
  const scope = doc.scope!;
  const [selected, setSelected] = useState([
    ...new Set([...(scope.selected_packages || []), ...(scope.minimum_packages || [])]),
  ]);
  const save = useMutation(correction ? "correct_assessment_scope" : "confirm_assessment_scope");
  const acknowledgement = scope.acknowledgement_required && session.kind === "Customer";
  const mayConfirm =
    doc.scope_editable &&
    (((!scope.confirmed || scope.can_change) && session.kind === "Customer") ||
      acknowledgement ||
      (correction && scope.can_correct));
  const optionalSelected = new Set(
    scope.packages
      .filter((p) => selected.includes(p.code))
      .flatMap((p) => p.sections)
      .filter((code) => !scope.required_sections.includes(code)),
  ).size;
  const valid = optionalSelected >= (scope.minimum_optional_sections || 0);
  return (
    <div className="scope-confirmation" data-tour="scope-confirmation">
      {!correction && (
        <PageTitle title="What would you like assessed?" description={doc.entity}>
          <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
        </PageTitle>
      )}
      {!correction && (
        <Link className="back-link" to={session.home + "/assessments"}>
          {t("Back to assessments")}
        </Link>
      )}
      <p>
        {t(
          acknowledgement
            ? "Your administrator corrected the scope. Review and acknowledge it before continuing."
            : correction
              ? "Existing answers are retained. Removed sections do not affect scoring. The customer must acknowledge this correction."
              : "Choose your audit packages. Required sections stay included. Confirm before answering.",
        )}
      </p>
      {!correction && (
        <p className="muted">
          {t(
            "You can return to assessments now. Questions remain unavailable until the required scope is confirmed. Leaving this screen does not save unconfirmed choices.",
          )}
        </p>
      )}
      <Form
        onSubmit={async (values) => {
          const result = await save.execute({
            name: doc.name,
            modified: doc.modified,
            packages: selected,
            reason: values.reason,
          });
          onDone(result);
        }}
      >
        <PackageChoices
          configuration={scope}
          sections={scope.sections}
          selected={selected}
          onChange={setSelected}
          disabled={acknowledgement || !mayConfirm}
        />
        {!valid && (
          <p className="notice" role="status">
            {t("Choose at least one of Risk, Compliance or Governance. Awareness is always included.")}
          </p>
        )}
        {correction && (
          <Field label="Reason for scope correction">
            <textarea name="reason" required maxLength={2000} />
          </Field>
        )}
        {mayConfirm ? (
          <Button type="submit" disabled={!valid} data-tour="confirm-scope">
            {t(
              acknowledgement
                ? "Acknowledge scope"
                : correction
                  ? "Correct scope"
                  : "Confirm scope and continue",
            )}
          </Button>
        ) : (
          <p className="notice">{t("Waiting for the customer to confirm the scope.")}</p>
        )}
      </Form>
      <ErrorNotice error={save.error} />
    </div>
  );
}
