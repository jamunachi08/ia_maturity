# v2.10.0 — Configurable report colors

GRC administrators and GRC managers have a Report color ranges page in the staff sidebar. Add/remove as many ranges as needed, including ten or more, choose colors with a picker or #RRGGBB input, preview the ranges, and save. Restore default ranges resets the editor; Save applies the choice.

Each start percentage is inclusive. A range ends just before the next start; the final range includes 100%. Starts must be finite, unique and within 0–100, and the first must be 0. Ranges are sorted on save, so there are no gaps or overlaps. A final start at 100 can give exactly 100% a separate color.

Managers can edit only this policy, without general Settings access. Customers and ordinary auditors cannot read the management API or save ranges. Writes are audited and reject stale revisions.

In-progress assessments and newly generated PDFs use the current saved policy. Released reports retain their issued PDF and a snapshot of the policy, and their frontend score bars use that snapshot. Reports issued before this feature use the previous default ranges. Scores, maturity labels and scoring thresholds are unchanged.

Upgrade: migrate the site and rebuild frontend assets with Node 24. Existing four-color behavior is the fallback until a policy is saved.

Validation: 77 backend integration cases, 7 unit/PDF cases, 14 browser scenarios, build/lint, ten-range save/reload and actual custom PDF drawing-color verification.

[Configuration and workflows](GRC_ASSESSMENT_PRESENTATION.md) · [Changelog](CHANGELOG.md) · [README](../README.md).
