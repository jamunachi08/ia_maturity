import { useAssessmentTypes } from "../assessmentTypes";
import { useState } from "react";
import "../template-controls.css";
import { Link, Navigate } from "react-router-dom";
import { useData, useMutation } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { Button, Empty, ErrorNotice, Field, Loading, PageTitle, Status } from "../components";
import Select from "../Select";
import { PackageChoices } from "../AuditScope";
import { withIndividualSectionChoices } from "../auditPackageConfiguration";
import type { AuditPackage, ScopeConfiguration, ScopeSection } from "../AuditScope";

type ConfigRow = {
  name: string;
  version: number;
  published: number;
  configuration: ScopeConfiguration;
  modified: string;
};
type Data = {
  templates: {
    name: string;
    template_name: string;
    version: number;
    assessment_type: string;
    modified: string;
    is_active: number;
    grc_is_default: number;
  }[];
  sections?: ScopeSection[];
  configurations: ConfigRow[];
};
const blank: ScopeConfiguration = { required_sections: [], packages: [] };
export default function AuditPackages() {
  const { session } = useSession(),
    { t, lang } = useLanguage();
  const [template, setTemplate] = useState("");
  const { data, error, mutate } = useData<Data>("scope_configurations", { template: template || undefined });
  if (!session.can_configure_scope) return <Navigate to={session.home} replace />;
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const selected = data.templates.find((row) => row.name === template);
  return (
    <div className="audit-packages-page">
      <PageTitle title="Audit packages" description="Configure what customers can choose before answering.">
        <Link to={session.home + "/guide"}>{t("Help & guides")}</Link>
      </PageTitle>
      <section className="panel padded template-picker">
        <p>
          {t(
            "This configuration is optional. Existing published defaults can be used without changes. Select a questionnaire version to manage choices for future assessments, or return to your workspace.",
          )}
        </p>
        <Link to={session.home}>{t("Return to workspace")}</Link>
        {data.templates.length ? (
          <Field label="Questionnaire version">
            <Select value={template} onChange={(e) => setTemplate(e.target.value)}>
              <option value="">{t("Select questionnaire")}</option>
              {data.templates.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.template_name} · v{a.version} · {t(a.is_active ? "Active" : "Disabled")}
                  {a.grc_is_default ? ` · ${t("Default")}` : ""}
                </option>
              ))}
            </Select>
          </Field>
        ) : (
          <Empty
            title="No questionnaire versions available"
            text="Ask an app administrator to prepare a questionnaire. You do not need to select an empty value."
          />
        )}
      </section>
      {template && !selected && (
        <p className="notice">
          {t(
            "This questionnaire is no longer available. Choose another version or return to your workspace.",
          )}
        </p>
      )}
      {selected && <TemplateType key={template + selected.modified} row={selected} reload={() => mutate()} />}
      {selected && data.sections && (
        <Editor key={template} template={template} data={data} reload={() => mutate()} lang={lang} />
      )}
    </div>
  );
}
function Editor({
  template,
  data,
  reload,
  lang,
}: {
  template: string;
  data: Data;
  reload: () => Promise<unknown>;
  lang: string;
}) {
  const { t } = useLanguage();
  const current = data.configurations[0];
  const [config, setConfig] = useState<ScopeConfiguration>(
    current?.configuration || { ...blank, required_sections: data.sections!.map((s) => s.code) },
  );
  const [name, setName] = useState(current && !current.published ? current.name : ""),
    [modified, setModified] = useState(current?.modified || "");
  const [error, setError] = useState<unknown>(),
    [busy, setBusy] = useState(false),
    [savedConfig, setSavedConfig] = useState<ScopeConfiguration>(),
    [preview, setPreview] = useState<string[]>([]);
  const save = useMutation("save_scope_configuration"),
    publish = useMutation("publish_scope_configuration");
  const offeredConfig = withIndividualSectionChoices(config, data.sections!);
  function packageChange(index: number, key: keyof AuditPackage, value: string | string[]) {
    setConfig((c) => ({
      ...c,
      packages: c.packages.map((p, i) => (i === index ? { ...p, [key]: value } : p)),
    }));
  }
  async function persist(publishNow = false) {
    setBusy(true);
    setError(null);
    try {
      const result = await save.execute({
        template,
        configuration: offeredConfig,
        name: name || undefined,
        modified: modified || undefined,
      });
      setName(result.name);
      setModified(result.modified);
      if (publishNow) {
        await publish.execute({ name: result.name, modified: result.modified });
        setName("");
      }
      await reload();
      setSavedConfig(config);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="scope-config-editor">
      <section className="panel padded" data-tour="scope-version">
        <h2>{t("Configuration version")}</h2>
        <p>
          {current ? `v${current.version}` : t("New configuration")}{" "}
          {current && <Status value={current.published ? "Published" : "Draft"} />}
        </p>
        <p>
          {t(
            "Publishing creates choices for future assessments. Existing assessments keep their saved version.",
          )}
        </p>
      </section>
      <fieldset disabled={busy} className="scope-config-fields">
        <section className="panel padded" data-tour="required-sections">
          <h2>{t("Always included sections")}</h2>
          <p>
            {t(
              data.templates.find((row) => row.name === template)?.assessment_type === "GRC"
                ? "For GRC, keep Awareness mandatory and the other sections optional. Customers must include at least one of Risk, Compliance or Governance."
                : "You may leave all sections optional. Sections outside your custom packages are offered individually.",
            )}
          </p>
          <div className="section-checks">
            {data.sections!.map((s) => (
              <label key={s.code}>
                <input
                  type="checkbox"
                  checked={config.required_sections.includes(s.code)}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      required_sections: e.target.checked
                        ? [...c.required_sections, s.code]
                        : c.required_sections.filter((x) => x !== s.code),
                    }))
                  }
                />
                {lang === "ar" ? s.title_ar || s.title : s.title} <small>({s.question_count})</small>
              </label>
            ))}
          </div>
        </section>
        <section className="panel padded" data-tour="package-editor">
          <h2>{t("Optional audit packages")}</h2>
          <p>
            {t(
              "Customers can select individual optional sections. Add packages to group sections into named choices.",
            )}
          </p>
          {config.packages.map((p, i) => (
            <div className="package-editor" key={i}>
              <div className="form-grid">
                <Field label="Package code">
                  <input
                    value={p.code}
                    maxLength={60}
                    onChange={(e) => packageChange(i, "code", e.target.value)}
                  />
                </Field>
                <Field label="Package label">
                  <input
                    value={p.label}
                    maxLength={140}
                    onChange={(e) => packageChange(i, "label", e.target.value)}
                  />
                </Field>
                <Field label="Package label in Arabic">
                  <input
                    dir="rtl"
                    value={p.label_ar}
                    maxLength={140}
                    onChange={(e) => packageChange(i, "label_ar", e.target.value)}
                  />
                </Field>
              </div>
              <div className="form-grid">
                <Field label="Package description">
                  <textarea
                    value={p.description}
                    maxLength={2000}
                    onChange={(e) => packageChange(i, "description", e.target.value)}
                  />
                </Field>
                <Field label="Package description in Arabic">
                  <textarea
                    dir="rtl"
                    value={p.description_ar}
                    maxLength={2000}
                    onChange={(e) => packageChange(i, "description_ar", e.target.value)}
                  />
                </Field>
              </div>
              <fieldset className="section-checks">
                <legend>{t("Included sections")}</legend>
                {data.sections!.map((s) => (
                  <label
                    key={s.code}
                    className={config.required_sections.includes(s.code) ? "mandatory-section" : undefined}
                  >
                    <input
                      type="checkbox"
                      disabled={config.required_sections.includes(s.code)}
                      checked={config.required_sections.includes(s.code) || p.sections.includes(s.code)}
                      onChange={(e) =>
                        packageChange(
                          i,
                          "sections",
                          e.target.checked ? [...p.sections, s.code] : p.sections.filter((x) => x !== s.code),
                        )
                      }
                    />
                    <span>
                      {lang === "ar" ? s.title_ar || s.title : s.title}
                      <small>
                        {t("Questions")}: {s.question_count}
                        {config.required_sections.includes(s.code) ? ` · ${t("Mandatory section")}` : ""}
                      </small>
                    </span>
                  </label>
                ))}
              </fieldset>
              <div className="scope-actions">
                <Button
                  type="button"
                  variant="ghost"
                  disabled={i === 0}
                  onClick={() =>
                    setConfig((c) => {
                      const rows = [...c.packages];
                      [rows[i - 1], rows[i]] = [rows[i], rows[i - 1]];
                      return { ...c, packages: rows };
                    })
                  }
                >
                  {t("Move up")}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setConfig((c) => ({ ...c, packages: c.packages.filter((_, j) => j !== i) }))}
                >
                  {t("Remove package")}
                </Button>
              </div>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            onClick={() =>
              setConfig((c) => ({
                ...c,
                packages: [
                  ...c.packages,
                  {
                    code: "package_" + (c.packages.length + 1),
                    label: "",
                    label_ar: "",
                    description: "",
                    description_ar: "",
                    sections: [],
                  },
                ],
              }))
            }
          >
            {t("Add package")}
          </Button>
        </section>
        <section className="panel padded" data-tour="package-preview">
          <h2>{t("Customer preview")}</h2>
          <PackageChoices
            configuration={offeredConfig}
            sections={data.sections!}
            selected={preview}
            onChange={setPreview}
          />
        </section>
        <div className="panel padded settings-actions" data-tour="publish-packages">
          <Button onClick={() => void persist()}>{t("Save draft")}</Button>
          <Button variant="secondary" onClick={() => void persist(true)}>
            {t("Save and publish")}
          </Button>
        </div>
      </fieldset>
      <ErrorNotice error={error} />
      {savedConfig === config && <p role="status">{t("Saved")}</p>}
      <details className="panel padded">
        <summary>{t("Version history")}</summary>
        {data.configurations.map((c) => (
          <p key={c.name}>
            v{c.version} · {t(c.published ? "Published" : "Draft")} · {c.modified}
          </p>
        ))}
      </details>
    </div>
  );
}

function TemplateType({ row, reload }: { row: Data["templates"][number]; reload: () => Promise<unknown> }) {
  const { t } = useLanguage(),
    save = useMutation("set_template_type"),
    assessmentTypes = useAssessmentTypes();
  const [value, setValue] = useState(row.assessment_type || "Internal Audit"),
    [active, setActive] = useState(!!row.is_active),
    [makeDefault, setMakeDefault] = useState(false),
    [error, setError] = useState<unknown>(),
    [busy, setBusy] = useState(false);
  return (
    <section className="panel padded template-settings">
      <header className="settings-heading">
        <h2>{t("Template availability and default")}</h2>
        <p>
          {t(
            "Disabled templates remain available here for management. They cannot be selected for new assessments. Existing assessments are unchanged.",
          )}
        </p>
      </header>
      {row.grc_is_default ? (
        <p>
          <strong>
            {t("Default")} · {assessmentTypes.label(row.assessment_type)}
          </strong>
        </p>
      ) : null}
      <Field label="Assessment type">
        <Select value={value} onChange={(e) => setValue(e.target.value)}>
          {assessmentTypes.types.map((type) => (
            <option key={type.name} value={type.name}>
              {assessmentTypes.label(type.name)}
            </option>
          ))}
        </Select>
      </Field>
      <div className="settings-options">
        <label className="settings-check">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => {
              setActive(e.target.checked);
              if (!e.target.checked) setMakeDefault(false);
            }}
          />
          <span>{t("Active template")}</span>
        </label>
        <label className="settings-check">
          <input
            type="checkbox"
            checked={makeDefault}
            disabled={!active}
            onChange={(e) => setMakeDefault(e.target.checked)}
          />
          <span>{t("Make default for this assessment type")}</span>
        </label>
      </div>
      <p className="settings-note">
        {t(
          "Disabling a default or changing its assessment type removes its default status. Choose another active template as default when needed.",
        )}
      </p>
      <div className="settings-actions">
        <Button
          loading={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              await save.execute({
                name: row.name,
                assessment_type: value,
                modified: row.modified,
                is_active: active ? 1 : 0,
                make_default: makeDefault ? 1 : 0,
              });
              await reload();
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("Save template settings")}
        </Button>
      </div>
      <ErrorNotice error={error} />
    </section>
  );
}
