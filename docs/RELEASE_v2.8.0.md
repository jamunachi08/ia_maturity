# v2.8.0 — Focused assessments and A4 reporting

The standard assessment report now fits its summary, section chart and table, totals and scoring method on the first A4 portrait page. The report uses the exact colors extracted from the supplied GRC PDF. Scores, maturity classifications and thresholds remain derived from the frozen assessment policy. Very long custom questionnaires continue onto additional pages. Existing released PDFs remain immutable; the new layout applies to newly rendered preliminary reports and future releases.

Customer section navigation starts collapsed until every question is answered. The aggregate answered/pending count and progress bar remain visible. Current scoring appears after the final answer, including an N/A answer. Settings > Assessment presentation offers scoring during assessment, after all answers, or after submission; section overview can expand after completion, stay collapsed, stay expanded or be hidden. Existing report-release and result-visibility permissions still apply.

Comments and evidence remain globally disabled by default. New questionnaire defaults and missing inherited flags also resolve to disabled. Explicit questionnaire overrides require the GRC admin master switch to be enabled.

GRC admins can open the default questionnaire and choose Edit default template. This creates an editable revision with extras disabled. Publish with Use as default for new assessments checked to switch the default; existing assessments keep their snapshots. Other published versions can also be selected as the default.

Upgrade: run site migration and rebuild frontend assets with Node 24. No scoring data or existing release files are rewritten.

Validation: 74 backend integration tests, 5 policy/PDF tests, 8 Playwright scenarios, production build, lint, and visual inspection of the one-page A4 render.

[Configuration and workflows](GRC_ASSESSMENT_PRESENTATION.md) · [Changelog](CHANGELOG.md) · [README](../README.md).
