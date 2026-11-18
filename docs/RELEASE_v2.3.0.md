# Release v2.3.0

**Date:** 2026-11-01

[README](../README.md) · [Developer introduction](introduction.md) · [Changelog](CHANGELOG.md) · [Operations](GRC_OPERATIONS.md)

## What changed

- English and Arabic in-app guides for customers, auditors and administrators, including administrator setup.
- Downloadable bilingual PDFs with schematic navigation illustrations.
- Page-specific tours that start on a first visit, describe available controls and examples, and can be skipped or replayed. Automatic tours can be disabled in the current browser.

Tour progress is stored per account in local browser storage and is not synchronized across devices. Availability of actual actions remains subject to roles, assignments and settings. No schema migration is introduced by this release.

## Deploy and verify

From the bench root, deploy this version using the normal site upgrade procedure, install the frontend lockfile if needed, run `bench --site YOUR_GRC_SITE migrate` and `bench build --app ia_maturity`, then restart the production services. The three PDFs under `ia_maturity/public/guides` must be included with the app files. Verify the asset links and sign in with customer, auditor and administrator accounts; check both languages, a page tour, skip and replay. Configure email and MFA using the existing operations and setup documentation.

To revise PDFs after changing `grc/src/guide-content.json`, run `cd grc && node scripts/build-guides.mjs` with Node 24, Playwright Chromium and Arabic fonts installed, then rebuild the frontend. PDF diagrams are illustrations rather than live screenshots.
