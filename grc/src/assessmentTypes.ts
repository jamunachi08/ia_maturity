import { useSession } from "./session";
import { useLanguage } from "./i18n";
import type { AssessmentTypeInfo } from "./types";

/** Used only until the session arrives (or on an older server): the two built-in types. */
const BUILTIN: AssessmentTypeInfo[] = [
  {
    name: "Internal Audit",
    label: "Internal Audit",
    label_ar: "التدقيق الداخلي",
    description: "Assess your internal audit function, governance, people, methodology and reporting.",
    description_ar: "قيّم وظيفة التدقيق الداخلي والحوكمة والموارد البشرية والمنهجية والتقارير.",
    behaviour: "Internal Audit",
    requires_company_profile: 0,
    icon: "clipboard",
  },
  {
    name: "GRC",
    label: "Governance, Risk and Compliance",
    label_ar: "الحوكمة والمخاطر والامتثال",
    description: "Assess your governance, risk management and compliance practices.",
    description_ar: "قيّم ممارسات الحوكمة وإدارة المخاطر والامتثال.",
    behaviour: "GRC",
    requires_company_profile: 1,
    icon: "shield",
  },
];

/** Active assessment types as configured by the GRC App Admin, with display helpers. */
export function useAssessmentTypes() {
  const { session } = useSession(),
    { lang } = useLanguage();
  const types = session.assessment_types?.length ? session.assessment_types : BUILTIN;
  const find = (name?: string) => types.find((row) => row.name === name);
  const ar = lang === "ar";
  return {
    types,
    names: types.map((row) => row.name),
    label: (name?: string) => {
      const row = find(name);
      return (ar && row?.label_ar) || row?.label || name || "";
    },
    description: (name?: string) => {
      const row = find(name);
      return (ar && row?.description_ar) || row?.description || "";
    },
    behaviour: (name?: string) => find(name)?.behaviour || (name === "GRC" ? "GRC" : "Internal Audit"),
    requiresProfile: (name?: string) => !!find(name)?.requires_company_profile,
  };
}
