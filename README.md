# AlphaX IA Maturity — Internal Audit Function Maturity Assessment

**AlphaX** product by **IRSAA Business Solutions** · Support: [erpsupport@irsaa.com](mailto:erpsupport@irsaa.com)

Built on Frappe / ERPNext (app name `ia_maturity`).

**Current version:** 3.2.0 · [Changelog](docs/CHANGELOG.md) · [v3.2.0 release notes](docs/RELEASE_v3.2.0.md) · [v3.0.0 release notes](docs/RELEASE_v3.0.0.md)

**DevOps: setting up or moving a GRC site?** Follow [GRC site setup and server migration](#grc-site-setup-and-server-migration), including the required site-specific `grc_enabled` setting.

Local performance validation passes for the documented 50-client read workload
using production-built, compressed assets. Public/login startup and portal routes
load separately; dashboards use bounded, authorized database reads and reuse
calculations only within a read operation. See the [local results](docs/PERFORMANCE_RESULTS.md),
[performance operations and DevOps commands](docs/PERFORMANCE_OPERATIONS.md) and
[architecture reference](docs/introduction.md#performance-with-workflow-preservation).
Synthetic local evidence does not certify the moved server or real-user timings.

New in 3.2.0: colour themes (IRSAA default), configurable assessment types, admin screen layouts (Standard and Compact company profile), role-based report access with a Reports page for managers, and a direct start after choosing the assessment type. See the [release notes](docs/RELEASE_v3.2.0.md).

Fixed in 3.1.2: customer email-code sign-in and staff 2FA sign-in work on current Frappe v15/v16, fresh installs get a default Internal Audit template, approved onboarding requests complete, and the A4 report fits one page. All 309 tests pass on v15 and v16. See the [release notes](docs/RELEASE_v3.1.2.md).

Fixed in 3.1.1: verification-limit switches now save, staff administration shows its validation messages, and the app installs and renders PDFs on current Frappe v15/v16 (WeasyPrint 70). See the [release notes](docs/RELEASE_v3.1.1.md).

New in 3.1.0: GRC admins manage customer verification rate limits, organization yes/no presentation and defaults for new users' guides and tours. Assessments show and link missing questions, and the initial audit type is selected once. See [admin controls and assessment guidance](docs/introduction.md#admin-controls-and-assessment-guidance-v310).

New in 3.0.1: a Frappe user with no GRC role goes directly to Desk at `/app/home`. See [Normal ERP Desk access](docs/introduction.md#normal-erp-desk-access-v301).

New in 3.0.0: the IA/GRC journey includes OTP-only customer access, department-bound invitations and permissions, the exact GRC46 instrument, mandatory GRC profile and selected scope, immediate preliminary results/PDF, registered-customer PDF attachments, and manager-approved additional audit access. Staff have a direct custom workspace, optional next-step guidance and default-off 2FA with admin role/username overrides. See the [workflow architecture](docs/introduction.md#iagrc-customer-and-staff-journey-v300), [demo runbook](docs/DEMO_JOURNEY.md), [eight-role UX validation](docs/UX_ROLE_REVIEW_2026-11-12.md) and [task progress](docs/PLAN_PROGRESS.md). This is a breaking customer-authentication and staff-entitlement upgrade; follow the release notes before rollout. Local validation is complete for the requested demo flow; business UAT and production deployment remain separate. Real inbox delivery is deferred until live deployment at the user's request.

Customer/staff release: [2026-10-26 requirements, completed tasks, validation and skipped work](docs/REQUIREMENTS_2026-10-26.md).

## GRC portal implementation

The GRC extension adds one React login, customer and auditor dashboards, app administration, customer-to-auditor assignments, tenant/ERP isolation and a controlled review/report-release workflow. It is enabled only on the designated site with `grc_enabled`.

Features include immutable questionnaire/scoring versions, private evidence and report release, bilingual RTL workflows, consistent dropdowns, dashboard cards that open related records, and profile self-service with admin-controlled fields. Customers use email OTP; staff retain password/MFA controls. The GRC frontend is built with React + TypeScript + Vite + Tailwind and lives entirely in this app.

### GRC site setup and server migration

**Installing the app or restoring its database does not enable GRC.** Every intended GRC site must have `"grc_enabled": 1` in its site configuration. This applies to new sites, sandbox copies and sites moved to another server. Enable it only on the designated GRC site, without a bench-wide `--global` setting.

Run commands as the bench owner from the bench directory. Replace `YOUR_GRC_SITE` with the actual site directory name under `sites/` and `https://your-grc-domain.example` with its public HTTPS URL.

1. **Prepare the bench and site.** Install the chosen app revision and its Python/native PDF dependencies using the [current release procedure](docs/RELEASE_v3.0.0.md#deployment-procedure). Use Node 24 for the frontend. On a new Frappe site, install the app once:

   ```bash
   bench --site YOUR_GRC_SITE install-app ia_maturity
   ```

   For a restored site, ensure the matching app code is present on the new bench and confirm installation with `bench --site YOUR_GRC_SITE list-apps`. Follow the restore/upgrade procedure for that revision.

2. **Activate GRC before migration, then build and clear caches.** The app's GRC setup/migration hooks are gated by this setting; installing the app alone is insufficient.

   ```bash
   bench --site YOUR_GRC_SITE set-config grc_enabled 1
   bench --site YOUR_GRC_SITE set-config host_name https://your-grc-domain.example
   bench --site YOUR_GRC_SITE migrate
   npm --prefix apps/ia_maturity/grc ci
   npm --prefix apps/ia_maturity/grc run build
   bench build --app ia_maturity
   bench --site YOUR_GRC_SITE clear-cache
   ```

   Restart web and worker processes through the deployment's normal service manager or hosting platform. Use `bench restart` where the bench's process manager supports it. Generated frontend assets are not committed and must be built on the destination bench.

3. **Preserve site configuration when moving servers.** Back up and restore the database, public/private files and the original encryption key through the [operations restore procedure](docs/GRC_OPERATIONS.md#backups-and-restoration). A database-only restore does not carry `sites/YOUR_GRC_SITE/site_config.json`. Explicitly restore or reapply `grc_enabled`, update `host_name`, and retain the original encryption key so existing encrypted credentials, including Email Account passwords, remain readable. Adapt database connection settings to the new server; keep configuration and secrets outside Git. Confirm DNS/reverse-proxy routing serves the intended site.

4. **Configure mail and access.** Configure the normal default outgoing Frappe **Email Account** and verify actual OTP inbox delivery before customer testing. Customers require an email code on every sign-in; invitation/report jobs also need the normal workers and scheduler. Review site email muting/suspension for the destination environment; keep local test sites muted. Provision a separate **GRC App Admin**, configure staff department memberships and assignments, and review Account security. Staff 2FA defaults to Disabled; preserve explicit policies and normal ERP MFA requirements. See [operations](docs/GRC_OPERATIONS.md#production-activation) and [MFA administration](docs/GRC_MFA_ADMINISTRATION.md).

5. **Verify the destination site.** Run the read-only configuration check:

   ```bash
   bench --site YOUR_GRC_SITE execute ia_maturity.grc.health.check
   ```

   Confirm `checks.grc_enabled` is `true` and review each remaining check; the report also includes business/content approval and security settings. Open `/grc-site`, customer login at `/login`, and staff/ERP password login at `/login?staff=1`. Verify GRC staff reach `/grc/auditor`, customers reach their customer workspace after email verification, and users without GRC roles retain normal ERP access. Test a PDF and real email delivery separately; a working landing page does not prove those services work.

#### Troubleshooting: “GRC is not enabled on this site.”

If the landing page raises `frappe.exceptions.DoesNotExistError: GRC is not enabled on this site.` from `ia_maturity/www/grc.py`, the active site's `grc_enabled` setting is missing or false. A restored database may still point the website home page to `grc-site` while the new server lacks that site setting. The same guard applies to the GRC page and public landing page.

Apply the setting to the site actually serving the hostname, rerun the gated migration and clear its cache:

```bash
bench --site YOUR_GRC_SITE set-config grc_enabled 1
bench --site YOUR_GRC_SITE migrate
bench --site YOUR_GRC_SITE clear-cache
```

Restart the web processes, then reload the landing page. If the error remains, check the hostname-to-site mapping and confirm the running processes use the bench/site you updated. This error indicates site activation, independently of SMTP delivery or user roles. Keep the activation guard in place.

New in 2.17.0: reusable Company profile with industry/sector, nationality/CR, licenses and regulators, bilingual validation, GRC assessment readiness checks, and immutable submitted profile snapshots. Internal Audit bypasses this profile gate. See [setup and upgrade notes](docs/RELEASE_v2.17.0.md); restricted department sharing remains future work.

Fixed in 2.16.2: all sections can be optional, with individual choices automatically offered outside custom packages. Mandatory sections are gray and locked in customer choices; per-section question counts and totals count overlaps once. See the [setup guide](docs/AUDIT_PACKAGE_OPTIONAL_SECTIONS.md).

Fixed in 2.16.1: consistent mobile workspace headers, readable scrolling tables, Help-page wrapping, and spaced settings/onboarding controls. Customers see only assessment start and finish dates; detailed activity remains stored and visible to authorized staff. See the [layout review](docs/GRC_LAYOUT_REVIEW.md).

New in 2.16.0: admins and GRC managers can disable templates (including defaults) and choose separate defaults for Internal Audit and GRC. Assessment choices show only active published templates with Default labels. Template and audit-package controls have grouped options, spaced actions and mobile/RTL layouts. See the [configuration guide](docs/GRC_ASSESSMENT_TYPES.md) and [developer introduction](docs/introduction.md#template-availability-and-defaults-v2160).

Fixed in 2.15.1: customer verification codes send immediately through the configured outgoing email account, without waiting for the scheduler or a background worker. Failed or suspended sends return an error and invalidate the failed attempt. See [delivery and upgrade notes](docs/RELEASE_v2.15.1.md).

New in 2.15.0: customers choose Internal Audit or Governance, Risk and Compliance before selecting a questionnaire. Administrators and GRC managers classify published templates in Audit packages; the dropdown and creation API enforce the chosen type. See the [assessment type guide](docs/GRC_ASSESSMENT_TYPES.md).

Fixed in 2.14.1: normal customer signup validates fields before reserving email allowance, and premature retries no longer exhaust the hourly allowance. A server-provided countdown explains when signup or email-code requests may resume. The five-per-email/hour and 30-per-IP/hour limits remain enforced. See [signup recovery and upgrade notes](docs/RELEASE_v2.14.1.md).

New in 2.14.0:

- Versioned audit packages with bilingual customer choices, required sections, confirmed scope and consistent scoring/report coverage.
- Auditor-owned customer invitations, private onboarding progress, manual reminders and admin-controlled ownership locks and exceptions.
- Dedicated manager guidance, contextual Help/tours and four bilingual PDF guides.
- Customer/auditor oversight and configurable operational approvals, plus a bilingual website editor with approved publication and audit history.

See the [audit packages and onboarding guide](docs/GRC_AUDIT_PACKAGES_ONBOARDING.md), [customer oversight guide](docs/GRC_CUSTOMER_OVERSIGHT.md) and [release/upgrade notes](docs/RELEASE_v2.14.0.md). Existing assessments and released reports keep their scope; existing customers are not retroactively locked.

Staff password login accepts Frappe email addresses or usernames, including Administrator. Staff 2FA is disabled by default. GRC app admins use Account security to choose a global default (Enabled, Disabled or Enforced), a verification method (Authenticator app or Email code), and role or individual username overrides. Individual Required/Disabled overrides roles; Required wins among multiple roles; roles override the global default. Enabled permits optional enrollment; Enforced requires staff 2FA by default. Explicit existing settings and unrelated ERP MFA coverage are preserved. Customers always use email OTP, with no password option. The built-in Administrator retains normal Frappe authentication and ERP access.

New in 2.6.0: per-user page-tour and Help visibility in My profile → Workspace preferences, reliable assessment notifications, and complete sign-out when MFA settings change. See the [release and upgrade notes](docs/RELEASE_v2.6.0.md).

New in 2.5.0: central Enabled, Disabled or Enforced MFA, with Authenticator app or Email code, optional profile enrollment and preserved non-GRC coverage. See the [release and deployment notes](docs/RELEASE_v2.5.0.md).

New in 2.4.0: MFA policies by GRC role or individual account, including app administrators. See the [MFA administration and recovery guide](docs/GRC_MFA_ADMINISTRATION.md).

New in 2.3.0: bilingual role guides, illustrated PDF downloads and replayable page-specific tours. See the [release notes](docs/RELEASE_v2.3.0.md).

New in 2.2.0:
- Full-page template dashboard, editor and customer preview with live scoring (no modal editor).
- Comment and attachment enablement per questionnaire, section and question; GRC Settings for report download/email and Before/After Audit timing.
- Optional multi-select questions (Highest / Average / Sum capped) and a live customer score while answering.
- Questionnaire UI aligned to the requirement layout (section stepper, progress, A–D cards).

New in 2.1.0: default maturity bands are Critical 0–29%, Low 30–49%, Medium 50–69%, High 70–84% and Leading 85–100%, with matching English and Arabic conclusions in the executive summary. Points stay A=25, B=50, C=75, D=100. Migrate updates the previous default bands; released GRC reports and custom bands are left unchanged.

New in 2.0.0:
- Multiple organization memberships, a persistent organization switcher and read-only holding-company access to subsidiary assessments.
- Separate customer/staff identity controls, direct custom staff workspace with optional getting-started guidance, and verification resend with cooldown and expiry.
- Staff-created customer organizations and drafts, customer-admin invitations, audited answer entry and consultant transfers with mandatory reasons.
- Organization/user optional-email preferences and separate customer/staff activity timelines.

Review the [v2 upgrade requirements](docs/RELEASE_v2.0.0.md) for customer roles, transfer API callers and deployment steps.

New in 1.10.0: a dedicated signup form without sign-in tabs, organization name and sector collection, and organization creation after email verification. Existing organizations still require an invitation. See the [signup upgrade guide](docs/RELEASE_v1.10.0.md).

Fixed in 1.9.1: backend validation of single-use MFA challenges and session proof, recovery without automatic login, and password/name protection across profile, User records and live identity displays. See the [security upgrade guide](docs/RELEASE_v1.9.1.md).

New in 1.9.0: explicit signup verification links and confirmation, protection against alternate unverified signup paths, and per-account MFA controls for GRC admins. See the [identity controls upgrade guide](docs/RELEASE_v1.9.0.md).

New in 1.8.0: customer authenticator enrollment using Frappe native MFA, protected personal-name editing, admin-controlled signup domains (all valid emails by default), standard Frappe email diagnostics, and secure report-link email with visible PDF release controls. See the [upgrade and email setup guide](docs/RELEASE_v1.8.0.md).

New in 1.7.0: a Saudi-inspired bilingual landing page with direct signup, fictional customer/auditor previews for ERP users, and self-contained Arabic-capable PDF downloads independent of website asset URLs. See the [production upgrade checklist](docs/RELEASE_v1.7.0.md).

### Website content and approvals

Authorized GRC users can edit English and Arabic public-site text in **Website content**. GRC administrators assign existing editor and approver roles and configure ordered approval steps; published content changes only after approval. See [website content and approvals](docs/GRC_SITE_CONTENT.md) for setup, preview, audit history and deployment.

### User help and guided tour

Signed-in users can open **Help & guides** in the workspace header for role-specific English and Arabic instructions, a guided tour, and a bilingual PDF download. Managers receive a dedicated manager guide and can also read auditor guidance; GRC app administrators can select all four role guides. The PDFs use demonstration illustrations; actual menus and available actions depend on access and settings.

Each page also offers **Take page tour** in the header. The contextual tour opens on the first visit to a page for each signed-in account in that browser; users may skip the page, skip future automatic tours, or replay any page manually. Tour progress and the automatic-tour choice are stored in that browser only. Each user can separately hide or restore the tour and Help buttons under **My profile → Workspace preferences**; this visibility preference is saved on the account across browsers. Hiding the page tour also stops automatic tours. Page-specific bilingual text and examples live in `grc/src/pageTourContent.ts`.

The shared guide text lives in `grc/src/guide-content.json`. After updating it, regenerate the four checked-in PDF assets with `cd grc && node scripts/build-guides.mjs` (Node 24, installed Playwright Chromium, and Arabic fonts are required), then rebuild the frontend with `npm run build`. The administrator guide includes site activation and first-admin setup; operators should also follow the current release and operations guides.

### Documentation

| Guide | Read this for |
|---|---|
| [Performance measurement and rollout](docs/PERFORMANCE_OPERATIONS.md) | Repeatable local baseline/load/browser checks, safe caching, destination diagnostics and rollback |
| [v2.15.1 release notes](docs/RELEASE_v2.15.1.md) | Immediate verification delivery, failure handling and validation |
| [Assessment types](docs/GRC_ASSESSMENT_TYPES.md) | Customer selection and admin/manager template classification |
| [v2.15.0 release notes](docs/RELEASE_v2.15.0.md) | Classification defaults, migration and validation |
| [v2.14.1 release notes](docs/RELEASE_v2.14.1.md) | Signup retry correction, remaining-wait countdown and preserved rate limits |
| [v2.14.0 release notes](docs/RELEASE_v2.14.0.md) | Audit packages, auditor onboarding, ownership, approval workflows and upgrade defaults |
| [Audit packages and onboarding](docs/GRC_AUDIT_PACKAGES_ONBOARDING.md) | Scope selection, scoring, invitation tracking, access controls and recovery |
| [Customer and auditor oversight](docs/GRC_CUSTOMER_OVERSIGHT.md) | Scoped portfolio reports, operational approval policies and requests |
| [v2.6.0 release notes](docs/RELEASE_v2.6.0.md) | Personal Help/tour controls, assessment notifications and MFA sign-out fixes |
| [v2.5.0 release notes](docs/RELEASE_v2.5.0.md) | Central MFA, email/authenticator methods and live upgrade |
| [v2.4.0 release notes](docs/RELEASE_v2.4.0.md) | MFA role policies, individual overrides and deployment |
| [v2.3.0 release notes](docs/RELEASE_v2.3.0.md) | Bilingual guides, tours and deployment |
| [Developer introduction](docs/introduction.md) | Architecture, DocType relationships, workflow diagrams and API/source map |
| [Development and acceptance criteria](docs/DEVELOPMENT.md) | Extension rules, test coverage, remaining business and deployment criteria |
| [Implementation notes](docs/GRC_IMPLEMENTATION.md) | Delivered behavior, dashboard/profile controls and local validation |
| [Website content and approvals](docs/GRC_SITE_CONTENT.md) | Bilingual editing, role access, publication and audit |
| [MFA administration and recovery](docs/GRC_MFA_ADMINISTRATION.md) | Central policy, email/authenticator methods, access recovery and deployment |
| [Operations](docs/GRC_OPERATIONS.md) | Build, local preview, services, backups and restoration |
| [v1.10.0 release notes](docs/RELEASE_v1.10.0.md) | Dedicated signup and verified organization onboarding |
| [v1.9.1 release notes](docs/RELEASE_v1.9.1.md) | Backend MFA enforcement, password/name separation and deployment checks |
| [v1.9.0 release notes](docs/RELEASE_v1.9.0.md) | Verified signup, admin MFA controls, migration and acceptance |
| [v1.8.0 release notes](docs/RELEASE_v1.8.0.md) | Authenticator enrollment, profile correction, signup policy, email troubleshooting and report delivery |
| [v1.7.0 release notes](docs/RELEASE_v1.7.0.md) | PDF fix, dependencies, designated-site activation and journey verification |
| [v1.6.0 release notes](docs/RELEASE_v1.6.0.md) | Installation, first administrator, migration and rollback |
| [Changelog](docs/CHANGELOG.md) | Version-by-version changes |

For GRC installation, follow the release notes above before the legacy instructions below. Node 24 and a frontend build are required; generated assets are not committed. Local preview: http://localhost:8005/login. Production activation still requires the documented business, content and operational acceptance gates.

**The sections below describe the imported legacy app.** In GRC mode, React workflows and the server-side access policy replace the legacy public portal, Desk review and automatic PDF-email behavior. The GRC implementation was validated on Frappe 15.118.0 / ERPNext 15.119.3; the legacy compatibility claims below do not certify GRC on Frappe 16.


A Frappe app that turns the *IA Maturity Assessment (20 Questions / 6 Sections)* workbook into a working system:
respondents fill it in on a web portal, the server scores it, a PDF report is produced, improvement actions are
created automatically and reviewers approve the result in the desk.

* **Frappe:** version 15 **and** version 16 (tested on 15.123 and 16.52). ERPNext is **not** required; the app works on
  ERPNext sites too.
* **Python:** 3.10 – 3.12 on Frappe v15; 3.14 on Frappe v16 (v16 requires Python 3.14 and Node 24)
* **Licence:** MIT · © 2026 IRSAA Business Solutions (AlphaX)

---

## 1. What you get

| Area | What it does |
|---|---|
| **Public landing page** `/ia-assessment` (signed-out visitors) | Branded, bilingual (English / Arabic, RTL) page that explains the assessment and collects the respondent's details – work e-mail, name, job title, perspective, organisation, date, report language and privacy consent. A 6-digit code (and one-click link) is e-mailed; entering it creates the account, signs the person in and opens a pre-filled draft at Section 1. Returning users choose *Continue / view results*. No passwords. |
| **Respondent portal** `/ia-assessment` (signed in) | Login-protected page. Respondents start an assessment, answer section by section (autosaved to the server), add comments and attach evidence files, submit, then see the full results report and download the PDF. |
| **Scoring engine** (server side) | A=25 · B=50 · C=75 · D=100; section % = points ÷ (applicable questions × 100); overall % = total points ÷ total possible. Default bands: Critical 0–29%, Low 30–49%, Medium 50–69%, High 70–84%, Leading 85–100%. Points and bands are configurable. Adds *Not applicable* answers and *gating questions*. |
| **Client and internal reports** | Two PDFs from one design. **IA Maturity Report** (client) contains only the sections enabled in *Settings > Client Report Content* — by default 01 Executive summary, 02 Results by section, 03 Peer benchmark. **IA Maturity Internal Report** (IRSAA) always contains everything and carries an *INTERNAL – not for distribution* banner; only IA Maturity staff can open it. The portal shows clients the client report only, and data of hidden sections is never sent to their browser. |
| **PDF report contents** | Executive summary, maturity scale, section bar chart (server-rendered SVG), section table, key findings, improvement roadmap (next-level practice, owner, timeframe), detailed responses, review comments, scoring method. |
| **Improvement actions** | On submission, one *IA Maturity Action* is created per A/B answer (optionally C too) with priority, due date (A: 90 days, B: 180, C: 365), owner role and the next-level practice as the recommended action. Track status, assignee and closure evidence. |
| **Review workflow** | Submitted assessments go to *Pending Review*. Reviewers use *Review → Reviewed / Approved* (with comments; reviewer and timestamp recorded). Reviewers cannot change answers. Managers can *Return to Respondent* for correction. |
| **Notifications** | Submission e-mail to the administrator mailbox (and optionally the respondent) with section scores and the PDF attached. |
| **Analytics** | Script report *IA Maturity Scores*: every assessment with section columns, or averaged **by entity** or **by respondent perspective** (perception gap between CAE, Audit Committee, management…), with chart and summary cards. |
| **Workspace** | *IA Maturity* desk workspace with shortcuts, pending-review and open-action counters. |
| **Seed data** | The 20 questions, 6 sections, framework references and owners from the workbook are loaded on install, in English **and Arabic**. |
| **Arabic / right-to-left** | One-click English ⇄ العربية switch in the portal (full RTL layout, Arabic questions, answers, guidance and report). The PDF report is produced in the assessment's *Report Language* with the bundled Noto Sans Arabic font, so Arabic renders on any server. |
| **Q13 from the issue register** | *IA Audit Issue* register (or any DocType you point it at). Q13 "average time to close audit issues" is calculated from issues closed in the last 24 months, locked for respondents and explained in the portal and report. Falls back to a manual answer when there are fewer than 5 closed issues. |
| **Anonymous peer benchmarking** | Portal and PDF show the entity's percentile, the peer median and the middle 50 % of peers for the overall score and each section, compared with the latest submitted assessment of every other entity. Hidden until at least 5 peer entities exist; never shows peer names, minimum or maximum. Staff get the *IA Maturity Benchmark* report. |

## 2. Installation

For the GRC portal, complete [GRC site setup and server migration](#grc-site-setup-and-server-migration) above as well. The legacy installation commands below do not activate GRC.

### On a bench you manage

```bash
cd ~/frappe-bench
# from the application repository:
bench get-app https://github.com/AlphaX-SAAS/ia_maturity.git
# …or from the zip: unzip into apps/ then
#   ./env/bin/pip install -e apps/ia_maturity && echo ia_maturity >> sites/apps.txt

bench --site <your-site> install-app ia_maturity
bench --site <your-site> migrate
bench build --app ia_maturity
bench restart            # production (supervisor / systemd)
```

### Frappe Cloud
Push the folder to a GitHub repository, add it as a custom app in your Frappe Cloud bench group (v15 or v16),
deploy, then install it on the site.

### After installing — 5-minute setup

1. **IA Maturity Settings** (desk → search "IA Maturity Settings")
   * *Notify on Submission*: the administrator mailbox (e.g. the CAE or practice-lead address).
   * Check the points and maturity bands (defaults are the suggested 0–29 / 30–49 / 50–69 / 70–84 / 85–100 scale).
   * Optional: *Require Evidence For Answers At* = "C and D" to stop unsupported high scores.
   * Optional: *Allowed Email Domains* to limit who can respond.
2. **Outgoing e-mail**: set up a default outgoing **Email Account** (Tools → Email Account). Without one,
   submissions still work but no e-mail is sent (an Error Log entry is written).
3. **Site host name** (needed for PDF generation in background jobs and correct links in e-mails):
   `bench --site <site> set-config host_name https://your.domain`
4. **Give people access** (see section 5).
5. Open `/ia-assessment` and try it.

## 3. Frappe v15 / v16 compatibility

One codebase installs on both versions (`frappe >=15,<17`). Version differences are handled in `ia_maturity/compat.py`:

| Topic | v15 | v16 | How the app handles it |
|---|---|---|---|
| Desk URL | `/app/...` | `/desk/...` (old `/app` links redirect) | Links built with `get_url_to_form` / `compat.desk_base()` |
| Permission hooks | `None` = no opinion | any falsy result = **deny** | `has_permission` hook returns `True`/`False` explicitly |
| Workspace | no `type` field | `type` required, new sidebar & desktop | Workspace JSON carries `type: Workspace`; v16 builds the sidebar and shows the AlphaX tile on the desktop automatically |
| Test base class | `FrappeTestCase` | `IntegrationTestCase` | Tests import whichever exists |
| `in_test` flag | `frappe.flags.in_test` | `frappe.in_test` | `compat.in_test()` |
| PDF engine | wkhtmltopdf | wkhtmltopdf by default (Chrome/WeasyPrint optional) | Print format is wkhtmltopdf-friendly (tables, inline SVG, embedded logos) |

Installing on v16:
```bash
bench init --frappe-branch version-16 --python python3.14 frappe-bench   # Node 24 required
cd frappe-bench && bench get-app <repo-url-or-path>
bench --site <site> install-app ia_maturity
```

## 4. Branding (AlphaX / IRSAA)

| Surface | Branding |
|---|---|
| Respondent portal | AlphaX header bar (mark + wordmark), AlphaX favicon, IRSAA blue accents, footer "AlphaX IA Maturity · a product of IRSAA Business Solutions · erpsupport@irsaa.com" with the IRSAA logo |
| PDF report | AlphaX logo and IRSAA-blue rule in the header; repeating footer on every page with the IRSAA logo, product/company/support line, entity, reference and *Page x of y* |
| Submission e-mail | AlphaX logo header, IRSAA-blue button, IRSAA signature line; subject starts with "AlphaX \|" |
| Desk | AlphaX mark as the desk logo (`app_logo_url`), *AlphaX IA Maturity* tile on `/apps` (staff only), AlphaX header on the workspace and on the score panel |

Brand colours (sampled from the supplied logos): AlphaX black `#181818`, IRSAA blue `#12506E`.
All names, colours and contact details live in `ia_maturity/branding.py`; logo files are in
`ia_maturity/public/images/`. Replace those to re-brand — no other code changes needed.

> **Desk logo is site-wide.** `app_logo_url` makes the AlphaX mark the navbar logo of the whole desk on the site where
> the app is installed (replacing the ERPNext/Frappe logo). Remove that line from `hooks.py` if you don't want this.

> **PDF footer needs the patched wkhtmltopdf** (0.12.6 "with patched qt"), which is the standard Frappe production
> install. Distribution packages (`apt install wkhtmltopdf`) ignore PDF headers/footers. Check with
> `wkhtmltopdf --version`.

## 5. Roles and access

| Role | Who | Can |
|---|---|---|
| **IA Assessment Respondent** (portal role, no desk) | Client CAE, Audit Committee members, managers | Create, answer, submit and print **their own** assessments; see actions raised from them. |
| **IA Maturity Reviewer** | Engagement reviewers | Read all assessments, set review status/comments, update actions, run reports. |
| **IA Maturity Manager** | Practice lead / administrator | Everything, including templates, settings, entities, cancel/amend. |

**Adding respondents**
* *Self sign-up*: enable sign-up in Website Settings. With *Auto-assign Respondent Role on Sign-up* ticked,
  people who register themselves (from allowed domains) get the respondent role automatically. Users created by an
  administrator never get it automatically — add the role yourself (this keeps staff accounts clean).
* *Invite*: create a **Website User** and add the role *IA Assessment Respondent*.
* *Restrict to one client*: add a **User Permission** for the user on *IA Maturity Entity* = that client. The
  portal then only offers that entity.

Respondents can register a new entity from the portal (turn off with *Respondents Can Register a New Entity*).
If the entity name already exists and the user has no access to it, they are asked to contact the administrator.

## 6. Day-to-day use

**Respondent:** log in → `/ia-assessment` → *Start assessment* (entity, perspective, job title, date) → answer six
sections (progress is saved automatically; leave and come back any time) → *Submit and generate report* →
*Download PDF report*.

**Staff (desk):**
* *IA Maturity Assessment* list shows review status; the form shows the score panel, answers, section scores.
  Staff can also fill in an assessment on someone's behalf directly in the desk grid.
* Buttons: *Open in Portal*, *Report PDF*, *View → Improvement Actions*, *Review → Reviewed / Approved* (asks for a
  comment).
* *Review → Return to Respondent* (Managers): asks what to correct, cancels the submission and gives the respondent an
  amended draft with all answers kept; the reviewer's note is shown at the top of their questionnaire.
* *IA Maturity Action*: assign owners, track status; overdue actions show red in the list.
* *IA Maturity Scores* report: filter by entity/template/date; *Group By → Respondent Perspective* for a
  perception-gap view.

**Changing the questionnaire:** edit *IA Maturity Template* or use *New Version* on the template form. Every answer
row stores a snapshot of the question and option text, so editing a template never changes submitted assessments.

## 7. Scoring rules (as implemented)

* Points per answer: Settings (default A 25, B 50, C 75, D 100). D is the maximum.
* **N/A** (only where *Allow 'Not Applicable'* is ticked on the question — Q20 in the seed) is excluded from the
  denominator.
* Section % = section points ÷ (applicable questions × max points), rounded to 1 decimal.
* Overall %:
  * *Points (each question equal)* — default, identical to the workbook (sections with 4 questions weigh more), or
  * *Section Weights* — weighted average of section % using the template's section weights.
* Level = highest band whose minimum ≤ score.
* **Gating:** a gating question answered at its trigger level caps the *overall level* (the score is unchanged and
  the report explains the cap). Seed: Q1 (independence) answered A caps the overall level at *Low*.
* Submission requires every question to be answered (and evidence, if configured).

> Design note: the workbook's scale can never go below 25 % (all A = 25 %). If you prefer a 0–100 range, set the
> points to A 0 · B 33.33 · C 66.67 · D 100 in Settings and review the band thresholds — no code change needed.

## 8. Data model

| DocType | Type | Purpose |
|---|---|---|
| IA Maturity Settings | Single | Points, bands, rules, notifications, portal options |
| IA Maturity Band | Child | Maturity band (name, min %, colour, interpretation) |
| IA Maturity Template | Master | Versioned questionnaire; child tables *Template Section* and *Template Question* |
| IA Maturity Entity | Master | Organisation being assessed (sector, CMA-listed, regulators) |
| IA Maturity Assessment | Submittable | Header, answers (*Assessment Answer*), scores (*Section Score*), review fields |
| IA Maturity Action | Transaction | Improvement action raised from an A/B(/C) answer |
| IA Audit Issue | Transaction | Audit-issue register (raised / closed dates) used to calculate Q13 |

## 9. Code map

```
ia_maturity/
├── compat.py                Frappe v15 / v16 differences (desk URL, test flag)
├── branding.py              AlphaX / IRSAA names, colours, logos (single place to re-brand)
├── hooks.py                 install hooks, portal menu, permission hooks, jinja helpers
├── install.py               roles, default settings, seed template (setup_data/iia_gias_20q*.json, Arabic in *_ar)
├── scoring.py               pure scoring engine (used everywhere)
├── report_data.py           report context (English / Arabic) + server-side SVG chart + embedded Arabic font
├── i18n.py                  English / Arabic report strings, level names, bidi helper
├── issues.py                issue-register statistics and Q13 auto-calculation
├── benchmark.py             anonymous peer benchmarking (quartiles, percentile, minimum-peer rule)
├── patches/v1_3/            upgrade patch: Arabic seed text, new settings defaults
├── api.py                   whitelisted portal API (bootstrap / save / submit / delete draft)
├── notifications.py         submission e-mails: internal PDF to admin, client PDF to respondent
├── registration.py          landing-page sign-up: e-mail code / link, rate limits, account + pre-filled draft
├── templates/ia_maturity_landing.html   public landing page (EN/AR)
├── permissions.py           role helpers, sign-up hook, action row-level permissions
├── www/ia-assessment.html   respondent portal (single page, no build step)
├── www/ia_assessment.py     portal page controller (login required)
└── ia_maturity/
    ├── doctype/…            DocTypes, controllers, desk JS, tests
    ├── print_format/ia_maturity_report (client), ia_maturity_internal_report (IRSAA)
    ├── report/ia_maturity_scores, report/ia_maturity_benchmark
    └── workspace/ia_maturity
```

## 10. Tests

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app ia_maturity
```
27 tests (run on both v15 and v16) cover: seed vs workbook structure, all-C = 75 % High, all-A = 25 % Critical, a mixed
pattern against the Excel formula, gating cap, N/A exclusion and validation, incomplete-submission block, action
creation and cancellation, section weighting, return-to-respondent, reviewer approval without edit rights, respondent
role only on self sign-up, PDF rendering, the Arabic seed / Arabic report / RTL PDF, Q13 auto-calculation (locked
answer, minimum sample, thresholds) peer benchmarking (minimum-peer rule, percentile, latest-per-entity) and the client/internal split (hidden sections
absent from client data and PDF, settings switches, clients blocked from the internal report) and the landing-page
sign-up (pre-filled draft, wrong-code lock-out, free e-mail and required-field checks, staff accounts refused,
resume and one-click link).

## 11. Arabic, the issue register and benchmarking

### Arabic / RTL
* Respondents switch language with the **العربية / English** button in the portal header. The choice is remembered
  in the browser and saved on the assessment as its *Report Language*, which the PDF and e-mailed report use.
* Questionnaire text: each template section and question has Arabic fields (*Section Title (Arabic)*,
  *Question (Arabic)*, *A (Arabic)* … *D (Arabic)*). The seed template ships fully translated; for your own templates,
  fill the Arabic fields — anything left blank falls back to English.
* Maturity band names and interpretations have Arabic fields in *IA Maturity Settings > Maturity Bands*.
* The Arabic translation of the seed questionnaire was prepared for this release using Saudi terminology
  (e.g. لجنة المراجعة, الرئيس التنفيذي للتدقيق). Have it reviewed by a qualified Arabic-speaking auditor before client use.
* Font: Noto Sans Arabic (SIL Open Font License, `public/fonts/OFL.txt`) is embedded in the PDF and served to the portal.
* The desk itself follows each user's Frappe language setting; this app's desk labels are English.

### Q13 – issue closure time from the register
1. Record audit issues in **IA Audit Issue** (entity, raised on, status, closed on). Days to close are computed.
2. *IA Maturity Settings > Issue Register*: the DocType and field names (defaults match IA Audit Issue — point these
   at your own issue DocType if you already keep one), look-back period (24 months), minimum closed issues (5),
   thresholds (average months: above 12 = A, above 9 = B, above 6 = C, otherwise D) and whether respondents may
   override the calculated answer.
3. Any template question with *Auto-calculate From = Issue Closure Time* uses it (Q13 in the seed). The answer is
   recalculated every time a draft is saved, frozen at submission, and the basis is printed in the report.

### Peer benchmarking
* *IA Maturity Settings > Peer Benchmarking*: on/off, show to respondents, minimum peer entities (default 5) and
  peer group (*All entities* or *Same sector* — uses the entity's Sector).
* Peers = the latest submitted assessment of every other entity on the same template. Benchmarks change as new
  assessments are submitted; the report states the date.
* Staff: *IA Maturity Benchmark* report (quartiles, median and average per section, maturity-level distribution).

## 12. Client report vs internal report

| Section | Client report (default) | Internal report |
|---|---|---|
| 01 Executive summary | ✔ | ✔ |
| 02 Results by section | ✔ | ✔ |
| 03 Peer benchmark | ✔ | ✔ |
| Key findings | – | ✔ |
| Improvement roadmap | – | ✔ |
| Detailed responses | – | ✔ |
| Reviewer comments | – | ✔ |
| Scoring method | – | ✔ |

* Change the client column in **IA Maturity Settings > Client Report Content** — it applies at once to the portal,
  the client PDF and the client e-mail (also for assessments already submitted). Section numbers adjust automatically.
* **Internal report**: desk *PDF → Internal Report (IRSAA)*, the *Internal report (IRSAA)* button that staff see in
  the portal, or *Print* (it is the doctype's default print format). Clients who try the internal format get a
  permission error.
* **E-mails on submission**: the administrator mailbox receives *[Internal]* with the internal PDF (English); the
  respondent receives a separate e-mail in their report language with the client PDF only.

## 13. Landing page and sign-up

**Flow:** visitor opens `/ia-assessment` → fills *Before you start* → receives a 6-digit code (valid 30 min) and a
one-click link → enters the code → an *IA Assessment Respondent* website user is created (or reused), signed in,
and a draft assessment is created with the entity, perspective, job title, date and report language → Section 1.

**Settings** (*IA Maturity Settings > Landing Page & Sign-up*): turn sign-up on/off, require a work e-mail (free
providers such as gmail.com are refused – list editable), code validity, optional headline override (EN/AR) and
the privacy notice shown next to the consent box (EN/AR). *Allowed Email Domains* still applies.

**Security:** codes and link keys are stored only as hashes; 5 wrong codes block the request; requests are
rate-limited per e-mail and per IP; staff (desk) accounts are never signed in this way – they use `/login`;
responses do not reveal whether an address already has an account. Every request is recorded in
**IA Maturity Registration** (useful as a lead list: who started, verified and which assessment was created).

**Requirement:** a working default outgoing *Email Account* – without it codes cannot be sent and visitors see a
clear "could not send the e-mail" message.

**Why this design (Frappe options considered)**
* *Web Form with guest access* – quick, but limited layout control, no e-mail verification, and guest
  submissions cannot be resumed securely.
* *Frappe sign-up + password* (`/login#signup`) – standard, but adds a password step and a separate page before
  the assessment; respondents often fill this in once a year.
* *Custom landing page + e-mail one-time code* (chosen) – the pattern Frappe itself uses for "login with e-mail
  link" and Frappe Cloud sign-up: one screen, verified business e-mail, no password, details captured up front.

## 14. Not included yet (suggested next steps)

* Arabic versions of the submission e-mail and of the desk labels (Frappe translation files).
* Trend view: an entity's score history across years on one chart.
* Benchmarks by respondent perspective (e.g. CAE versus Audit Committee across all entities).

Customer and auditor oversight, scoped reports and onboarding/allocation approvals: [usage and deployment](docs/GRC_CUSTOMER_OVERSIGHT.md).

- Assessment presentation: collapsed maturity/report panels, default-off question extras, and shared reference-based PDF preview. See [configuration and report guide](docs/GRC_ASSESSMENT_PRESENTATION.md).

- Compact A4 reports use the GRC reference palette. Admins control customer scoring timing and section overview visibility, and can revise the default questionnaire for future assessments.

- Screenshot-aligned questionnaire opening with visible section tabs and compact expand/collapse rows; shared percentage-based section colors and rounded report/progress bars.

- Admins and GRC managers can configure any number of section color ranges, including ten or more, with matching frontend/PDF colors and frozen report snapshots.

- Overall Maturity is hidden by default. Admins and GRC managers can choose completion-based or completed-section-only display from Desk or the portal.

Customers automatically enter questionnaire focus mode, with Normal view and Full screen controls that preserve answers. See [assessment presentation](docs/GRC_ASSESSMENT_PRESENTATION.md#customer-assessment-focus-mode).

Assessment creation lists only active, published templates, including for administrators.

Fullscreen customers can independently hide section overview and progress. Long questions and answer options wrap and scroll in both fullscreen and normal view.

Versioned audit packages, customer-confirmed scope, auditor-owned onboarding, private progress tracking, ownership controls, and bilingual role guides: [configuration, defaults and recovery](docs/GRC_AUDIT_PACKAGES_ONBOARDING.md).

### Easy role guides

[Download the five AlphaX role guides](docs/easy-guides/README.md) for Customers, Auditors, Managers, Admins and Consultants, with steps, menu locations and process flowcharts. [ZIP bundle](docs/easy-guides/AlphaX-GRC-Role-Guides.zip).
