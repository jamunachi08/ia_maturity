/** Creation choices must satisfy the same active/published policy as the server. */
export function activeAssessmentTemplates<
  T extends { is_active?: number | string; grc_published?: number | string },
>(templates: T[] = []): T[] {
  return templates.filter(
    (template) => Number(template.is_active) === 1 && Number(template.grc_published) === 1,
  );
}
