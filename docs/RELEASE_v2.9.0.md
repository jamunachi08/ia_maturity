# v2.9.0 — Report colors and questionnaire opening

Section percentages use the screenshot depth: 100% blue #1C5CA3, 75–<100% green #2D7A33, 50–<75% orange #BF530B, below 50% red #B42318. Exact boundary scores 75 and 50 use green and orange. The frontend and PDF renderer read the same public/section-score-colors.json palette. These are presentation bands; maturity labels, assessment points and policy thresholds are unchanged. Overall maturity keeps its existing classification color.

The questionnaire opens with visible section tabs, a clear assessment title and compact Overall maturity/Report rows with chevrons and Expand/Collapse actions. Before results are authorized, expanding maturity shows a completion message. Scoring timing remains admin controlled. Comments and attachments remain disabled by default. The report preview and download still share the same authorized PDF endpoint.

PDF chart bars and frontend progress tracks have rounded ends. Fonts and the compact A4 layout are unchanged. Existing released PDF artifacts remain immutable; new rendering applies to preliminary reports and future releases.

Upgrade: run site migration and rebuild frontend assets with Node 24. The opening-view patch changes the former Collapsed until complete default to Always expanded, while preserving Always collapsed/Hidden overrides. Admins can select any overview mode again after migration.

Validation: 75 backend integration cases, 6 policy/PDF unit tests, 10 Playwright scenarios, production build/lint and visual review of desktop/mobile screenshots and one-page A4 output.

[Configuration and workflows](GRC_ASSESSMENT_PRESENTATION.md) · [Changelog](CHANGELOG.md) · [README](../README.md).
