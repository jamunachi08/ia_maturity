import { useMemo, useState } from "react";
import { Copy, Plus, Star, Trash2 } from "lucide-react";
import { useData, useMutation } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { Button, Empty, ErrorNotice, Field, Loading, Modal, PageTitle, Table } from "../components";
import Select from "../Select";
import { applyTheme, themeStyle, type ThemeTokens } from "../theme";
import { TYPE_ICONS } from "../typeIcons";
import { ProfileEditor, type Catalog, type ProfileLayout, type ProfileResult } from "../OrganizationProfile";
import "./configuration.css";

/* ------------------------------------------------------------------------------------------------
   Shared helpers */

const COLOUR_FIELDS: [keyof ThemeTokens, string, string][] = [
  ["primary", "Primary", "Buttons, links, highlights and the login banner"],
  ["primary_dark", "Primary dark", "Hover states and the login gradient"],
  ["accent", "Accent", "Completed states and secondary highlights"],
  ["ink", "Text", "Body text"],
  ["muted", "Muted text", "Hints and secondary text"],
  ["background", "Page background", "Behind panels"],
  ["surface", "Panels and cards", "Panel, card and sidebar background"],
  ["border", "Borders", "Dividers and input borders"],
];

function luminance(hex: string) {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}
function contrast(a: string, b: string) {
  if (!/^#[0-9a-f]{6}$/i.test(a) || !/^#[0-9a-f]{6}$/i.test(b)) return 0;
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
// Mirrors the server rules in themes.py so problems show while editing; the server still decides.
const CONTRAST_CHECKS: [keyof ThemeTokens, keyof ThemeTokens | "#FFFFFF", number, string][] = [
  ["primary", "#FFFFFF", 4.5, "White button text on primary"],
  ["primary_dark", "#FFFFFF", 4.5, "White text on primary dark"],
  ["ink", "surface", 7, "Text on panels"],
  ["ink", "background", 7, "Text on the page background"],
  ["muted", "surface", 4.5, "Muted text on panels"],
  ["primary", "surface", 4.5, "Links on panels"],
  ["accent", "surface", 3, "Accent marks on panels"],
];

function Badge({ children, tone = "" }: { children: React.ReactNode; tone?: string }) {
  return <span className={"config-badge " + tone}>{children}</span>;
}

/* ------------------------------------------------------------------------------------------------
   Themes */

type ThemeRow = ThemeTokens & { name: string; description?: string; is_default: number; is_system: number };

export function ThemesPage() {
  const { t } = useLanguage(),
    { refresh } = useSession();
  const { data, error, mutate } = useData<{ themes: ThemeRow[] }>("themes");
  const makeDefault = useMutation("set_default_theme"),
    remove = useMutation("delete_theme");
  const [editing, setEditing] = useState<{ base: ThemeRow; mode: "edit" | "new" } | null>(null),
    [failure, setFailure] = useState<unknown>();
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        title="Themes"
        description="Colour themes for the portal, login page and website. Built-in themes can be duplicated; the default applies to everyone."
      />
      <ErrorNotice error={failure} />
      <div className="theme-grid">
        {data.themes.map((theme) => (
          <article key={theme.name} className="panel theme-card" style={themeStyle(theme)}>
            <ThemeSample theme={theme} />
            <div className="theme-card-body">
              <h2>
                {theme.name} {!!theme.is_default && <Badge tone="good">{t("Default")}</Badge>}{" "}
                {!!theme.is_system && <Badge>{t("Built-in")}</Badge>}
              </h2>
              {theme.description && <p className="muted">{theme.description}</p>}
              <div className="theme-swatches" aria-hidden="true">
                {COLOUR_FIELDS.map(([key]) => (
                  <span key={key} title={key} style={{ background: theme[key] as string }} />
                ))}
              </div>
              <div className="row-actions">
                {!theme.is_default && (
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      setFailure(undefined);
                      try {
                        applyTheme(await makeDefault.execute({ name: theme.name }));
                        await Promise.all([mutate(), refresh()]);
                      } catch (e) {
                        setFailure(e);
                      }
                    }}
                  >
                    <Star size={15} />
                    {t("Make default")}
                  </Button>
                )}
                {!theme.is_system && (
                  <Button variant="secondary" onClick={() => setEditing({ base: theme, mode: "edit" })}>
                    {t("Edit")}
                  </Button>
                )}
                <Button variant="secondary" onClick={() => setEditing({ base: theme, mode: "new" })}>
                  <Copy size={15} />
                  {t("Duplicate")}
                </Button>
                {!theme.is_system && !theme.is_default && (
                  <Button
                    variant="ghost"
                    aria-label={t("Delete") + " " + theme.name}
                    onClick={async () => {
                      if (!window.confirm(t("Delete this theme?"))) return;
                      setFailure(undefined);
                      try {
                        await remove.execute({ name: theme.name });
                        await mutate();
                      } catch (e) {
                        setFailure(e);
                      }
                    }}
                  >
                    <Trash2 size={15} />
                  </Button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
      {editing && (
        <ThemeEditor
          base={editing.base}
          mode={editing.mode}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await Promise.all([mutate(), refresh()]);
          }}
        />
      )}
    </>
  );
}

/** A miniature portal drawn with the theme's own variables. */
function ThemeSample({ theme }: { theme: ThemeTokens }) {
  return (
    <div className="theme-sample" style={themeStyle(theme)} aria-hidden="true">
      <div className="theme-sample-side">
        <i />
        <b />
        <b className="on" />
        <b />
      </div>
      <div className="theme-sample-main">
        <div className="theme-sample-banner">AlphaX</div>
        <div className="theme-sample-card">
          <strong>Your assessments</strong>
          <span>Governance · 78%</span>
          <div className="theme-sample-actions">
            <em className="primary">Continue</em>
            <em className="secondary">Report</em>
            <em className="accent">Completed</em>
          </div>
        </div>
      </div>
    </div>
  );
}

function ThemeEditor({
  base,
  mode,
  onClose,
  onSaved,
}: {
  base: ThemeRow;
  mode: "edit" | "new";
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const { t } = useLanguage(),
    save = useMutation("save_theme");
  const [values, setValues] = useState<ThemeTokens>({ ...base }),
    [name, setName] = useState(mode === "new" ? base.name + " (copy)" : base.name),
    [description, setDescription] = useState(base.description || ""),
    [error, setError] = useState<unknown>();
  const checks = CONTRAST_CHECKS.map(([fg, bg, min, label]) => {
    const ratio = contrast(values[fg] as string, bg === "#FFFFFF" ? bg : (values[bg] as string));
    return { label, ratio, ok: ratio >= min, min };
  });
  return (
    <Modal title={mode === "new" ? "New theme" : "Edit theme"} onClose={onClose}>
      <form
        className="theme-editor"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(undefined);
          try {
            await save.execute({
              data: { ...values, theme_name: name, description },
              name: mode === "edit" ? base.name : undefined,
            });
            await onSaved();
          } catch (e) {
            setError(e);
          }
        }}
      >
        <div className="theme-editor-fields">
          <Field label="Theme name">
            <input
              value={name}
              readOnly={mode === "edit"}
              required
              maxLength={40}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field label="Description">
            <input value={description} maxLength={500} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <div className="theme-colour-grid">
            {COLOUR_FIELDS.map(([key, label, hint]) => (
              <label key={key} className="theme-colour">
                <input
                  type="color"
                  value={values[key] as string}
                  onChange={(e) => setValues({ ...values, [key]: e.target.value.toUpperCase() })}
                  aria-label={t(label)}
                />
                <span>
                  <b>{t(label)}</b>
                  <small>{t(hint)}</small>
                </span>
                <input
                  className="theme-hex"
                  value={values[key] as string}
                  pattern="#[0-9A-Fa-f]{6}"
                  maxLength={7}
                  aria-label={t(label) + " hex"}
                  onChange={(e) => setValues({ ...values, [key]: e.target.value.toUpperCase() })}
                />
              </label>
            ))}
          </div>
        </div>
        <div className="theme-editor-preview">
          <ThemeSample theme={values} />
          <ul className="theme-checks">
            {checks.map((c) => (
              <li key={c.label} className={c.ok ? "ok" : "bad"}>
                {c.ok ? "✓" : "✗"} {t(c.label)}: {c.ratio.toFixed(1)}:1
                {!c.ok && ` (${t("needs")} ${c.min}:1)`}
              </li>
            ))}
          </ul>
        </div>
        <ErrorNotice error={error} />
        <div className="row-actions">
          <Button type="submit" loading={save.loading} disabled={checks.some((c) => !c.ok)}>
            {t("Save theme")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------------------------
   Screen layouts */

type LayoutRow = ProfileLayout & {
  name: string;
  screen: string;
  description?: string;
  is_default: number;
  is_system: number;
  columns: 1 | 2 | "1" | "2";
  yes_no_display: any;
};

const DEMO_PROFILE: ProfileResult = {
  profile: {
    organization: "Example Trading Co.",
    industry_type: "",
    industry_sector: "",
    other_sector: "",
    company_nationality: "",
    cr_number: "",
    ksa_license_type: "",
    ksa_license_na: 0,
    ksa_license_rows: [{ license_name: "", valid: "", expiry_date: "" }],
    regulators: [],
    other_regulator: "",
  },
  modified: "",
  can_edit: true,
  complete: false,
};

export function ScreenLayoutsPage() {
  const { t } = useLanguage();
  const { data, error, mutate } = useData<{
    layouts: LayoutRow[];
    styles: string[];
    yes_no: string[];
    global_yes_no: string;
  }>("screen_layouts");
  const catalog = useData<Catalog>("profile_catalog");
  const makeDefault = useMutation("set_default_screen_layout"),
    remove = useMutation("delete_screen_layout");
  const [editing, setEditing] = useState<{ base: LayoutRow; mode: "edit" | "new" } | null>(null),
    [previewing, setPreviewing] = useState<string>(""),
    [failure, setFailure] = useState<unknown>();
  if (error || catalog.error) return <ErrorNotice error={error || catalog.error} />;
  if (!data || !catalog.data) return <Loading />;
  const resolve = (row: LayoutRow): ProfileLayout => ({
    ...row,
    columns: String(row.columns) === "1" ? 1 : 2,
    yes_no_display:
      row.yes_no_display === "Buttons" || row.yes_no_display === "Dropdown"
        ? row.yes_no_display
        : (data.global_yes_no as "Dropdown" | "Buttons"),
    show_intro: !!Number(row.show_intro),
    show_report_lookup: !!Number(row.show_report_lookup),
    show_saved_assessments: !!Number(row.show_saved_assessments),
  });
  const preview = data.layouts.find(
    (row) => row.name === (previewing || data.layouts.find((r) => r.is_default)?.name),
  );
  return (
    <>
      <PageTitle
        title="Screen layouts"
        description="Choose how the company profile screen looks. Layouts change presentation only; validation and saved data are the same in every layout."
      />
      <ErrorNotice error={failure} />
      <section className="panel">
        <div className="table-scroll">
          <Table headers={["Layout", "Style", "Yes/No answers", "Extras", ""]}>
            {data.layouts.map((row) => (
              <tr key={row.name}>
                <td>
                  <strong>{row.name}</strong> {!!row.is_default && <Badge tone="good">{t("Default")}</Badge>}{" "}
                  {!!row.is_system && <Badge>{t("Built-in")}</Badge>}
                  {row.description && <div className="muted">{row.description}</div>}
                </td>
                <td>
                  {t(row.style)} · {String(row.columns) === "1" ? t("1 column") : t("2 columns")}
                </td>
                <td>{t(resolve(row).yes_no_display)}</td>
                <td>
                  {[
                    Number(row.show_report_lookup) ? t("Report lookup") : "",
                    Number(row.show_saved_assessments) ? t("Saved assessments") : "",
                  ]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </td>
                <td className="row-actions">
                  <Button variant="secondary" onClick={() => setPreviewing(row.name)}>
                    {t("Preview")}
                  </Button>
                  {!row.is_default && (
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        setFailure(undefined);
                        try {
                          await makeDefault.execute({ name: row.name });
                          await Promise.all([mutate(), catalog.mutate()]);
                        } catch (e) {
                          setFailure(e);
                        }
                      }}
                    >
                      <Star size={15} />
                      {t("Make default")}
                    </Button>
                  )}
                  {!row.is_system && (
                    <Button variant="secondary" onClick={() => setEditing({ base: row, mode: "edit" })}>
                      {t("Edit")}
                    </Button>
                  )}
                  <Button variant="secondary" onClick={() => setEditing({ base: row, mode: "new" })}>
                    <Copy size={15} />
                    {t("Duplicate")}
                  </Button>
                  {!row.is_system && !row.is_default && (
                    <Button
                      variant="ghost"
                      aria-label={t("Delete") + " " + row.name}
                      onClick={async () => {
                        if (!window.confirm(t("Delete this layout?"))) return;
                        try {
                          await remove.execute({ name: row.name });
                          await mutate();
                        } catch (e) {
                          setFailure(e);
                        }
                      }}
                    >
                      <Trash2 size={15} />
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </div>
      </section>
      {preview && (
        <section className="layout-preview">
          <h2>
            {t("Preview")}: {preview.name}
          </h2>
          <p className="muted">{t("Sample data. Try the controls; nothing is saved from this preview.")}</p>
          <ProfileEditor
            key={preview.name + preview.style + preview.columns + preview.yes_no_display}
            entity="preview"
            initial={DEMO_PROFILE}
            catalog={catalog.data}
            layout={resolve(preview)}
            requiredForAssessment
            preview
            onSaved={async () => {}}
          />
        </section>
      )}
      {editing && (
        <LayoutEditor
          base={editing.base}
          mode={editing.mode}
          options={data}
          onClose={() => setEditing(null)}
          onSaved={async (name) => {
            setEditing(null);
            setPreviewing(name);
            await Promise.all([mutate(), catalog.mutate()]);
          }}
        />
      )}
    </>
  );
}

function LayoutEditor({
  base,
  mode,
  options,
  onClose,
  onSaved,
}: {
  base: LayoutRow;
  mode: "edit" | "new";
  options: { styles: string[]; yes_no: string[] };
  onClose: () => void;
  onSaved: (name: string) => Promise<void>;
}) {
  const { t } = useLanguage(),
    save = useMutation("save_screen_layout");
  const [values, setValues] = useState({
    layout_name: mode === "new" ? base.name + " (copy)" : base.name,
    description: base.description || "",
    style: base.style,
    columns: String(base.columns),
    yes_no_display: base.yes_no_display,
    show_intro: !!Number(base.show_intro),
    show_report_lookup: !!Number(base.show_report_lookup),
    show_saved_assessments: !!Number(base.show_saved_assessments),
    continue_label: base.continue_label || "",
    continue_label_ar: base.continue_label_ar || "",
  });
  const [error, setError] = useState<unknown>();
  const set = (patch: Partial<typeof values>) => setValues({ ...values, ...patch });
  return (
    <Modal title={mode === "new" ? "New screen layout" : "Edit screen layout"} onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(undefined);
          try {
            const result = await save.execute({
              data: {
                ...values,
                screen: "Company profile",
                show_intro: values.show_intro ? 1 : 0,
                show_report_lookup: values.show_report_lookup ? 1 : 0,
                show_saved_assessments: values.show_saved_assessments ? 1 : 0,
              },
              name: mode === "edit" ? base.name : undefined,
            });
            await onSaved(result.name);
          } catch (e) {
            setError(e);
          }
        }}
      >
        <Field label="Layout name">
          <input
            value={values.layout_name}
            readOnly={mode === "edit"}
            required
            maxLength={40}
            onChange={(e) => set({ layout_name: e.target.value })}
          />
        </Field>
        <Field label="Description">
          <input
            value={values.description}
            maxLength={500}
            onChange={(e) => set({ description: e.target.value })}
          />
        </Field>
        <div className="form-grid">
          <Field label="Style">
            <Select value={values.style} onChange={(e) => set({ style: e.target.value as any })}>
              {options.styles.map((s) => (
                <option key={s} value={s}>
                  {t(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Field columns">
            <Select value={values.columns} onChange={(e) => set({ columns: e.target.value })}>
              <option value="2">{t("2 columns")}</option>
              <option value="1">{t("1 column")}</option>
            </Select>
          </Field>
          <Field label="Yes/No answers">
            <Select value={values.yes_no_display} onChange={(e) => set({ yes_no_display: e.target.value })}>
              {options.yes_no.map((s) => (
                <option key={s} value={s}>
                  {t(s)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <fieldset className="config-checks">
          <label>
            <input
              type="checkbox"
              checked={values.show_intro}
              onChange={(e) => set({ show_intro: e.target.checked })}
            />
            {t("Show introduction notes")}
          </label>
          <label>
            <input
              type="checkbox"
              checked={values.show_report_lookup}
              onChange={(e) => set({ show_report_lookup: e.target.checked })}
            />
            {t("Show report lookup by ID")}
          </label>
          <label>
            <input
              type="checkbox"
              checked={values.show_saved_assessments}
              onChange={(e) => set({ show_saved_assessments: e.target.checked })}
            />
            {t("Show saved assessments")}
          </label>
        </fieldset>
        <div className="form-grid">
          <Field label="Continue button label" hint="Leave empty for the default wording.">
            <input
              value={values.continue_label}
              maxLength={60}
              onChange={(e) => set({ continue_label: e.target.value })}
            />
          </Field>
          <Field label="Continue button label (Arabic)">
            <input
              dir="rtl"
              value={values.continue_label_ar}
              maxLength={60}
              onChange={(e) => set({ continue_label_ar: e.target.value })}
            />
          </Field>
        </div>
        <ErrorNotice error={error} />
        <div className="row-actions">
          <Button type="submit" loading={save.loading}>
            {t("Save layout")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------------------------
   Assessment types */

type TypeRow = {
  name: string;
  label: string;
  label_ar?: string;
  description?: string;
  description_ar?: string;
  behaviour: string;
  requires_company_profile: number;
  icon: string;
  sort_order: number;
  report_prefix: string;
  active: number;
  is_system: number;
  templates: number;
};

export function AssessmentTypesPage() {
  const { t } = useLanguage(),
    { refresh } = useSession();
  const { data, error, mutate } = useData<{ types: TypeRow[]; behaviours: string[]; icons: string[] }>(
    "assessment_types_admin",
  );
  const [editing, setEditing] = useState<TypeRow | "new" | null>(null);
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        title="Assessment types"
        description="Types customers choose when starting an assessment. Each type is also a department for staff access, invitations and report IDs."
      >
        <Button onClick={() => setEditing("new")}>
          <Plus size={16} />
          {t("New assessment type")}
        </Button>
      </PageTitle>
      <section className="panel">
        {!data.types.length ? (
          <Empty title="No assessment types" text="Add the first assessment type." />
        ) : (
          <div className="table-scroll">
            <Table
              headers={[
                "Type",
                "Base behaviour",
                "Company profile",
                "Report prefix",
                "Templates",
                "Status",
                "",
              ]}
            >
              {data.types.map((row) => {
                const Icon = TYPE_ICONS[row.icon] || TYPE_ICONS.clipboard;
                return (
                  <tr key={row.name}>
                    <td>
                      <span className="type-cell">
                        <Icon size={18} />
                        <span>
                          <strong>{row.label}</strong>
                          {row.label !== row.name && <small className="muted"> ({row.name})</small>}
                          {!!row.is_system && <Badge>{t("Built-in")}</Badge>}
                          {row.description && <div className="muted">{row.description}</div>}
                        </span>
                      </span>
                    </td>
                    <td>{t(row.behaviour)}</td>
                    <td>{t(row.requires_company_profile ? "Required" : "Not required")}</td>
                    <td>
                      <code>{row.report_prefix}</code>
                    </td>
                    <td>{row.templates}</td>
                    <td>
                      {row.active ? <Badge tone="good">{t("Active")}</Badge> : <Badge>{t("Inactive")}</Badge>}
                    </td>
                    <td>
                      <Button variant="secondary" onClick={() => setEditing(row)}>
                        {t("Edit")}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </Table>
          </div>
        )}
      </section>
      <p className="muted config-note">
        {t(
          "After adding a type: classify or create its questionnaire under Audit packages, publish it as the type's default, and add staff to the department under Audit access.",
        )}
      </p>
      {editing && (
        <TypeEditor
          row={editing === "new" ? null : editing}
          options={data}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await Promise.all([mutate(), refresh()]);
          }}
        />
      )}
    </>
  );
}

function TypeEditor({
  row,
  options,
  onClose,
  onSaved,
}: {
  row: TypeRow | null;
  options: { behaviours: string[]; icons: string[] };
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const { t } = useLanguage(),
    save = useMutation("save_assessment_type");
  const [v, setV] = useState({
    name: row?.name || "",
    label: row?.label || "",
    label_ar: row?.label_ar || "",
    description: row?.description || "",
    description_ar: row?.description_ar || "",
    behaviour: row?.behaviour || "Internal Audit",
    requires_company_profile: !!row?.requires_company_profile,
    icon: row?.icon || "clipboard",
    sort_order: row?.sort_order ?? 30,
    report_prefix: row?.report_prefix || "",
    active: row ? !!row.active : true,
  });
  const [error, setError] = useState<unknown>();
  const set = (patch: Partial<typeof v>) => setV({ ...v, ...patch });
  return (
    <Modal title={row ? "Edit assessment type" : "New assessment type"} onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(undefined);
          try {
            await save.execute({
              data: {
                ...v,
                requires_company_profile: v.requires_company_profile ? 1 : 0,
                active: v.active ? 1 : 0,
              },
              name: row?.name,
            });
            await onSaved();
          } catch (e) {
            setError(e);
          }
        }}
      >
        {!row && (
          <Field
            label="Type name"
            hint="Permanent identifier, e.g. ESG or Cybersecurity. The label below can change later."
          >
            <input value={v.name} required maxLength={60} onChange={(e) => set({ name: e.target.value })} />
          </Field>
        )}
        <div className="form-grid">
          <Field label="Label">
            <input
              value={v.label}
              required
              maxLength={140}
              onChange={(e) => set({ label: e.target.value })}
            />
          </Field>
          <Field label="Label (Arabic)">
            <input
              dir="rtl"
              value={v.label_ar}
              maxLength={140}
              onChange={(e) => set({ label_ar: e.target.value })}
            />
          </Field>
          <Field label="Description">
            <textarea
              value={v.description}
              maxLength={500}
              onChange={(e) => set({ description: e.target.value })}
            />
          </Field>
          <Field label="Description (Arabic)">
            <textarea
              dir="rtl"
              value={v.description_ar}
              maxLength={500}
              onChange={(e) => set({ description_ar: e.target.value })}
            />
          </Field>
          <Field
            label="Base behaviour"
            hint="Internal Audit: starts directly. GRC: section choice and self-reported answers."
          >
            <Select
              value={v.behaviour}
              disabled={!!row?.is_system}
              onChange={(e) => set({ behaviour: e.target.value })}
            >
              {options.behaviours.map((b) => (
                <option key={b} value={b}>
                  {t(b)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Report prefix" hint="2 to 8 letters or digits; starts every report ID of this type.">
            <input
              value={v.report_prefix}
              required
              pattern="[A-Za-z0-9]{2,8}"
              maxLength={8}
              onChange={(e) => set({ report_prefix: e.target.value.toUpperCase() })}
            />
          </Field>
          <Field label="Display order">
            <input
              type="number"
              min={0}
              max={9999}
              value={v.sort_order}
              onChange={(e) => set({ sort_order: Number(e.target.value) })}
            />
          </Field>
        </div>
        <fieldset className="type-icons">
          <legend>{t("Icon")}</legend>
          {options.icons.map((icon) => {
            const Icon = TYPE_ICONS[icon] || TYPE_ICONS.clipboard;
            return (
              <label key={icon} className={v.icon === icon ? "selected" : ""}>
                <input
                  type="radio"
                  name="type-icon"
                  checked={v.icon === icon}
                  onChange={() => set({ icon })}
                />
                <Icon size={20} aria-label={icon} />
              </label>
            );
          })}
        </fieldset>
        <fieldset className="config-checks">
          <label>
            <input
              type="checkbox"
              checked={v.requires_company_profile}
              onChange={(e) => set({ requires_company_profile: e.target.checked })}
            />
            {t("Customers complete the company profile before answering")}
          </label>
          <label>
            <input type="checkbox" checked={v.active} onChange={(e) => set({ active: e.target.checked })} />
            {t("Active: customers and staff can choose this type")}
          </label>
        </fieldset>
        <ErrorNotice error={error} />
        <div className="row-actions">
          <Button type="submit" loading={save.loading}>
            {t("Save assessment type")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------------------------
   Report access */

type ReportAccess = {
  roles: Record<string, Record<"view" | "download" | "email", number>>;
  assigned_staff: number;
  staff_roles: string[];
  capabilities: ("view" | "download" | "email")[];
};

export function ReportAccessPage() {
  const { t } = useLanguage(),
    { refresh } = useSession();
  const { data, error, mutate } = useData<ReportAccess>("report_access_settings");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <ReportAccessForm
      key={JSON.stringify(data)}
      data={data}
      t={t}
      onSaved={async () => void (await Promise.all([mutate(), refresh()]))}
    />
  );
}

function ReportAccessForm({
  data,
  t,
  onSaved,
}: {
  data: ReportAccess;
  t: (s: string) => string;
  onSaved: () => Promise<void>;
}) {
  const save = useMutation("save_report_access");
  const [roles, setRoles] = useState(data.roles),
    [assigned, setAssigned] = useState(!!data.assigned_staff),
    [error, setError] = useState<unknown>(),
    [saved, setSaved] = useState(false);
  const labels = useMemo(() => ({ view: "View", download: "Download PDF", email: "Email PDF" }), []);
  const toggle = (role: string, cap: "view" | "download" | "email", on: boolean) => {
    const row = { ...roles[role], [cap]: on ? 1 : 0 };
    if (cap === "view" && !on) row.download = row.email = 0;
    if (cap !== "view" && on) row.view = 1;
    setRoles({ ...roles, [role]: row });
    setSaved(false);
  };
  return (
    <>
      <PageTitle
        title="Report access"
        description="Which staff roles can see assessment reports. Every role stays inside its own organizations and departments; customers follow the report release settings."
      />
      <form
        className="panel padded"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(undefined);
          setSaved(false);
          try {
            await save.execute({ roles, assigned_staff: assigned ? 1 : 0 });
            setSaved(true);
            await onSaved();
          } catch (e) {
            setError(e);
          }
        }}
      >
        <div className="table-scroll">
          <Table headers={["Role", ...data.capabilities.map((c) => labels[c])]}>
            {data.staff_roles.map((role) => (
              <tr key={role}>
                <td>
                  <strong>{t(role)}</strong>
                  {role === "GRC App Admin" && <div className="muted">{t("Always has full access.")}</div>}
                </td>
                {data.capabilities.map((cap) => (
                  <td key={cap}>
                    <input
                      type="checkbox"
                      aria-label={t(role) + ": " + t(labels[cap])}
                      checked={!!roles[role]?.[cap]}
                      disabled={role === "GRC App Admin"}
                      onChange={(e) => toggle(role, cap, e.target.checked)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </Table>
        </div>
        <label className="config-checks single">
          <input
            type="checkbox"
            checked={assigned}
            onChange={(e) => (setAssigned(e.target.checked), setSaved(false))}
          />
          {t("The consultant and reviewer assigned to an assessment can always see its report")}
        </label>
        <ErrorNotice error={error} />
        {saved && (
          <p role="status" className="form-state success">
            {t("Report access saved.")}
          </p>
        )}
        <Button type="submit" loading={save.loading}>
          {t("Save report access")}
        </Button>
      </form>
    </>
  );
}
