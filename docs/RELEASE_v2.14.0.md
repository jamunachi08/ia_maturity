# v2.14.0 — Audit packages and auditor-owned onboarding

Customers can combine named audit packages, confirm the resulting scope and receive scores and reports for the included questions. Auditor invitations retain the original inviter throughout verification, MFA and operational approval; completed onboarding creates the customer's organization and ownership lock atomically. Auditors can monitor milestones and blockers without seeing unfinished profile values.

[README](../README.md) · [Developer introduction and diagrams](introduction.md) · [Changelog](CHANGELOG.md)

## Included changes

- Managers and administrators configure required sections and bilingual packages, preview customer choices and publish immutable versions. Assessment snapshots keep historic choices stable. Only administrators may correct an original unsubmitted draft, with a reason, concurrency check and customer acknowledgement; removed responses and evidence remain inactive history.
- One backend scope boundary controls questions, automatic answers, submission/evidence validation, scores, gating, findings and actions. Frontend progress and PDF reports follow the same coverage. Required-only scopes are valid when they contain questions; overlaps count once and empty scope is rejected. Excluded report sections read **Not assessed**.
- Auditors issue recipient-specific invitations and track server-confirmed milestones, email-system status, blockers and next actions. Resends and reminders rotate the link while preserving original attribution and progress. Completion requires the verified recipient and creates a new organization; matching names/emails never grant control of an existing organization.
- Ownership applies consistently to customer data, evidence, reports, exports and notifications. Administrators can transfer ownership, lock/unlock and grant named staff exceptions with reasons. Transfers update active consultant allocations and revoke former-owner access unless explicitly retained.
- Help now includes a distinct manager guide alongside administrator, auditor and customer guidance. Four bilingual PDFs and contextual tours cover package selection, invitations, tracking and ownership while preserving existing Help/tour preferences.
- Customer/auditor oversight includes scoped reports and configurable operational approvals. The bilingual public-site editor supports structural/content drafts, previews, ordered approval and audited publication.

## Defaults and compatibility

| Setting | Upgrade/default behavior |
| --- | --- |
| Audit package configuration | Opt in per questionnaire version; existing assessments and unconfigured templates retain all sections |
| Released reports | Existing scores, scope and released PDF files remain unchanged |
| Invitation lifetime | Seven days; new links invalidate previous tokens |
| Invited-customer auto-lock | On; snapshotted at invitation issue, never retroactive |
| Inactivity attention | 48 hours at customer-action stages; administrators may set 1–720 hours |
| Manual mail controls | 60-second minimum interval per invitation and 10 messages per recipient/hour, plus existing safeguards |
| Customer reminders | Manual only; no scheduled onboarding reminders |
| Existing customers | Remain unlocked unless an administrator explicitly changes access |
| Operational approvals | Disabled until configured; pending requests retain their submitted workflow |
| Public-site content | Existing defaults stay live; saved legacy legal notices seed the approved content store |

Package configuration privileges do not grant questionnaire, scoring-policy or account administration rights. Customer membership remains independent of staff ownership. Submitted assessments and clarification revisions retain scope; different coverage requires a new assessment. No questionnaire is imported from the reference workbook.

## Upgrade and recovery

This release prepares source and assets; it does not deploy automatically. Back up the intended GRC site's database and files before a separately authorized rollout. Deploy the tag, run `bench --site SITE migrate`, build the frontend with Node 24 (`cd apps/ia_maturity/grc && npm ci && npm run build`), run the site's normal asset build and restart procedure, and clear caches. See [Operations](GRC_OPERATIONS.md) for the established service and build commands. Run migration only against the intended site; GRC setup/default seeding is site-gated and idempotent.

Migration adds audit-scope and onboarding-invitation DocTypes, ownership and scope fields, operations policies/requests, and site content/revision/event records. Existing invitation attribution and customer access are not inferred or rewritten. Verify an unconfigured legacy assessment, a newly configured assessment, invitation completion, a permitted staff exception and an unrelated user's access denial on staging before production release.

For failed mail, inspect email diagnostics then resend after the cooldown. For a disabled inviter or competing invitation, an administrator must resolve the original request; do not rewrite `invited_by`. Restore the legitimate inviter or revoke and issue a new invitation from the intended auditor. For ownership conflicts, use authorized organization membership/ownership controls. Stale scope, ownership or content edits require a reload and review before retrying. See [audit packages/onboarding recovery](GRC_AUDIT_PACKAGES_ONBOARDING.md), [oversight policies](GRC_CUSTOMER_OVERSIGHT.md) and [website publication recovery](GRC_SITE_CONTENT.md).

If rollback is required after new records are created, restore the matching pre-upgrade database/files and previous app version using the operations procedure. Do not run older application code against newly adopted workflow state and assume it enforces the new locks.

## Validation

- Disposable `grc.local`: 131 backend tests passed across scope/onboarding (20), access (78), operations (9), notifications (10), assessment presentation (7) and site content (7).
- Native HTTP acceptance passed for authentication/MFA, ERP/API-token denial and revocation. The scope/onboarding HTTP journey passed verified-email isolation, cross-browser resume, simultaneous/idempotent activation, scope corrections/acknowledgement, scoped score/report release and immediate ownership-transfer revocation.
- All 23 affected Playwright checks passed: guides (3), page tours (3), oversight (3), scope/onboarding (5) and website content (9), including desktop/mobile and Arabic workflows and a real editor/reviewer/publication journey.
- Frontend lint/build and Python compilation passed. Lint has three existing warnings in PageTour, Templates and SiteEditor; no errors. Static public-copy validation checked 169 lookups and sample-score entries.
- All 31 pages across the four bilingual guide PDFs were visually reviewed, including Arabic layout/page breaks. The scoped report was visually checked for included scores and excluded **Not assessed** sections.
- Migration was run twice to verify idempotence. Test email was muted; production SMTP delivery was not exercised.
