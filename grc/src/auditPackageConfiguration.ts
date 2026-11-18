import type { ScopeConfiguration, ScopeSection } from "./AuditScope";

/** Materialize individual choices before saving, so published snapshots stay authoritative. */
export function withIndividualSectionChoices(
  configuration: ScopeConfiguration,
  sections: ScopeSection[],
): ScopeConfiguration {
  const covered = new Set([
    ...configuration.required_sections,
    ...configuration.packages.flatMap((p) => p.sections),
  ]);
  const codes = new Set(configuration.packages.map((p) => p.code));
  const individual = sections.flatMap((s, index) => {
    if (covered.has(s.code) || s.question_count === 0) return [];
    let code = `section_${index + 1}`;
    while (codes.has(code)) code += "_";
    codes.add(code);
    return [
      {
        code,
        label: s.title,
        label_ar: s.title_ar || s.title,
        description: "Assess this section.",
        description_ar: "تقييم هذا القسم.",
        sections: [s.code],
      },
    ];
  });
  return { ...configuration, packages: [...configuration.packages, ...individual] };
}
