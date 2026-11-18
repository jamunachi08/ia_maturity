# Release v2.17.0: Company profile

## What users can do

Open **Organization > organization > Company profile** (staff use **Assigned customers**) to view the organization's reusable company details. Existing organization-management permissions govern editing. GRC drafts with an incomplete profile show this form before scope/questions; Internal Audit assessments bypass it.

The profile includes organization name, industry and dependent sector, Other-sector text, nationality, optional 10-digit CR where applicable, KSA license or explicit N/A, optional complete license detail rows, and applicable regulators. A license marked valid cannot have an expired date. Nationality and sector determine CR visibility and regulator choices. Profile answers do not affect scores or question scope.

Submission saves a profile snapshot plus catalogue hash on the assessment. Later organization edits do not rewrite that snapshot or historical report context. Existing released reports remain unchanged; historic assessments without a profile snapshot are not populated from the current profile.

## Upgrade

1. Back up the target site using the normal deployment process.
2. Install this app revision and run `bench --site YOUR_GRC_SITE migrate`. This adds Entity/Assessment fields and the GRC Profile License and GRC Profile Regulator child tables. GRC setup backfills only missing assessment types from the linked template; repeat runs preserve populated values.
3. Rebuild frontend assets with the supported Node 24 setup and restart application processes using the normal deployment procedure. Clear caches and verify Company profile in English and Arabic.
4. Test GRC profile completion, scope confirmation, submission and report access; confirm Internal Audit still opens without this gate.

Incomplete existing GRC drafts now require company details before further scope/answer work. Already-submitted profile snapshots stay frozen. If rollback is necessary, use the tested backup/restore procedure; do not delete profile tables or snapshots as an ad hoc rollback.

## Validation and limits

Release checks: 8 profile backend tests and 23 combined profile/scope UI tests passed. Build/typecheck passed; lint has zero errors and three pre-existing warnings. The Profile implementation handoff also records repeated migration, exact catalogue parity, 20 backend scope regressions and one unmocked browser/API/database save/reload/restore test.

Restricted department-level sharing is not implemented by this release. S03.01 remains in Review for that acceptance criterion; S03.02-S03.05 remain locally verified Done (4/46 Done, 1 Review, 41 pending). This release uses current organization authorization and does not certify the broader questionnaire/backlog. Production deployment and business UAT remain separate.

[README](../README.md) · [Changelog](CHANGELOG.md) · [Profile architecture](introduction.md#company-profile-v2170) · [Progress record](PLAN_PROGRESS.md)
