# Development and acceptance criteria

[README](../README.md) · [Architecture and workflows](introduction.md) · [Changelog](CHANGELOG.md) · [Operations](GRC_OPERATIONS.md)

## Current customer journey amendment (2026-11-12)

Later staff-auth amendment: staff 2FA is disabled by default. App admins manage
global defaults, per-staff-role policies and individual username overrides in
Account security. Individual overrides win, then role policies (Required wins
among multiple roles), then the global default. Preserve explicit settings and
unrelated ERP security requirements. Customer email OTP remains mandatory every
sign-in; customers have no password option. This supersedes historical mandatory
staff defaults below. Changes require admin/password authorization, audited
session revocation, native challenge checks when enabled, and EN/AR frontend QA.

The final user journey supersedes historical customer password requirements and link-only report email. Customers create an account only after email verification and use a server-proven email OTP on every sign-in; staff/ERP password and MFA controls remain. Company is required at signup; sector belongs to the mandatory reusable GRC profile. Invitations lock recipient/company/type/minimum scope. GRC includes Awareness plus at least one other section; IA skips GRC profile/scope. Email report attaches the authorized PDF to the registered customer.

Department membership and organization grants are server-owned. Apply the same predicate to rows/counts/oversight, actions, files, PDFs and notification references. Basics-only staff access must not disclose profile snapshots or report artifacts. A second audit requires source-manager approval and target-manager acceptance. Preserve submitted policies/profile snapshots, original IA20 and released PDF bytes.

See `DEMO_JOURNEY.md` and `PLAN_PROGRESS.md` for current validation. Native immediate-mail tests retain Email Queue construction/status but use a guarded reserved SMTP sink; no product fallback may fake sending. The user deferred real inbox testing until live deployment. Keep the local site muted. Historical version-specific criteria below remain context and do not override this amendment.

## Working environment

The validated stack is Frappe 15.118.0, ERPNext 15.119.3, Python 3.11.14 and Node 24.18.1. Frappe 16 support in the imported README is a legacy claim; it is not GRC certification. Use a disposable GRC site and distinct customer, auditor, reviewer, admin and normal ERP accounts. Never run local fixture/HTTP scripts on a production site.

From the bench directory:

```bash
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site YOUR_TEST_SITE migrate
```

The root npm build delegates to the frontend. Commit the npm lockfile; generated bundles and HTML entry points are ignored. The Doppio scaffold is already included; do not re-scaffold or move custom behavior into another app. See [operations](GRC_OPERATIONS.md) for local services, test commands and deployment.

## Design and extension rules

1. **Keep the tenant boundary on the server.** Resolve the current user, organization membership/customer assignment and operation permission before querying or returning data. Apply the same predicate to list rows, counts, search, downloads, actions, exports and notifications.
2. **Keep ERP and GRC identities separate.** Never let extra ERP roles override a GRC classification. New APIs need purpose-specific signatures and explicit request-allowlist review in `security.py`; avoid generic document CRUD endpoints.
3. **Guard writes before using service permissions.** `service_write()` and `ignore_permissions=True` are internal implementation mechanisms after validation, not caller-controlled capabilities. Validate parent/child organization ownership and attachment ownership.
4. **Preserve history.** Published templates, submitted answers, scoring snapshots and released report artifacts are immutable. Add a new template version or correction chain rather than rewriting historical data. Use row locks for transitions and optimistic concurrency for editing.
5. **Respect live result visibility.** Do not leak Status-only results through charts, counts derived from scores, notifications, private files or alternate APIs. Released authorized artifacts retain availability.
6. **Keep migrations idempotent and site-scoped.** New DocTypes belong in the app. Setup is gated by `grc_enabled`; it must not publish unrelated drafts or silently convert ERP users. Rehearse existing-data migrations on a backup.
7. **Reuse the interface.** Use the shared Select, Field, Modal, navigation and status patterns. Preserve keyboard interaction, focus, EN/AR translations, RTL, mobile layout and loading/empty/error/session-expiry states. Filters belong in URLs when navigation must preserve them.
8. **Keep profile authority explicit.** Only catalogued personal fields may be admin-enabled. The server rechecks current policy; email, roles, classification and memberships are never self-editable. Password changes continue through Frappe policy and MFA.
9. **Keep unfinished modules out of navigation.** Control/compliance/risk/asset/audit/incident/vulnerability modules are future scope. Do not present maturity scores as regulatory compliance or certification.
10. **Keep secrets and runtime artifacts outside Git.** No site config, database dumps, private evidence, credentials, OTP seeds, session tokens, test traces or generated production assets.

## Acceptance matrix

The evidence below records local validation through v1.7.2. Tests are source-controlled; logs/screenshots are transient runtime evidence. Automated checks do not replace business UAT or production configuration validation.

| ID | Required behavior | Main automated evidence |
|---|---|---|
| ID-01 | Single login routes customer, staff/admin and normal ERP correctly; staff requires MFA by default; app admins control customer/auditor policy | `scripts/http_acceptance.py`; portal/staff browser suites |
| ID-02 | Customer codes cannot authenticate staff/ERP; verification is single-use; recovery preserves MFA | `test_access.py` verification/MFA tests; HTTP suite |
| AC-01 | Multiple assigned auditors see one customer; unassigned auditor sees no customer data | Assignment/query-scope integration tests; `staff.spec.ts` |
| AC-02 | Revocation blocks current sessions and private downloads on next request; task allocation cannot bypass assignment | Revocation and assignment-only integration tests; HTTP suite |
| AC-03 | Organizations and contributors are isolated, including evidence and assigned actions | Customer/contributor, evidence ownership and assigned-action integration tests |
| AC-04 | Desk/generic APIs/tokens/accidental ERP roles cannot bypass GRC; normal ERP role administration still works | ERP boundary integration tests; HTTP suite |
| WF-01 | Submission, clarification, amendment, review, approval and release retain history | Full correction/release integration test |
| RS-01 | Both visibility modes apply on the server, including score-derived actions and reports | Status-only integration test |
| RS-02 | Later settings/template changes do not alter submitted scores or released PDFs | Published-policy and frozen-release integration tests |
| UI-01 | Deep links, refresh, autosave/navigation, EN/AR RTL and mobile work | `portal.spec.ts`, `staff.spec.ts` |
| UI-02 | Cards navigate to scoped details or matching filters; dropdown keyboard/RTL/modal behavior works | Dashboard filter integration test; `profile-controls.spec.ts` |
| PR-01 | Admin controls editable profile fields; self-edit is scoped and rejects security fields | Profile-policy integration tests; profile browser suite |
| PR-02 | Wrong current password fails; successful change logs out, invalidates old password and preserves the current required-MFA policy | `scripts/profile_http_acceptance.py` and password integration test |
| OP-01 | Schema migration, builds, Arabic PDF generation and isolated backup restore work | Migration/build checks, Arabic PDF integration test and local restore rehearsal |

Recorded checks: 27 original baseline tests before activation; 29 GRC integration tests; 15 Chromium scenarios; HTTP authentication/access and profile/password suites; lint, TypeScript/Vite/bench build; zero production npm audit findings. Arabic PDFs and dropdown/profile layouts were visually checked. See [implementation notes](GRC_IMPLEMENTATION.md) for limitations.

## Testing changes

Run only relevant checks while developing, then the affected acceptance suites before release. Shared local HTTP/browser fixtures mutate assignments and drafts; run those suites sequentially. The integration command uses `--skip-before-tests` to avoid unrelated ERPNext all-role fixtures that violate this app's separate-account policy.

A permission change needs negative tests for another tenant, an unassigned user, revoked access and a direct API/file request. A workflow change needs history/transition tests. A UI change needs the relevant browser scenario, including Arabic or keyboard interaction when affected. Avoid tests that merely duplicate implementation details.

## Remaining release prerequisites

| Owner | Required decision or verification |
|---|---|
| Assessment owner | Supply reference workbook; approve Q1 cap, Q20 N/A, Q13 fallback/minimum sample and equal weighting |
| Content/legal owner | Approve bilingual questions, framework claims, public content, Privacy and Terms |
| Product/QA | Customer/staff UAT, Firefox/Safari, formal accessibility and representative load testing |
| Platform operator | Production hostname, HTTPS, real transactional email/MFA enrollment, workers/scheduler, private-file proxy, monitoring |
| Platform operator | Full restore drill including database, files, encryption key and service configuration; remove demo accounts |
| Product/data owner | Approve a versioned anonymized benchmark dataset before enabling any future peer comparison |
| Migration owner | Map existing legacy users, organizations and assessments before opting an existing legacy site into GRC |

## Release procedure

Use semantic versioning. Update `ia_maturity/__init__.py`, root/frontend package versions and frontend lockfile metadata together. Python packaging reads its dynamic version from the module. Add dated changelog and upgrade notes; keep this acceptance matrix and architecture guide current.

Stage source, schema, tests, lockfiles and documentation only. Check staged diffs for secrets, whitespace and generated files. Create a descriptive commit and annotated `vX.Y.Z` tag; push the intended branch and tag, then verify their remote hashes. Never force-push `main`. Authentication keys and account-specific SSH configuration remain local.

For v1.7.0, the complete customer journey is exercised in grc/tests/journey.spec.ts, using the actual queued verification code and real UI assignments/review. PDF regression tests cover the standard endpoint, unreleased denial, frozen artifact reuse, external-resource rejection and unrelated ERP delegation. See [production verification steps](RELEASE_v1.7.0.md).


## v1.8.0 security and delivery acceptance

- Customer native authenticator enrollment must require password reauthentication, a session-bound expiring setup and a valid OTP. Activation revokes sessions. Email verification and recovery must not bypass MFA.
- Personal-name writes validate syntax and reject the current password. The profile never displays malformed saved name fields. Live owner names follow corrected User data; released report history remains frozen.
- All valid signup emails are accepted by default. Only GRC admins control exact-domain restrictions, and existing accounts retain login access.
- Verification and report emails use the configured Frappe outgoing Email Account and queue. Do not add app-specific SMTP credentials or claim queue creation proves delivery.
- Report emailing requires release and current access and sends only an authenticated link to the actor. Customer tenant separation and auditor revocation cover email and PDF methods.
- Tests: 36 backend integration cases, 16 browser scenarios, existing HTTP security suites, build and lint. The guarded local_authenticator_fixture.py operates only on disposable reserved addresses in the muted grc.local test database. Never run acceptance fixtures against production.
- See [v1.8.0 operations and rollout](RELEASE_v1.8.0.md) for profile correction, SMTP troubleshooting, MFA recovery and rollback constraints.


## v1.9.0 identity acceptance

- New public signup creates no User until email-link or code verification succeeds. Merely opening a link must not consume it; generic Frappe signup and unverified Guest provisioning remain blocked on GRC-enabled sites.
- Existing authenticated sessions are explicitly distinguished from new signup. Existing/admin-provisioned accounts are not retroactively disabled.
- MFA policy changes require a GRC app admin, password reauthentication and an audit entry, and revoke affected sessions. Test Required and Disabled for both customer and auditor.
- App-admin MFA, other native role policies, Administrator ERP access, tenant isolation and customer-assignment permissions remain enforced.
- Native OTP secrets survive migration and policy changes. The GRC Account MFA role grants no record permissions.
- Coverage: 40 backend cases, 18 browser scenarios and both HTTP suites, plus lint/build. See [v1.9.0 upgrade guide](RELEASE_v1.9.0.md).


## v1.9.1 backend identity acceptance

- Exercise name/password collisions through direct profile APIs, User document writes and password recovery, including alphabetic passwords and first/last-name combinations.
- Mask unsafe legacy names in profile values, live owners, staff lists, bootstrap and login response/cookie data. Verify real-name correction still works.
- Reject fabricated, wrong, expired, cross-user and reused MFA challenges before session creation. Do not authorize from frontend flags.
- Require persisted server proof for subsequent MFA-required GRC requests; reject token/OAuth bypass and invalidate older unverified sessions.
- Prove recovery never calls login_as/make_session, keeps native password strength/reset validation, consumes links and revokes sessions.
- Preserve Administrator/ERP and admin MFA policy behavior. Profile/password/authenticator browser forms delegate validation to APIs.
- Coverage: 46 backend integration cases, 18 browser scenarios and both HTTP suites; lint and production build. Test native Frappe v15 challenge/cache and reset-helper compatibility again when upgrading Frappe.


## v1.10.0 signup acceptance

- Signup hides both login-method tabs and collects organization name and sector in English/Arabic. Back to sign in retains normal password/email-code choices.
- New signup form fields are validated on the backend; no User, organization or membership is created before email verification.
- Verified new organizations use the verified email as contact and grant their creator Organization Admin membership.
- Existing-name matches, existing customers and pending invitations never grant or overwrite organization access.
- Old links/API clients without organization data retain authenticated manual onboarding.
- Validation: 50 backend integration cases, 19 browser scenarios, both HTTP suites, migration, frontend lint/build, and visual review of desktop English and Arabic mobile signup.
