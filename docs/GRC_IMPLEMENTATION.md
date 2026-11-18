# GRC implementation

[README](../README.md) · [Developer introduction](introduction.md) · [Changelog](CHANGELOG.md)

Implemented in `ia_maturity` and activated only on `grc.local`. This is a working local release candidate, not a production deployment.

## Local preview

- Login: http://localhost:8005/login
- Public website: http://localhost:8005/grc-site
- Customer: `customer@alpha.example.test`
- Auditor: `auditor@grc.example.test`
- Reviewer: `reviewer@grc.example.test`
- GRC app admin: `admin@grc.example.test`
- Unassigned auditor: `unassigned@grc.example.test`
- Separate ERP account: `erp@grc.example.test`

Passwords are generated locally and stored in `sites/grc.local/private/grc-local-credentials.json` (mode 0600). They are not committed. Staff require an authenticator code. The CLI helper `scripts/local_test_otp.py <demo-email>` is restricted to the muted local test site and reserved demo addresses. It is for local acceptance testing, not production authentication.

## Delivered behavior

| Area | Implementation |
|---|---|
| Login | One branded React login, EN/AR, standard password authentication, customer email code/link, recovery, staff MFA |
| Dashboards | Customer next action, assessments, completion, scorecards and actions; auditor assigned portfolio, due reviews, follow-ups and reassignment indicators |
| Admin | Nested auditor administration for assignments, staff, versioned templates, scoring defaults, result visibility, reminders, legal content and consultations |
| Organizations | Verified onboarding, organization profile, branches/departments, active memberships, invitations and member responsibilities |
| Assignments | Multiple explicitly assigned auditors per organization, Consultant/Reviewer responsibilities, separate assessment task allocation |
| Assessments | Bilingual questionnaire, section navigation, autosave with optimistic concurrency, private evidence, submission validation and correction cycle |
| Reports | Frozen published questionnaire/scoring policy, frozen release context and private PDF with SHA-256 integrity checks; embedded Arabic fonts |
| Actions | Owners/deadlines, completion notes/evidence, separate reviewer closure; contributors see their assigned actions without gaining access to another person's assessment |
| Operations | Audited changes, notification preferences, reminders, delivery status/retries through Frappe Email Queue, follow-up history |
| Public website | Home, services, catalogue, frameworks/sectors, About, Contact, Resources, FAQs, Privacy, Terms, Start Assessment and tracked consultation requests |

Later control/compliance/risk/asset/audit/incident/vulnerability modules are not exposed in navigation.

## Routes and account boundary

| Route | Purpose |
|---|---|
| `/login`, `/update-password` | React authentication and recovery |
| `/grc/customer/*` | Customer workspace |
| `/grc/auditor/*` | Auditor workspace |
| `/grc/auditor/admin/*` | GRC app-admin screens |
| `/grc-site/*` | Public pages |
| `/ia-assessment` | Compatibility redirect retaining assessment and verification parameters |
| Existing ERP home | Normal ERP account destination |

Server-side account classification survives accidental ERP role assignment. GRC accounts cannot use Desk, ERP document routes, generic Frappe APIs, REST resources or API v2. A narrow allowlist permits purpose-specific GRC APIs and necessary core authentication methods. Cookie and token authentication pass through the same request boundary. Document hooks and private-file checks provide an additional boundary.

Normal ERP accounts retain their normal routing and permissions. GRC app admins are portal accounts; the Frappe Administrator remains the platform operator. Users needing both applications need separate accounts.

Every GRC list, lookup, count, assessment, action and download is scoped through current memberships or auditor assignments. Assessment task allocation cannot grant customer visibility. Revocation is checked on the next request, clears task allocation for reassignment, invalidates permissions, and expires queued tracked messages where access was lost. The React session polls an access/version fingerprint every 30 seconds and reloads to clear stale displayed data. Already-viewed information cannot be recalled.

Private evidence is restricted to authorized assessment/action ownership. Released report downloads additionally verify file integrity. Generic export/report APIs are blocked for GRC accounts; approved PDF downloads are the supported report export. Confidential ERP attachments must also use private storage.

## Workflow and history

`Draft → In Progress → Submitted → Under Review → Approved → Report Released`

Clarification creates an amended draft while retaining the earlier submission and review history:

`Under Review → Clarification Required → Resubmitted → Under Review`

Consultants/reviewers require both an active customer assignment and the relevant assessment task. Approval and release require the designated reviewer or app admin. Report release freezes the customer report context, policy reference, reference date and PDF. Later template, scoring or visibility changes do not rewrite a released artifact.

Published templates cannot be edited. Clone a new version, edit the questionnaire/sections, and publish it. Each assessment retains its published policy and questionnaire snapshot.

The provisional scoring behavior retains Q1 gating, Q20 N/A, calculated Q13 with manual fallback, and equal question weighting. Owner approval and comparison with the source workbook remain release gates.

## Result visibility

- **Preliminary scorecard (default):** submitted self-assessment scores are visible and labeled preliminary; final PDF is unavailable before release.
- **Status only:** unreleased scores, scorecards, findings/actions derived from scores and reports are withheld by the server.

The setting applies immediately on subsequent requests. Changes trigger the frontend access fingerprint refresh. Released reports remain available to authorized users. Workflow emails contain status and links, not scores, report attachments or customer results.

Cross-customer live benchmarking is suppressed in GRC customer reports to preserve strict customer isolation. A future benchmark feature needs an approved, versioned anonymized reference dataset; it must not query another customer's live records through the portal.

## Source map

- `grc/src`: React/TypeScript screens, RTL translations and styles.
- `grc/tests`: Playwright browser acceptance tests.
- `ia_maturity/grc/security.py`: account, tenant, document, file and request boundaries.
- `ia_maturity/grc/auth.py`: customer verification and MFA-safe recovery.
- `ia_maturity/grc/assessments.py`: immutable policies, workflow, results and release.
- `ia_maturity/grc/organizations.py`, `administration.py`, `api.py`: authenticated application services.
- `ia_maturity/grc/notifications.py`: reminders and delivery records.
- `ia_maturity/grc/setup.py`: idempotent activation/migration.
- `ia_maturity/templates/grc_report.html`: GRC PDF layout.
- `ia_maturity/grc/test_access.py`: integration acceptance tests.

Doppio supplied the React scaffold. Runtime behavior, build hooks, routing and permissions are inside this app. No Doppio customization or other custom theme dependency is required.

## Validation performed

Validated locally on Frappe **15.118.0**, ERPNext **15.119.3**, Python **3.11.14** and Node **24.18.1**.

- Existing downloaded-app baseline: 27 tests passed before enabling GRC mode.
- GRC integration: 23 tests passed, including tenant isolation, multi-auditor access, revocation, contributor actions, immutable scoring, correction/release and Arabic PDF generation.
- HTTP acceptance passed: login routing, MFA, password recovery without an MFA bypass, cookie/token restrictions and active-session revocation.
- Chromium acceptance: 10 scenarios passed, including styled dropdown keyboard/RTL behavior, dashboard card filters, profile editing and admin field restrictions. Coverage also includes customer/admin/auditor/unassigned journeys, nested routes, immediate-navigation autosave, Arabic RTL and a 390px mobile layout.
- TypeScript/Vite/Frappe build and lint passed; production npm dependency audit reported zero vulnerabilities.
- Migration completed successfully; a backup was restored into a disposable isolated schema and core row counts matched.
- Arabic report pages were rasterized and visually inspected.

The original README's framework compatibility claims describe the imported baseline. This GRC implementation has not been certified on Frappe 16. Browser coverage is Chromium; Firefox/Safari, formal accessibility review, load testing and production email delivery still require acceptance.

## Release gates

1. Assessment owner confirms scoring against the reference workbook and approves framework/questionnaire content in both languages.
2. Replace draft public/legal content with reviewed organization-specific text.
3. Provide the production hostname, HTTPS, transactional email and MFA enrollment delivery.
4. Configure supervised web/worker/scheduler processes, private file storage, backups, monitoring and restore procedures.
5. Rehearse a full production restore including files, encryption key, services and DNS; perform customer UAT, additional browser/accessibility and load testing.
6. Remove demo/test accounts from production and provision real organization memberships and staff assignments.

See [GRC operations](GRC_OPERATIONS.md) for build, test, local startup and production procedures.


## Dashboard controls and profile settings

All portal dropdown menus use the same styled Select component, including dialogs, administration, questionnaire templates, organization forms and public contact forms. The component provides keyboard navigation, typeahead, scrolling, focus return, RTL and native form validation/serialization.

Dashboard cards are links:
- Assigned customers opens the customer directly when only one is assigned; otherwise it opens the permitted customer list.
- In progress filters Draft and In Progress assessments.
- Awaiting review filters Submitted, Resubmitted and Under Review.
- Overdue applies the same deadline predicate as the card count.
- Reports released filters Report Released assessments.

Filters are retained in the URL; refresh and browser navigation preserve them. Selecting an individual status replaces a grouped card filter. Tenant permissions remain enforced before counts and filters.

Click the sidebar avatar/name to open My profile at `/grc/customer/profile` or `/grc/auditor/profile`. Users can edit approved name, phone, language and time-zone fields. In **Administration → Settings → Profile editing permissions**, a GRC app admin controls the allowed fields for customer and staff self-service. An empty selection locks all personal fields. Saves re-read the policy on the server; manipulating disabled controls or calling the API directly cannot change a forbidden field or another account.

Email, roles, account classification and organization assignments cannot be enabled as self-editable fields. Password changes remain available to the account owner, require the current password and confirmation, use Frappe password policy, and sign out sessions. Staff must complete MFA on the next login. Password values are never included in the GRC audit log.

Validation includes `scripts/profile_http_acceptance.py`, which tests customer and staff password changes with disposable accounts on the muted local site. It verifies wrong-password rejection, old-password invalidation, logout and staff MFA, then deletes only its own test accounts.
