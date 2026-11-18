# Release v2.16.1

Version: 2.16.0 → 2.16.1. Date: 2026-11-11.

## Customer assessment dates

Customers now see only when an assessment started and when they submitted it, in the assessment page, dashboard and Assessment dates page. Submission is labelled Assessment finished; it does not mean staff approval or report release. Answer edits, evidence events, actors and review details are absent from customer history views.

All underlying GRC Activity records remain intact. Authorized staff retain their detailed Activity view. This is a presentation change, not a deletion or change to the existing activity authorization model. Customer Help, page tour and bilingual PDF are updated.

## Layout corrections

Mobile workspace controls use an aligned grid. Tables keep readable names/emails with horizontal scrolling. Help setup text wraps within the page. Workspace preferences, assessment-display settings, ownership controls and onboarding dates/actions now have consistent spacing. Signed-out demo access uses a centered panel. The [review record](GRC_LAYOUT_REVIEW.md) lists page and role coverage, including the manager presentation fixture limitation.

## Validation

- Main role pass: 303 views; profile/organization/oversight tab pass: 255 views; public/access pass: 48 views. No page-width overflow or page errors reported; changed controls received targeted visual rechecks.
- Browser regression coverage includes customer/staff history, focus mode, packages, assessment types, display settings, colors, Help/PDF, signup, page tours and workspace preferences. Initial 41-scenario pass and final 17-scenario pass succeeded.
- Backend checks cover customer milestone filtering before the recent-event limit, unchanged stored history, full staff activity and existing access/lifecycle behavior. Long-process runs encountered native segmentation faults near PDF-related cases; all 79 tests subsequently passed using four sequential 16-test batches and 15 isolated test processes. No product workaround was added for the native-process crash.
- Frontend typecheck/build passed; lint has zero errors and three pre-existing warnings. Updated English/Arabic customer PDF pages were visually reviewed.

## Upgrade and recovery

Use the normal backup and deployment procedure, install the release, and rebuild the frontend with Node 24 (`cd apps/ia_maturity/grc && npm ci && npm run build`). Restart application processes and clear site/browser caches through the normal deployment process. No data migration is needed for this release. Deploying older frontend assets restores the older presentation without requiring history recovery, because events are never removed.

This commit/push does not deploy production. Disposable-site tests sharing database/cache state must run sequentially.

[README](../README.md) · [Changelog](CHANGELOG.md) · [Developer flow](introduction.md#customer-assessment-dates-v2161) · [Layout audit](GRC_LAYOUT_REVIEW.md)
