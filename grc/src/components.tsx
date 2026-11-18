import Select from "./Select";
import { useState, useEffect, useRef, useId, Children, isValidElement, cloneElement } from "react";
import type { ReactNode, FormEvent } from "react";
import { AlertCircle, ArrowLeft, ArrowRight, Check, LoaderCircle, Search, X, Inbox } from "lucide-react";
import { useLanguage } from "./i18n";
import { errorText } from "./http";
import { FieldLabelContext } from "./fieldContext";

export function Button({
  children,
  variant = "primary",
  loading = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={"button " + variant + " " + (props.className || "")}
    >
      {loading && <LoaderCircle size={16} className="spin" />}
      {children}
    </button>
  );
}
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  const { t } = useLanguage(),
    id = useId();
  const controls = Children.map(children, (child) => {
    if (
      isValidElement<Record<string, any>>(child) &&
      typeof child.type === "string" &&
      ["input", "textarea", "select"].includes(child.type)
    ) {
      return cloneElement(child, {
        "aria-labelledby": child.props["aria-labelledby"] || id,
        "aria-describedby": child.props["aria-describedby"] || (hint ? id + "-hint" : undefined),
      });
    }
    return child;
  });
  return (
    <FieldLabelContext.Provider value={t(label)}>
      <label className="field">
        <span id={id}>{t(label)}</span>
        {controls}
        {hint && <small id={id + "-hint"}>{t(hint)}</small>}
      </label>
    </FieldLabelContext.Provider>
  );
}
export function Status({ value }: { value: string }) {
  const { t } = useLanguage();
  return (
    <span className={"status status-" + value?.toLowerCase().replaceAll(" ", "-")}>
      <span className="status-dot" />
      {t(value || "Draft")}
    </span>
  );
}
export function Loading() {
  const { t } = useLanguage();
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} />
      {t("Loading…")}
    </div>
  );
}
export function ErrorNotice({ error }: { error: any }) {
  return error ? (
    <div className="notice danger" role="alert">
      <AlertCircle size={18} />
      <span>{errorText(error)}</span>
    </div>
  ) : null;
}
export function Empty({
  title = "No results",
  text = "Nothing to show yet.",
  children,
}: {
  title?: string;
  text?: string;
  children?: ReactNode;
}) {
  const { t } = useLanguage();
  return (
    <div className="empty">
      <div className="empty-icon">
        <Inbox size={25} />
      </div>
      <h3>{t(title)}</h3>
      <p>{t(text)}</p>
      {children}
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  const { t } = useLanguage();
  return (
    <div className="page-title">
      <div>
        {eyebrow && <span className="eyebrow">{t(eyebrow)}</span>}
        <h1>{t(title)}</h1>
        {description && <p>{t(description)}</p>}
      </div>
      <div className="page-title-actions">{children}</div>
    </div>
  );
}
export function SearchInput({ value, onChange }: { value: string; onChange: (s: string) => void }) {
  const { t } = useLanguage();
  return (
    <div className="search-input">
      <Search size={17} />
      <input
        aria-label={t("Search")}
        placeholder={t("Search")}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
export function Pagination({
  page,
  total,
  size = 15,
  onPage,
}: {
  page: number;
  total: number;
  size?: number;
  onPage: (p: number) => void;
}) {
  const { t } = useLanguage();
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="pagination">
      <span>
        {t("Page")} {page} {t("of")} {pages} <span className="muted">· {total}</span>
      </span>
      <div>
        <Button variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <ArrowLeft size={15} />
          {t("Previous")}
        </Button>
        <Button variant="ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          {t("Next")}
          <ArrowRight size={15} />
        </Button>
      </div>
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const { t } = useLanguage(),
    ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.querySelector<HTMLElement>("button,input,select,textarea")?.focus();
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = before;
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        ref={ref}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={t(title)}
        onKeyDown={(e) => {
          if (e.defaultPrevented) return;
          if (e.key === "Escape") onClose();
          if (e.key === "Tab") {
            const nodes = Array.from(
              ref.current?.querySelectorAll<HTMLElement>(
                "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
              ) || [],
            ).filter((n) => n.getClientRects().length);
            const first = nodes[0],
              last = nodes[nodes.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last?.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first?.focus();
            }
          }
        }}
      >
        <header>
          <h2>{t(title)}</h2>
          <button className="icon-button" aria-label={t("Close")} onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
export function Form({
  children,
  onSubmit,
  className = "",
  noValidate = false,
  id,
}: {
  noValidate?: boolean;
  children: ReactNode;
  onSubmit: (data: Record<string, any>) => Promise<any>;
  className?: string;
  id?: string;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<any>(),
    [saved, setSaved] = useState(false);
  const { t } = useLanguage();
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await onSubmit(Object.fromEntries(new FormData(e.currentTarget)));
      setSaved(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form id={id} noValidate={noValidate} className={"form " + className} onSubmit={submit}>
      <fieldset disabled={busy}>{children}</fieldset>
      <ErrorNotice error={error} />
      {busy && (
        <div className="form-state">
          <LoaderCircle size={15} className="spin" />
          {t("Saving…")}
        </div>
      )}
      {saved && !busy && (
        <div className="form-state success">
          <Check size={15} />
          {t("Saved")}
        </div>
      )}
    </form>
  );
}
export function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  const { t } = useLanguage();
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{t(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

const SECTORS = [
  "Banking & Financial Services",
  "Insurance",
  "Capital Markets",
  "Government / Semi-Government",
  "Energy & Utilities",
  "Healthcare",
  "Retail & Consumer",
  "Real Estate & Construction",
  "Telecom & Technology",
  "Manufacturing",
  "Non-Profit",
  "Other",
];
export function SectorSelect(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { t } = useLanguage();
  return (
    <Select name="sector" {...props}>
      <option value="">{t("Select sector")}</option>
      {SECTORS.map((v) => (
        <option value={v} key={v}>
          {t(v)}
        </option>
      ))}
    </Select>
  );
}
