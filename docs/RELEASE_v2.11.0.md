# v2.11.0 — Overall Maturity visibility

Overall Maturity is completely hidden by default for customers and staff. This removes the entire panel and its aggregate current-score display, without changing assessment calculations, answering, or report contents.

Modes:
- Hidden: no panel or aggregate score widget.
- After assessment completion: show overall maturity and all section scores once every question is attempted, including N/A.
- Completed sections only: progressively show fully answered sections; omit unfinished sections and never show an aggregate score. All-N/A sections display Not applicable without a zero-score bar.

When enabled, the panel opens automatically and can still be manually collapsed. The old expansion-default field is hidden and retained only for compatibility. Existing result-access permissions remain enforced, including submitted customer results withheld until release where configured.

Controls:
- Portal: staff sidebar > Assessment display, available to GRC App Admin and GRC Manager. Admin Settings > Assessment presentation also exposes the mode.
- Desk administrator: /app/grc-settings > Overall Maturity panel.
- Desk GRC manager or GRC app admin: /app/grc-staff > Assessment display.

Managers use dedicated validated, audited APIs and do not gain broad Settings or unassigned assessment access. The native Settings controller validates modes too. HTTP allowlists and MFA enforcement cover the new methods.

Deploy: update code, run site migration, rebuild frontend assets with Node 24, clear cache and restart backend services. Updating the Python version alone will not update the live questionnaire UI.

Validation: 78 backend integration tests, 7 policy/PDF tests and 23 browser scenarios, including native Desk control wiring, plus build/lint and isolated-release checks.

[Configuration](GRC_ASSESSMENT_PRESENTATION.md) · [Changelog](CHANGELOG.md) · [README](../README.md).
