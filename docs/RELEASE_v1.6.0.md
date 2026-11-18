# Release v1.6.0

**Date:** 2026-10-24
**Status:** Development release validated on the local GRC site; production activation remains subject to acceptance.

[README](../README.md) · [Changelog](CHANGELOG.md) · [Architecture](introduction.md) · [Acceptance criteria](DEVELOPMENT.md)

## Scope and version decision

This minor release adds the GRC platform to client baseline 1.5.0. The feature is enabled by the site configuration flag `grc_enabled`; other sites retain legacy behavior. Schema changes add GRC records and snapshot fields without removing baseline fields. Enabling the feature deliberately replaces the legacy public/Desk assessment workflow on the selected site.

Highlights: shared branded login and staff MFA; customer/auditor React dashboards; admin-controlled customer assignments; ERP and organization isolation; immutable assessment/review/report workflow; bilingual public pages; styled dropdowns and navigable cards; profile/password self-service with admin field controls. See the [changelog](CHANGELOG.md) for the full list.

## Installation on a new designated site

Use the validated Frappe 15 stack and Node 24. ERPNext 15 was included in local acceptance; the app itself declares only Frappe as a required app. Provision the site/database, Redis and normal bench services before these steps. Example commands run from the bench root:

```bash
bench get-app --branch main https://github.com/AlphaX-SAAS/ia_maturity.git
git -C apps/ia_maturity checkout v1.6.0
npm --prefix apps/ia_maturity/grc ci
bench --site YOUR_GRC_SITE install-app ia_maturity
bench --site YOUR_GRC_SITE set-config grc_enabled 1
bench --site YOUR_GRC_SITE migrate
bench build --app ia_maturity
```

Apply the production service restart procedure after building/migrating. Generated portal assets and `www/grc.html` / `www/grc-site.html` are not in Git; skipping the build leaves the portal unavailable. Doppio does not need to be installed at runtime. WeasyPrint and its native text libraries are required for GRC PDFs.

Activation configures portal roles, User fields, assignment/membership uniqueness, OTP App MFA, the public homepage and disabled generic signup. It provisionally publishes only the imported reference template. Drafts created later are not automatically published.

## First app administrator and real users

Use a separate trusted platform operator, not a shared demo account. From `bench --site YOUR_GRC_SITE console`, create the first GRC administrator through the app service:

```python
import frappe
from ia_maturity.grc.administration import save_staff

frappe.set_user("Administrator")
save_staff("grc-admin@YOUR_DOMAIN", "GRC Administrator", role="GRC App Admin")
frappe.db.commit()
```

Replace the example address with the intended real administrator. Staff creation does not send a welcome email or set a shared password. Configure outgoing email, use Forgot password for the new account, then complete the normal password login and authenticator enrollment/MFA flow. Verify actual email delivery.

That administrator creates additional GRC staff in the auditor workspace. Customers verify email and create their organization, or join through an invitation. Assign customer-level Consultant/Reviewer responsibilities before allocating an assessment team. Users requiring ERP access receive separate ERP accounts.

## Upgrading an existing installation

1. Record the current Git revision and take a complete database, file and site-configuration backup.
2. Fetch and check out `v1.6.0`; install the frontend lockfile with `npm ci`.
3. Rehearse `bench --site SITE migrate` and `bench build --app ia_maturity` on an isolated copy.
4. If the site already uses the GRC development implementation, migration adds the profile settings schema. Missing profile policy defaults to the seven supported personal fields; an explicitly empty selection locks all fields.
5. If the site is a legacy deployment, keep GRC disabled until its account/organization/assessment mappings are reviewed. There is no automatic bulk conversion of legacy respondents into memberships or old assessments into GRC workflow assignments.
6. Resolve mixed ERP/legacy assessment-role accounts into separate identities before activation. Legacy assessment staff roles become portal-only in GRC mode.
7. Activate only the designated site, migrate, build and restart its normal services. Confirm routing, staff MFA, customer scopes, assignment revocation and private downloads before admitting users.

Do not mark an assessment as historical by inventing a scoring snapshot. A legacy-data migration must preserve original submissions/reports and have an approved mapping and rollback plan.

## Validation and remaining gates

Locally validated: 23 GRC integration tests, 10 Chromium scenarios, authentication/access and profile/password HTTP suites, lint/typecheck/build, migration, Arabic PDF rendering and an isolated backup restore rehearsal. The original 27-test baseline passed before GRC activation. Production npm dependency audit found zero vulnerabilities at validation. The full development dependency audit reports three moderate findings in the Tailwind/PostCSS selector-parser chain; the suggested complete remediation includes a Tailwind major upgrade and needs a separate styling/build validation. Vite also reports a 585.58 kB main JS chunk (184.99 kB gzip); further code splitting is a performance follow-up. Neither warning prevented the validated production build.

Production remains gated by owner-approved scoring/workbook and bilingual content, reviewed legal text, the final hostname/HTTPS, transactional email and MFA enrollment delivery, supervised workers/scheduler, private storage, monitoring and a complete restore drill. Firefox/Safari, formal accessibility, load testing and customer UAT are still pending.

The local `grc.local` instance uses an isolated development database, muted emails and a disabled scheduler. These choices are local test arrangements, not production deployment instructions. Do not copy its demo credentials or users. Read [operations](GRC_OPERATIONS.md) for configuration, backup, monitoring and rollback procedures.

## Rollback

Restore a matching code/database/file/configuration backup in a separate environment and validate it before traffic cutover. Disabling `grc_enabled` removes the GRC request boundary and is not an emergency security rollback for live GRC accounts. Suspend access while recovering when necessary.
