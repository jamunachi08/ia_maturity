# Optional sections and mandatory section display

## Configure

1. Open **Audit packages** and choose the questionnaire version.
2. Under **Always included sections**, clear any or all mandatory checks.
3. Any section with questions that is neither mandatory nor mapped to a custom package is offered as an individual choice automatically. Custom packages still group their mapped sections.
4. Check **Customer preview**, then **Save draft** or **Save and publish**.

Individual choices are materialized into the configuration before saving, including English/Arabic labels. They remain part of the published snapshot; existing assessments are not retroactively changed. To offer every section individually, remove custom packages and clear the mandatory checks before publishing. Customers may choose one or more sections; a confirmed assessment still needs at least one question.

## Mandatory sections and counts

Mandatory sections remain editable only in the administrator/manager's **Always included sections** list. In package mappings and customer choices they are checked, disabled, gray and labelled **Mandatory section**. Packages containing only mandatory sections do not appear as optional choices. A mixed package remains selectable for its optional content; its mandatory content stays included regardless.

Each choice shows question counts by section. The selected-scope breakdown lists each included section once, so overlaps do not inflate the total.

## Local verification

TypeScript/build and 10 scope/onboarding browser scenarios passed, including admin/manager optional-only publishing, locked mandatory controls, overlapping counts and Arabic mobile layout. The existing backend optional-only confirmation test passed; empty customer selection is still rejected when there are no required questions. Lint has no errors and three existing warnings outside these changes.

The organization-profile agent completed its work before these changes started. No backend, profile or organization implementation file was edited by this change. Its uncommitted work is preserved. No migration, production deployment or release is required to validate this frontend change locally.

## Release v2.16.2

After updating the app, rebuild frontend assets using the existing deployment procedure and refresh browser caches. No schema migration is introduced. Review and publish a new package configuration for future assessments to use individual choices; existing assessments keep their saved scope. The server still rejects an assessment with no included questions.

[README](../README.md) · [Developer workflow](introduction.md#optional-section-choices-v2162) · [Changelog](CHANGELOG.md)
