import type { ReactNode } from "react";
import { ChevronRight, Plus, Minus } from "lucide-react";
import { useLanguage } from "./i18n";
export default function AssessmentDisclosure({
  title,
  note,
  open,
  className = "",
  children,
}: {
  title: string;
  note?: string;
  open?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const { t } = useLanguage();
  return (
    <details className={"panel assessment-disclosure " + className} open={open || undefined}>
      <summary>
        <ChevronRight className="disclosure-chevron" size={18} />
        <span className="disclosure-label">
          <strong>{t(title)}</strong>
          {note && <span className="disclosure-note">{t(note)}</span>}
        </span>
        <span className="disclosure-action">
          <span className="when-closed">
            {t("Expand")} <Plus size={16} />
          </span>
          <span className="when-open">
            {t("Collapse")} <Minus size={16} />
          </span>
        </span>
      </summary>
      <div className="disclosure-content">{children}</div>
    </details>
  );
}
