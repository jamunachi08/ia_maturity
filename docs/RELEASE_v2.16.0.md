# Release v2.16.0

Version: 2.15.1 → 2.16.0. Date: 2026-11-11.

Admins and GRC managers can disable templates, including defaults, and select independent defaults for Internal Audit and GRC. All new-assessment choices show active published templates with Default labels. Management retains disabled versions for reactivation. Template and audit-package pages now have spaced option cards, guidance and action areas with mobile/Arabic RTL support.

## Upgrade

1. Back up the target site and install this release through the normal deployment process.
2. Run `bench --site <grc-site> migrate` to add the default marker and apply the GRC-only patch.
3. Build the frontend with Node 24 (`cd apps/ia_maturity/grc && npm ci && npm run build`), then restart application processes and clear the site cache through the normal deployment process.
4. Verify both assessment types in Audit packages. The previous active published default is preserved in its own type; configure the other type explicitly as needed.

The migration does not reactivate templates or alter existing assessments/reports. Non-GRC sites retain legacy defaults. This release preparation does not deploy to production.

## Behavior and recovery

- Disabling or reclassifying a default clears its designation without promoting a replacement. Re-enable it and select Make default for this assessment type to restore it, or choose another active published version.
- A stale save requires reloading the page. Default changes are serialized and audited.
- Admin integrations needing draft/disabled lists must request `templates(management=1)`. Ordinary choices are active/published only; managers continue using `scope_configurations` for configuration.
- Requests omitting a template use the selected type's default (Internal Audit when type is omitted). When no default exists, supply an active template explicitly.

## Validation

- 83 backend tests passed: 78 access/lifecycle regressions and 5 assessment-type/default tests on disposable `grc.local`.
- 8 browser scenarios passed; the 7 package/onboarding scenarios were rerun after layout changes.
- Frontend build passed. Lint reported zero errors and three existing warnings.
- English desktop/mobile publishing and package controls, plus Arabic mobile packages, were visually reviewed.

[Configuration guide](GRC_ASSESSMENT_TYPES.md) · [Feature architecture](introduction.md#template-availability-and-defaults-v2160) · [Changelog](CHANGELOG.md) · [README](../README.md)
