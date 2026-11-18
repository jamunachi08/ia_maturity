# v2.12.1 — Active questionnaire choices

Start assessment offers only active, published templates for customers and administrators. Ineligible defaults are skipped, and creation is disabled when no eligible template exists. Template management continues listing all versions, and existing assessments retain their snapshots.

Deploy the release, rebuild frontend assets and clear caches. No schema change is introduced.

[Workflow and behavior](GRC_ASSESSMENT_PRESENTATION.md#active-assessment-template-selection-v2121) · [Introduction](introduction.md) · [Changelog](CHANGELOG.md).

## Validation

The isolated staged release passed production build/TypeScript checks, lint (zero errors; two existing warnings), 36 Playwright checks (35 browser regressions and one template-filter unit check), and seven Python presentation unit tests. Customer and administrator fixtures cover mixed template lists, inactive defaults and no eligible templates. Backend creation validation is unchanged.
