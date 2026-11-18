import { ClipboardCheck } from "lucide-react";
import { TYPE_ICONS } from "./typeIcons";
import { useLanguage } from "./i18n";
import { useAssessmentTypes } from "./assessmentTypes";
import "./assessment-types.css";

export default function AssessmentTypeChoice({
  value,
  onChange,
  allowedTypes,
}: {
  value: string;
  onChange: (value: string) => void;
  allowedTypes?: string[];
}) {
  const { t } = useLanguage(),
    { types, label, description } = useAssessmentTypes();
  return (
    <fieldset className="assessment-types">
      <legend>{t("Assessment type")}</legend>
      {types
        .filter((row) => !allowedTypes || allowedTypes.includes(row.name))
        .map((row) => {
          const Icon = TYPE_ICONS[row.icon || ""] || ClipboardCheck;
          return (
            <label
              key={row.name}
              className={"assessment-type-card " + (value === row.name ? "selected" : "")}
            >
              <input
                type="radio"
                name="assessment_type"
                value={row.name}
                checked={value === row.name}
                onChange={() => onChange(row.name)}
              />
              <Icon size={28} />
              <strong>{label(row.name)}</strong>
              <span>{description(row.name)}</span>
            </label>
          );
        })}
    </fieldset>
  );
}
