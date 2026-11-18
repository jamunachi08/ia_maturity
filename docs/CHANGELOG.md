## [3.2.0] — 2026-11-17

Configuration release: colour themes, configurable assessment types, an admin screen-layout tool, role-based report access for managers and a shorter start flow.

### Added

- **Colour themes.** New GRC Theme records with an IRSAA theme taken from the logo (IRSAA blue #12506E, green accent #487242, Business Solutions grey #5A6562), now the default, and the original colours as AlphaX Classic. Admins duplicate, edit, preview and choose the default under Themes. Every brand shade in the portal, login and website derives from the theme at runtime; status colours stay fixed. Themes failing WCAG AA contrast for buttons, text and links are refused.
- **Configurable assessment types.** Admins add types (label and description in English and Arabic, icon, display order, report prefix, active switch) under Assessment types. Each type has a base behaviour (Internal Audit or GRC) and its own company-profile requirement, so new types reuse the proven rules. Each type is a department for staff access, invitations and report IDs; customers can request any type they do not have yet.
- **Screen layouts.** Admins choose how the company profile looks: Standard (the original form, still the default) or Compact (single card, Yes/No buttons per regulator, Continue to questions, report lookup by ID and saved assessments). Layouts are duplicated, adjusted (style, columns, Yes/No display, notes, extras, button label) and previewed with sample data before becoming the default. Presentation only; validation and saved data are unchanged.
- **Report access by role.** Reports (in-app view and PDF/email) are available to GRC App Admin and GRC Manager by default; admins can grant Reviewer, Consultant or Auditor view/download/email under Report access. The assessment's assigned consultant and reviewer keep access (switchable). Every check stays inside the organization and department boundary; customers keep the release policy.
- **Reports page and in-app report view** for staff with report access: summary, strongest and weakest sections, section bars, results table and scoring method, with PDF download when allowed. Customers get View report beside download.
- Report lookup by ID and saved-assessment list return only assessments the user can already open; lookups are rate-limited and give the same answer whether an ID exists or not.

### Changed

- Choosing the assessment type on the dashboard and pressing Continue now starts the assessment directly when there is one organization and a default template. The confirmation dialog appears only when something is still to choose.
- Template, assessment and invitation type fields accept any configured type (validated by the app instead of a fixed list).
- Arabic text for all new screens.

### Upgrade notes

- `migrate` adds the GRC Theme and GRC Screen Layout records, fills the built-in assessment-type fields and stores report-access defaults. Existing admin labels are kept.
- **Behaviour change:** staff who are neither managers, admins nor the assigned consultant/reviewer no longer download reports of assessments they merely can open. Grant their role under Report access if they need it.

## [3.1.2] — 2026-11-17

Repairs the test suite on Frappe v15 and v16. Doing so exposed four product defects on current Frappe, all fixed here. All 309 tests pass on fresh v15 and v16 sites. No schema changes.

### Fixed

- **Customers could not sign up or sign in on current Frappe v15/v16.** `frappe.sendmail(now=True)` now delivers only after the transaction commits, so the verification email always read "Not Sent", the code was expired and the customer saw an error. Verification emails are now queued and sent inside the request through Frappe's own queue `send()`; muted or suspended sites still report failure.
- **Staff with 2FA enabled or enforced could not sign in on current Frappe v15/v16.** Frappe now caches the 2FA challenge with `set_value`; the app read raw keys only and rejected every attempt. Both storage styles are read and both are cleared on use, so a challenge stays single-use.
- **Fresh GRC installs had no default Internal Audit template.** Frappe records patches as done on a new install without running them, so invited Internal Audit customers could not start an assessment. The per-type default is now set once at install; migrate never re-sets a default an admin cleared.
- **Approved onboarding requests failed since departments (3.0).** An approved auditor onboarding now gives the new staff member only the departments the requesting manager shares with the customer; an approved auditor-requested customer onboarding grants the requester's department, matching direct creation. Both were refused at the final assignment step.
- **A4 report spilled the scoring method onto a second page** for six-section questionnaires. Section chart rows and table padding are slightly tighter (rows 51→42 px, bars 27→24 px, cells 6→5 px) so page 1 holds the summary, results and scoring method.

### Tests

- 70 tests that failed on v16 now pass; 4 regression tests added (309 in total, passing on v15 and v16).
- Fixtures updated for the department model, fresh-install defaults, v16 email internals (`add_css`, SMTP extension checks) and current notification subjects. Fixtures are idempotent, so a failed run cannot cascade into the next.
- The original Internal Audit suites run as a non-GRC site, the mode those flows exist for, instead of against GRC guards.

See [v3.1.2 release notes](RELEASE_v3.1.2.md).

## [3.1.1] — 2026-11-17

Stabilisation release: fixes two admin defects and makes the app install and render PDFs on current Frappe v15/v16 benches. No schema changes and no workflow changes.

### Fixed

- Saving the customer verification-limit switches (new in 3.1.0) failed and rolled back every change. The policy now saves, is audited and returns the saved state.
- Staff administration showed a server error instead of its validation message for an invalid email, an attempt to convert an ERP or customer account, or removing your own admin access.
- The app failed to install on Frappe v16 because a query used `max(version)` as a field string, which v16 rejects. The query is now portable across v15 and v16.
- GRC PDF reports failed on WeasyPrint 68+ (current Frappe v15 and v16 pin 70.0) because `default_url_fetcher` was removed. Reports now use WeasyPrint's protocol allow-list on 68+ and keep the previous path on older releases; both allow embedded `data:` resources only, with no network or file reads.
- The dependency range was `weasyprint>=67,<68`, which conflicted with Frappe's own pin and forced a downgrade. It is now `>=67,<71`.
- Auditors opening an old `/desk/grc-staff` bookmark on v16 were refused instead of being redirected to their workspace.

### Changed

- Desk links and redirects use the version-correct prefix (`/app` on v15, `/desk` on v16) everywhere, including the login hand-off for ERP users and the staff Desk brand link.
- `after_install`/`after_migrate` are declared once in `hooks.py` (behaviour unchanged).
- Removed genuinely unused imports. The endpoint re-exports in `grc/api.py` are intentional and now documented and protected by the Ruff configuration.
- Frontend source formatted with Prettier (110 columns), so very long single-line components are readable and reviewable. A scoring memo in Templates no longer recomputes on every render.

### Added

- GitHub Actions CI: Ruff, Prettier check, oxlint and a production build, then the Frappe test suite on version-15 and version-16 with GRC enabled.
- Regression tests for the fixes above (`grc/test_phase1_regressions.py`); access tests now cover v16 Desk paths.

See [v3.1.1 release notes](RELEASE_v3.1.1.md).

## [3.1.0] — 2026-11-14

Add audited verification-limit administration and clearer assessment guidance.

### Added

- GRC admins can inspect and reset individual verification counters and independently enable or disable customer email and IP attempt limits, with a required reason and audit history. Limits default to enabled.
- Admin settings choose organization-profile yes/no controls and the initial guide and tour visibility for new users. Existing personal preferences remain unchanged.
- Unanswered questions are highlighted and linked by section in the assessment overview, including full-screen mode.

### Fixed

- Carry the first assessment type selection into the start dialog without asking the customer to select it twice.

See [admin controls and assessment guidance](introduction.md#admin-controls-and-assessment-guidance-v310) and the [README](../README.md).

## [3.0.2] — 2026-11-14

Improve IA/GRC startup, session handling and dashboard performance while preserving workflows and authorization.

### Changed

- Split public/login startup from the authenticated portal SDK and lazy-load workspace routes, guides and previews. Keep the small login component eager to avoid React's measured cold-route fallback delay. Published public content no longer waits for the full session bootstrap; protected routes and signup still wait for authoritative session state.
- Deduplicate session refresh requests, pause hidden-tab polling and refresh immediately on return while retaining the 30-second visible refresh interval and access-version redirects. Serialize authentication changes after older bootstrap responses to prevent stale Guest cookies overwriting a successful sign-in; cover timer/focus pause, failure recovery and access-version redirects.
- Use SQL filtering, aggregation and pagination for dashboards and bounded five-row activity/action previews, preserving the existing API contracts, role/tenant/department rules and canonical assessment payloads.
- Reuse repeated permission/name reads only inside explicit read operations. Site/user isolation, defensive copies and write/commit/rollback invalidation retain live revocation and password-name masking; no private response or authorization result is cached across requests.
- Apply language and RTL direction before the first React paint to prevent the faster login page shifting after render; keep language preference persistence unchanged.
- Keep private/authenticated responses uncached; approved public-content JSON uses private ETag revalidation against the current publication. External font styles load without blocking initial rendering, retaining the original fonts and a no-JavaScript fallback.

### Added

- Guarded, separate muted performance fixtures, production-style Gunicorn baseline/optimized servers, sanitized SQL/HTTP/browser measurement tooling and a 50-client sustained-load runner. See [local results](PERFORMANCE_RESULTS.md), [performance operations](PERFORMANCE_OPERATIONS.md) and [architecture](introduction.md#performance-with-workflow-preservation). Local implementation and synthetic acceptance remain separate from destination deployment, external inbox verification and field Web Vitals.

- 2026-11-13: [DevOps setup and server-migration checklist](../README.md#grc-site-setup-and-server-migration), covering site-specific GRC activation before migration, frontend builds, process restarts, configuration/encryption-key preservation, mail and access checks, and recovery from “GRC is not enabled on this site.” See the [activation flow](introduction.md#grc-site-activation-and-server-migration). Documentation only; application version remains 3.0.1.

## [3.0.1] — 2026-11-12

Users with no GRC role open the normal Frappe Desk at `/app/home`.

### Fixed

- Accounts without a GRC role are no longer held on the GRC site or treated as inactive because of a stale classification or the legacy respondent role.
- Sign-in, `/`, `/login` and `/grc-site` send those users to `/app/home`, and a Website User without a GRC role can open Desk.
- GRC customer and staff accounts stay on the portal and remain blocked from Desk.
- Login reports a failed session lookup instead of leaving the form in a broken state.

## [3.0.0] — 2026-11-12

Implement the final IA/GRC customer journey and clarify all eight customer,
consultant, reviewer and manager role/type workflows.

### Breaking

- Customers must sign in with immediate email OTP on every visit. Customer
  password login/reset, API-token access and pre-OTP sessions are rejected.
- Staff require explicit active IA/GRC department membership in addition to
  existing assignment rules. Role names alone no longer establish department
  access; operators must configure memberships before returning staff to service.

### Added

- Server-owned departments, staff memberships, company grants and source/target
  manager approval for a second audit type, with cross-department artifact guards.
- Workbook-derived GRC46 instrument with source provenance, selected-scope
  scoring, required Awareness and at least one optional GRC section; retain IA20.
- Recipient/company/type/minimum-scope-bound invitations and company-profile
  reuse before GRC questions, with immediate preliminary result/report access.
- Matching PDF attachments to the customer's registered email, preserving the
  independent reviewer approval and official report release workflow.
- Admin global, role and username staff2FA policy controls with a Disabled
  default, explicit policy precedence and preserved unrelated ERP requirements.
- Guarded disposable-site fixture/SMTP runner and native browser acceptance
  scenarios; no private credentials or runtime evidence included in the app.

### Fixed

- Staff login and legacy Desk bookmarks now open the custom workspace with
  correct IA/GRC branding and optional dismissible Getting started guidance.
- Draft Continue, OTP/invitation recovery, required-answer navigation,
  save-failure/exit behavior, reviewer next steps and report timing explanations.
- Manager scope/first-assignment staff choices, optional cancellation, two-stage
  access requests, organization tabs and capability-based follow-up controls.
- Bilingual role help and all four downloadable guides reflect the new journey.

### Validation

- Latest role review:147 unique browser scenarios,137 backend tests,25 help PDF
  pages rendered and visually inspected; TypeScript/Vite and targeted lint pass.
- Earlier journey/auth milestones and exact unfinished source requirements
  remain recorded separately; test counts from different milestones are not summed.
- Real inbox delivery is user-deferred until live deployment. No deployment is
  implied by this version. Broader combined-source/UAT criteria remain open.

[Release and upgrade notes](RELEASE_v3.0.0.md) ·
[Workflow reference](introduction.md#iagrc-customer-and-staff-journey-v300) ·
[Role UX acceptance](UX_ROLE_REVIEW_2026-11-12.md)

## [2.17.0] — 2026-11-11

### Added

- Company profile tab and GRC profile-before-scope/questionnaire flow, separate from personal user profiles.
- Workbook-backed industry/sector catalogue, nationality-dependent CR/MISA, license validity/expiry and regulator responses with server and bilingual UI validation.
- Organization-authorized profile APIs, immutable submitted assessment profile snapshots and snapshot-only report context.
- GRC-scoped assessment-type backfill, profile child DocTypes, acceptance tests and project continuity records.

### Changed

- GRC draft scope confirmation, answer saves and submission require a complete organization profile; Internal Audit assessments bypass this requirement.
- Align Python, root and frontend package version metadata at 2.17.0.

Validation: 8 profile backend tests and 23 combined profile/scope browser tests passed for release. Earlier recorded checks include 20 scope/backend regressions, migration idempotency, catalogue parity and one real browser/database round-trip. Restricted department sharing remains pending. [Upgrade notes](RELEASE_v2.17.0.md).

## [2.16.2] — 2026-11-11

### Fixed

- Allow admins and managers to clear all mandatory sections by offering unmapped question-bearing sections as individual choices before configuration save.
- Display mandatory sections as gray, checked and disabled in package mappings and customer choices, with a Mandatory section label.
- Show per-section question counts and a deduplicated included-scope breakdown; retain existing published assessment snapshots and backend validation.

Validation: TypeScript/build, 10 browser scenarios and the backend optional-only confirmation regression passed. Lint: zero errors, three existing warnings. [Configuration and upgrade notes](AUDIT_PACKAGE_OPTIONAL_SECTIONS.md).

## [2.16.1] — 2026-11-11

## Documentation update - 2026-11-11

- Added five AlphaX-branded easy role PDFs, reproducible source, and a ZIP bundle with menu paths, steps, flowcharts and access boundaries. Documentation-only; app version remains 2.16.1.

### Fixed

- Align mobile header controls and wrapping action groups; keep table names/emails readable inside horizontally scrolling tables.
- Fix narrow-screen Help overflow, workspace-preference checkboxes, assessment-display spacing, onboarding consent/ownership controls, and milestone/action spacing.
- Style the signed-out demo access screen as a centered panel.

### Changed

- Customer assessment, Activity and dashboard views show only assessment start and submission dates. Detailed change events remain stored and available to authorized staff.
- Customer Help, contextual tour and bilingual PDF describe Assessment dates. Dashboard event selection filters milestones before limiting recent entries.
- Add repeatable disposable-site layout audit scripts and customer/staff history regression checks.

[Release notes](RELEASE_v2.16.1.md) · [Layout review](GRC_LAYOUT_REVIEW.md) · [Customer date flow](introduction.md#customer-assessment-dates-v2161).

## [2.16.0] — 2026-11-11

### Added

- Admin/manager template activation controls and independent defaults for Internal Audit and GRC, with audit history and stale-save protection.
- GRC-only migration preserving the previous active published default in its type.

### Changed

- All assessment choices show only active published templates, with Default labels. Management retains disabled templates for reactivation.
- Disabling or reclassifying a default clears its designation. Cloned drafts do not inherit defaults; existing assessments remain unchanged.
- Template and audit-package pages group checkbox options, guidance and action buttons with consistent spacing and mobile/RTL layouts.

[Release and upgrade notes](RELEASE_v2.16.0.md) · [Feature reference](introduction.md#template-availability-and-defaults-v2160).

## [2.15.1] — 2026-11-11

Send customer verification codes immediately instead of waiting for scheduled mail processing.

### Fixed

- Use Frappe's immediate SMTP delivery for signup, customer email-code sign-in and invited-customer verification, retaining native Email Queue delivery records and the configured outgoing account.
- Check the persisted send result; muted, suspended, missing-account and SMTP failures return a delivery error instead of a misleading success.
- Expire failed registrations and their unsent email records, including after native SMTP commits, so background retries cannot deliver a code from a failed attempt.
- Preserve code expiry, single-use verification, rate limits, invitation binding, Arabic content and MFA requirements.

[Release and validation notes](RELEASE_v2.15.1.md) · [Verification flow](introduction.md#immediate-verification-email-v2151).

## [2.15.0] — 2026-11-11

### Added

- Customer selection cards for Internal Audit and Governance, Risk and Compliance, with English/Arabic labels and responsive layouts.
- Administrator/manager template classification controls in Audit packages, with audit history and stale-save protection.
- Assessment-type filtering in template discovery and server validation of template/type agreement on creation.

### Changed

- Existing templates default to Internal Audit; GRC-site migration fills missing classifications without overwriting configured values.
- Existing assessments, scoring snapshots, released reports and API clients omitting the new optional type retain their prior behavior.

[Release notes](RELEASE_v2.15.0.md) · [Feature and workflow reference](introduction.md#assessment-type-selection-v2150).

## [2.14.1] — 2026-11-11

### Fixed

- Validate eligible customer signup fields before reserving email allowance, so form corrections do not exhaust the hourly verification limit.
- Atomically check and reserve the per-email cooldown and hourly allowance; rejected cooldown retries no longer consume another slot, and concurrent requests cannot both pass.
- Show the server's remaining wait on normal signup/email-code screens, prevent duplicate sends and preserve English/Arabic mobile layout.

### Changed

- Return `retry_after_seconds` with application rate-limit errors while retaining neutral account-eligibility responses and existing hourly/IP protections.
- Preserve existing counter expiries on upgrade and give legacy email counters without expiry a bounded lifetime.

[Release and validation notes](RELEASE_v2.14.1.md) · [Signup flow](introduction.md#signup-verification-retry-handling-v2141).

## [2.14.0] — 2026-11-10

### Added
- Immutable, questionnaire-linked audit package configurations with bilingual labels/descriptions, required sections, customer preview and confirmed assessment scope.
- Reasoned admin draft-scope corrections with concurrency protection, retained inactive responses/evidence and customer acknowledgement.
- Email-specific auditor onboarding invitations, server-owned attribution, cross-browser resume, milestone tracking, delivery states, blockers and manual reminder/resend/revoke actions.
- Default ownership locks, configurable invitation defaults and named staff exceptions; audited ownership transfers update active allocations and revoke previous access.
- A distinct manager guide, contextual Help and replayable tours, and four illustrated English/Arabic PDF guides.
- Scoped customer/auditor oversight and configurable approval workflows for onboarding, invitations, memberships and assignments.
- Bilingual public-site content and layout editing, authorized previews, ordered approval, immutable publication history and audit events.

### Changed
- Use confirmed scope consistently in question payloads, evidence validation, progress, scoring, gating, findings, improvement actions and PDF reports; omitted sections are marked Not assessed.
- Enforce ownership across customer data, files, exports, oversight and notifications; pending onboarding remains private to its inviter and GRC administrators.
- Preserve all-section behavior for legacy assessments, released reports and questionnaire versions without package configuration. Existing customers remain unlocked unless explicitly changed.

### Fixed
- Serialize invitation completion and scope/assignment updates with locking reads to prevent duplicate activation or stale decisions under concurrent requests.

[Release and upgrade notes](RELEASE_v2.14.0.md) · [Feature and workflow reference](introduction.md).

## [2.13.0] — 2026-11-08

### Added
- Independent fullscreen controls to hide/show section overview and progress without losing answers.
- Long-question scrolling regressions for desktop, narrow mobile and short landscape in fullscreen and normal mode.

### Fixed
- Keep questionnaire content at its natural height with vertical scrolling, wrapping long text and narrow answer grids.
- Normal-view section navigation brings questions into view.

[Release notes](RELEASE_v2.13.0.md).

## [2.12.1] — 2026-11-08

### Fixed
- Assessment creation hides inactive and unpublished templates for every role, including administrators.
- An inactive default no longer becomes a creation choice; an empty eligible list disables creation with a clear message.
- Template management and existing assessments retain access to historical versions.

[Release notes](RELEASE_v2.12.1.md).

## [2.12.0] — 2026-11-08

### Added
- Automatic customer questionnaire focus mode with optional native browser fullscreen on interaction.
- Normal view and Full screen controls preserve answers and remember the view per assessment and tab session.
- Browser coverage for fullscreen denial, unsupported browsers, Escape, native exit, mobile submission and role restrictions.

### Changed
- Surrounding navigation, reports, maturity panels and activity are hidden while answering in focus mode; staff and read-only views keep their normal presentation.

[Release notes](RELEASE_v2.12.0.md).

## [2.11.0] — 2026-11-08

### Added
- Default-hidden Overall Maturity visibility policy for customers and staff: Hidden, After assessment completion, or Completed sections only.
- Admin/manager controls in the portal Assessment display page and native GRC Staff Desk page; admins can also use GRC Settings directly.
- Permission, Desk save, completion, N/A, partial-section and aggregate-suppression regression coverage.

### Changed
- Enabled panels open automatically once eligible; the superseded expansion-default field is hidden but retained for compatibility.
- Section-only mode excludes unfinished sections and never shows an aggregate score.

[Release notes](RELEASE_v2.11.0.md).

## [2.10.0] — 2026-11-06

### Added
- Report color ranges editor for GRC administrators and GRC managers, supporting ten or more ranges, color picking, hex values, previews and default restoration.
- Validated color policy with inclusive lower bounds, automatic upper bounds, complete coverage, audit logging and stale-save protection.

### Changed
- Assessment bars and newly generated PDF bars/chart backgrounds use the saved policy.
- Report releases freeze their policy so historical UI/PDF colors remain consistent after later configuration changes.

[Release and validation notes](RELEASE_v2.10.0.md).

## [2.9.0] — 2026-11-06

### Added
- Shared section-percentage palette for frontend score bars and PDF reports: 100% blue, 75–<100% green, 50–<75% orange, below 50% red.
- Compact maturity/report disclosure rows with keyboard-accessible Expand/Collapse controls and visible section navigation on first opening.

### Changed
- Rounded report chart bars and questionnaire progress tracks.
- Upgrade the previous collapsed-until-complete overview default to visible tabs; retain explicit always-collapsed/hidden choices and all scoring timing controls.

### Fixed
- Section colors follow percentages independently of maturity labels; scores and classifications remain unchanged.

[Release and validation notes](RELEASE_v2.9.0.md).

## [2.8.0] — 2026-11-05

### Added
- Customer scoring timing and section overview visibility controls in GRC admin Settings.
- Edit-default-template revision flow with publication as the default for future assessments.
- Browser and integration coverage for final-answer visibility, admin overrides, and default-template revisions.

### Changed
- Summary, section chart/table, totals and scoring method flow onto one A4 page for the standard six-section assessment.
- Questionnaire comment/attachment defaults and missing inherited flags now default to disabled.

### Fixed
- Apply question-evidence restrictions to assessment endpoints while retaining action-evidence access.
- Match the exact reference ink, muted text, accent and five maturity colors without modifying scores or thresholds.

[Upgrade and validation notes](RELEASE_v2.8.0.md).

## [2.7.1] — 2026-11-04

### Fixed
- Verify shared authorized PDF content and inline/download disposition in backend and browser checks.
- Embed the original assessment font families for consistent reference-report typography across servers.
- Match landscape report margins, chart geometry, table alignment and summary sizing more closely to the approved PDF.
- Preserve font licenses and verify the same embedded fonts in PDF regression tests.

## [2.7.0] — 2026-11-04

### Added
- GRC admin controls for collapsed maturity/report sections and a default-off comments/evidence switch.
- Shared PDF preview and reference-based three-page landscape report.
- Playwright, policy, PDF and API regression coverage.

### Changed
- Hidden extras are omitted from answer saves; historical evidence and released PDFs remain intact.
- [Assessment presentation and report guide](GRC_ASSESSMENT_PRESENTATION.md).

# Changelog

[README](../README.md) · [Developer introduction](introduction.md)

This project follows Semantic Versioning and the Keep a Changelog categories. The imported 1.5.0 baseline is retained as a separate Git commit; earlier release details remain in the original source and README.

## [2.6.0] — 2026-11-02

Personal Help/tour visibility and workflow reliability fixes. [Release notes](RELEASE_v2.6.0.md).

### Added
- My profile → Workspace preferences: separate controls for the page-tour and Help buttons, saved per user across browsers and sign-ins.
- Default-visible English/Arabic controls for customers and staff; hiding the page tour also suppresses automatic tours.
- Four backend preference cases, two real browser journeys, ten native notification cases and three active-session MFA regressions.

### Fixed
- Assessment submission no longer sends the built-in Administrator user ID to native email-address validation. Notifications use validated enabled-user email addresses and retain the user identity for access and preference checks.
- Expected email-address/configuration failures are recorded without rolling back assessment submission; unexpected programming errors still propagate.
- Central policy changes and optional MFA enrollment explicitly end the initiating HTTP session so Frappe cannot restore it at request completion.

## [2.5.0] — 2026-11-02

Central GRC MFA policies with authenticator or email verification. [Release notes](RELEASE_v2.5.0.md) · [MFA administration and recovery](GRC_MFA_ADMINISTRATION.md).

### Added
- One administrator-controlled Enabled, Disabled or Enforced policy for all GRC users, with Authenticator app or Email code as the shared verification method.
- Password-confirmed optional enrollment/withdrawal, email readiness checks, audit logging and affected-session revocation.
- Native email challenge verification with expiry, account/password binding, policy revision checks, rate limits and single-use consumption.
- Integration and bilingual/mobile browser coverage for central configuration, optional enrollment, platform preservation and stale-policy races.

### Changed
- Existing role/account behavior remains active until the first explicit central save; central adoption then supersedes GRC overrides and closes legacy mutation APIs.
- Migration retains native secrets and the adopted method. Help, tours and bilingual downloadable guides describe central administration.

### Fixed
- Inherited All-role enforcement no longer prevents the intended GRC policy from being applied; former non-GRC coverage is preserved through an authentication-only role.
- User/enrollment and legacy policy writes recheck the current locked settings so stale requests cannot override central decisions.

## [2.4.0] — 2026-11-01

Configurable GRC role and account MFA policies, including administrator accounts. [Release notes](RELEASE_v2.4.0.md) · [MFA administration and recovery](GRC_MFA_ADMINISTRATION.md).

### Added
- Role-level MFA defaults and individual overrides in bilingual Account security, with password confirmation, audit logging and affected-session revocation.
- Administrator account MFA can be explicitly disabled or required; defaults remain unchanged until edited.
- Integration and browser coverage for role precedence, authorization, independent Frappe MFA requirements and administrator password-only sign-in.

### Changed
- Individual policies override role defaults; Required wins among conflicting GRC role policies. Separate Frappe MFA requirements continue to apply.
- The administrator guide, tour and recovery documentation describe the updated policies.

## [2.3.0] — 2026-11-01

Bilingual role guidance, downloadable illustrated guides and contextual page tours. [Release notes](RELEASE_v2.3.0.md).

### Added
- Customer, auditor and administrator guides in English and Arabic, with role-specific workflows, navigation and first-administrator setup.
- Three bilingual PDF guides with navigation illustrations and a repeatable generation script.
- Page-specific guided tours with contextual highlights and examples, first-visit display, replay, skip and an option to skip automatic tours.
- Browser coverage for role guides, PDF access, page tours, mobile layout and Arabic.

### Changed
- Workspace header exposes Help & guides and Take page tour. Tour completion and automatic-tour preference are stored per account in the current browser.

## [2.2.0] — 2026-10-31

Full-page questionnaire admin, customer-style preview, response/report policies, multi-select scoring and a live customer score.

### Added
- Full-page questionnaire template dashboard, create/edit routes and customer-style preview with live percentage and maturity band (replaces the modal editor).
- Per-questionnaire, per-section and per-question toggles for comments and attachments (question → section → template inheritance).
- GRC Settings controls for customer report PDF download, report email and Before Audit / After Audit timing, enforced in download and email APIs.
- Optional Multi selection mode on questions with Highest / Average / Sum (capped) scoring; answer rows store one or more selected letters.
- Live overall percentage and band on editable customer assessments while answers change.

### Changed
- Customer questionnaire chrome matches the requirement layout (section stepper, progress, A–D option cards with point labels).
- Assessment and template APIs expose resolved response flags, selection mode and scoring policy needed by the admin editor and live score.

### Fixed
- Report download and email respect admin policy timing instead of only checking UI visibility.

## [2.1.0] — 2026-10-30

Suggested score-to-maturity mapping for the 20-question assessment.

### Changed
- Default maturity bands are Critical 0–29%, Low 30–49%, Medium 50–69%, High 70–84% and Leading 85–100%.
- English and Arabic executive-summary conclusions follow the suggested scoring text for each mark.
- The scoring-method sentence prints those inclusive ranges. Answer points, questions and section weights are unchanged.
- Sites still on the previous default bands (0–34 / 35–54 / 55–74 / 75–89 / 90–100) are updated on migrate. Released GRC reports and custom bands stay as stored.

## [2.0.0] — 2026-10-26

Customer organizations, scoped staff workflows and assessment activity history. [Upgrade notes](RELEASE_v2.0.0.md) · [Task completion and skipped work](REQUIREMENTS_2026-10-26.md).

### Added
- Multiple organization memberships and per-organization roles, persistent portal organization switching, optional acyclic parent organizations and inherited subsidiary assessment reads.
- Explicit GRC Manager/Consultant roles, organization-scoped Manager assignments and a restricted staff Desk timeline.
- Staff-created organizations and pending customer-owned assessment drafts, Invite Customer Admin, audited answer entry and complete transfer history.
- Organization and user controls for optional reminders/status updates; mandatory verification, security, invitation and clarification emails bypass opt-outs.
- Customer activity summaries and detailed staff activity for answers, evidence uploads/deletions, status changes, assignments and transfers.

### Changed
- Customer identity requires GRC Customer; stale classification metadata or legacy customer roles alone remain restricted.
- Staff use System User accounts for the dedicated GRC Desk page while generic ERP/Desk routes and document APIs remain denied.
- Transfers of existing consultants, reviewers or customer owners require a reason; API callers must supply current team values and a reason when changing ownership.
- Optional email requires both organization and user permission; legacy overall user opt-outs remain effective.

### Fixed
- Registration offers visible sign-in/recovery and neutral guidance without asserting that an unsent code was sent.
- Verification resends enforce a 60-second server cooldown and display 15-minute expiry; queue failures have clear feedback.
- Tenant boundaries cover inherited reads, contributor list queries, report metadata and private files.
- Evidence deletion targets authorized attachments, retains historical/shared references and records the responsible actor.
- Internal review/transfer details are removed from customer timelines.

### Skipped
- Production mail-provider delivery timing, SPF/DKIM/DMARC and recipient spam investigation, at the user's request. Local queue/configuration findings remain documented.

Validation: 69 backend integration tests, 23 Chromium scenarios, both HTTP security suites, isolated migration, lint, TypeScript/build, syntax and diff checks passed.

## [1.10.0] — 2026-10-25

Dedicated signup with verified organization onboarding. [Upgrade notes](RELEASE_v1.10.0.md).

### Added
- Organization name and sector on the bilingual signup form; verified email becomes the organization contact.
- Pending registration metadata and transactional creation of a new organization plus Organization Admin membership after successful email verification.
- Safe fallback for existing organization names and pending invitations; no membership is granted from a matching name.

### Changed
- Hide Password/Email code tabs during signup while keeping both options on normal sign-in.
- Keep older verification links and API clients that omit organization fields on the existing authenticated organization setup flow.

## [1.9.1] — 2026-10-24

Backend MFA proof and password/name separation. [Upgrade notes](RELEASE_v1.9.1.md).

### Fixed
- Validate native authenticator challenges against the account, current password hash and native OTP secret before creating sessions; atomically consume successful challenges.
- Store server-validated MFA proof in native sessions. Require reauthentication for older unverified sessions and block API-token/OAuth bypasses for MFA-required GRC users.
- Reset GRC passwords using native proof and password policy without creating an authenticated session; revoke sessions and consume reset links.
- Enforce name/password separation on User document writes and password recovery as well as profile APIs; mask malformed or current-password name values in live identity responses, staff lists and login cookies.
- Submit profile, authenticator and login forms to backend validation without client-side verification gates.
- Preserve Administrator/ERP authentication and admin-controlled MFA policy.

## [1.9.0] — 2026-10-24

### Added

- Admin Account security page with per-customer/auditor Default, Required and Disabled MFA policies, admin password confirmation, audit history and active-session revocation.
- Protected User MFA policy and email-verification fields; migration to native per-account GRC Account MFA enforcement without rotating OTP secrets.
- Explicit verification-link confirmation screen and signup email action, with mailbox code verification retained as an alternative.

### Fixed

- Block the separate Frappe signup endpoint on GRC sites and reject unverified Guest User creation even if generic signup is re-enabled.
- Avoid silently redirecting an already-signed-in visitor from signup into their existing dashboard.
- Keep customer self-enrollment disabled when the admin disables MFA; preserve GRC app-admin MFA and other native role/site requirements.
- Add backend and real-browser coverage for verification links, signup-session confusion and customer/auditor MFA policy changes.

[Upgrade and admin instructions](RELEASE_v1.9.0.md).

## [1.8.0] — 2026-10-24

### Added

- Customer authenticator enrollment in Profile → Account security, backed by Frappe's native encrypted OTP secret and role-based login. Password reauthentication, expiring session-bound setup, code confirmation and session revocation protect activation.
- Admin signup policy: all valid emails by default, or an explicit exact-domain allowlist for new accounts.
- Read-only Frappe email diagnostics for outgoing accounts, scheduler/workers, muted/suspended sending and categorized queue failures.
- Email report action sends a secure authenticated report link to the requesting user's own email, using the site's standard outgoing Email Account and Email Queue.
- English/Arabic labels, access regressions and a real browser authenticator enrollment/login scenario.

### Fixed

- Separate personal details from security forms, identify autofill fields and validate names against malformed values and the user's current password.
- Display current safe owner names; mask malformed stored profile names until corrected. Existing frozen releases are preserved.
- Make PDF availability explicit before release and retain immutable, authorized PDF downloads after release. Released report API context now also uses the frozen snapshot.
- Apply the GRC signup policy independently of legacy organizational-email restrictions; recheck it when creating a verified account without locking out existing users.
- Avoid reporting a successful verification/report queue request when Frappe did not create an email queue record.

[Upgrade, customer setup and email troubleshooting](RELEASE_v1.8.0.md).

## [1.7.2] — 2026-10-24

### Fixed

- Classify the built-in Administrator as ERP before evaluating Frappe's synthetic all-roles list, preventing incorrect GRC staff MFA rejection.
- Preserve its ERP home and session classification while retaining normal Frappe authentication/MFA policy and administrative maintenance privileges.
- Keep separate GRC app admins and auditors under mandatory staff MFA and ERP isolation.
- Add real Administrator browser login coverage and backend regressions for classification, routing and staff boundaries.

[Upgrade and backend restart instructions](RELEASE_v1.7.2.md).

## [1.7.1] — 2026-10-24

### Fixed

- Allow Frappe usernames such as Administrator on password login by replacing email-only browser validation with an Email or username field (English/Arabic).
- Retain email validation for customer signup, email-code access and password recovery. Credentials, MFA and account routing remain server-controlled.
- Add browser regression coverage for Administrator submission and email-only flows; retain real customer/staff/ERP login tests.
- Make the bench-root working directory explicit in upgrade commands.

[Upgrade notes](RELEASE_v1.7.1.md).

## [1.7.0] — 2026-10-24

Reliable PDFs, a Saudi-inspired public journey and isolated ERP previews. [Upgrade notes](RELEASE_v1.7.0.md).

### Added

- Responsive green/sand landing page, accessible navigation, Arabic RTL, journey guidance and direct signup.
- Fictional read-only customer/auditor demo pages for ERP users and GRC admins.
- Browser coverage from a real queued verification email through organization setup, 20 questions, save/resume, assignments, review and released PDF.
- PDF regression coverage and guarded local-only email-code/assignment-cleanup helpers.

### Fixed

- Remove website-asset and letterhead dependencies from both IA PDF formats and legacy notification attachments.
- Use the shared WeasyPrint engine and embedded logos/fonts, correcting Arabic layout while preserving client/internal content and access checks.
- Preserve release gating and return the immutable private artifact through the standard PDF endpoint for GRC assessments.
- Support direct signup, refresh and return-to-sign-in through React.

### Changed

- Declare WeasyPrint 67.x; production must install its native text-rendering libraries.
- Document production upgrade and designated-site homepage activation.
- Other DocTypes/print formats retain Frappe's PDF implementation. Normal ERP login and site-scoped activation remain unchanged.

## [1.6.0] — 2026-10-24

Opt-in GRC platform with React workspaces, assigned-customer access and controlled assessment release. [Upgrade and release notes](RELEASE_v1.6.0.md).

### Added

- Doppio-scaffolded React/TypeScript/Vite/Tailwind frontend, Frappe React SDK, shared branded login, customer and auditor dashboards, and nested GRC administration.
- English/Arabic RTL interfaces, responsive navigation, public pages and tracked consultation requests.
- Protected portal account classification, staff MFA, customer-only email verification, organization onboarding, memberships, invitations and units.
- Multiple Consultant/Reviewer customer assignments, assessment team allocation, audit history and reassignment after revocation.
- Server-side ERP/tenant isolation across cookie and token authentication, generic APIs, documents and private files.
- Published immutable questionnaire/scoring versions, correction history, private evidence, frozen approved report release and Arabic-capable PDFs.
- Preliminary-scorecard/Status-only result policy, improvement actions with verified closure, follow-ups, reminders and delivery history.
- Styled shared dropdown popups, navigable dashboard cards and URL-preserved assessment filters.
- Self-service profile and password changes, with admin-controlled editable-field policy and server-side enforcement.
- GRC DocTypes, idempotent site setup, integration/browser/HTTP acceptance suites and guarded local provisioning/restore helpers.
- Developer architecture/workflow diagrams, acceptance matrix, operations guide and release instructions.

### Changed

- On GRC-enabled sites, route legacy assessment links into authorized React workflows and retain normal ERP destinations for separate ERP accounts.
- Use pinned assessment scoring/questionnaire snapshots and freeze report content at release.
- Replace automatic submission PDF emails in GRC mode with status-only workflow notices.
- Build portal assets through `bench build --app ia_maturity`; keep generated bundles and HTML entry points out of Git.
- Suppress live cross-customer benchmarks in GRC customer reports pending an approved versioned reference dataset.

### Fixed

- Prevent staff password recovery and password changes from bypassing MFA.
- Enforce revocation for subsequent record/file requests and expire affected queued tracked notifications.
- Preserve pending assessment edits during internal navigation and reject stale writes.
- Keep contributor action access independent from access to another respondent's assessment.
- Enforce profile restrictions even when clients manipulate fields or call APIs directly.
- Keep dropdown Escape handling within the menu before closing its parent dialog.

### Compatibility and status

GRC behavior requires explicit site activation. Legacy sites remain on their existing behavior when disabled; schema additions are additive. Enabling GRC changes that site's identity, routing and report-release contract, so existing legacy data needs reviewed migration mapping. This is a locally validated development release, with production and business acceptance gates still open.

## [1.5.0] — Imported baseline

Client-supplied IA Maturity source imported as commit `f527532`. Its original publication date is not asserted here. Includes the legacy bilingual questionnaire, scoring, verification, evidence, reports, actions, issue-based Q13 and benchmarking.
