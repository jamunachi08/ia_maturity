# v2.12.0 — Customer assessment focus

Customers enter questionnaire focus mode automatically. Normal view restores the application while retaining answers; Full screen reopens focus mode. Native fullscreen starts on interaction when permitted by the browser. Escape and browser exit are respected for the current tab session. Staff and read-only assessments keep their usual view.

No schema migration is introduced. Deploy the release and rebuild frontend assets, then clear site/browser caches. Existing maturity visibility, report and question-extra policies remain active.

See [presentation and flow](GRC_ASSESSMENT_PRESENTATION.md#customer-assessment-focus-mode), [introduction](introduction.md) and [changelog](CHANGELOG.md).

## Validation

- Production build and TypeScript checks passed on the isolated staged release.
- Lint passed with zero errors and two pre-existing warnings (PageTour and Templates).
- 31 Playwright checks passed, including actual Chromium fullscreen entry/exit, unsupported/denied fullscreen, persisted normal view, mobile submission, existing visibility controls and report colors.
- 78 local Frappe access/integration regressions and seven presentation unit tests passed.
- Desktop and mobile screenshots reviewed. Browser API interactions are exercised in Chromium; unsupported environments keep the app focus layout.
