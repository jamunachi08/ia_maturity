# v2.0.0 — Customer organizations and scoped staff workflows

[README](../README.md) · [Changelog](CHANGELOG.md) · [Architecture and workflows](introduction.md#organization-switching-and-holding-companies) · [Task validation and skipped work](REQUIREMENTS_2026-10-26.md)

## Compatibility requirements

This is a major release because customer-role enforcement and ownership-transfer validation deliberately change previously accepted behavior.

- Customers require **GRC Customer** plus active organization membership for tenant access. Accounts with only stale GRC classification metadata or legacy customer roles remain restricted. Review affected accounts explicitly; never infer organization membership from matching email domains or organization names.
- Changing an existing consultant, reviewer or customer owner through assign_assessment requires a nonempty transfer reason. Callers must preserve current consultant/reviewer values when retaining them; omitted values retain the endpoint's existing clearing semantics.
- GRC staff become System Users solely for the restricted /app/grc-staff page. Customer accounts remain Website Users. General ERP/Desk routes and generic document APIs remain blocked for GRC accounts.
- **GRC Manager is organization-scoped**, through an explicit Manager customer assignment. It does not grant global staff, MFA or application-setting administration. GRC App Admin retains those controls.
- Parent hierarchy changes require GRC App Admin. Holding administrators inherit assessment reads, while writes still require explicit direct subsidiary membership.

## Deployment

Back up the designated site's database, private/public files and encryption configuration before deployment. Review customer roles and any external assign_assessment integrations before switching versions.

From the bench root, using the production service/container equivalents where appropriate:

~~~bash
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity describe --tags --exact-match
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site YOUR_GRC_SITE migrate
bench --site YOUR_GRC_SITE clear-cache
bench restart
~~~

Verify v2.0.0 or an explicitly reviewed later release. Ship backend code, schemas, Desk page and frontend assets together. Migration is idempotent and gated by grc_enabled; it does not change global outgoing-mail settings or unmute any queue.

Schema additions: parent organization and optional-email controls on IA Maturity Entity; optional-email controls on User; customer_pending on GRC Assessment Assignment; notification_kind on GRC Reminder Delivery; Manager responsibility and the restricted GRC Staff Desk page.

## Acceptance after deployment

1. Confirm customer sign-in, password recovery, neutral registration guidance, resend cooldown and displayed expiry.
2. Check one account with different roles in two organizations; verify switching and unrelated-tenant denial.
3. Configure a parent/subsidiary hierarchy. Parent admins must have read-only subsidiary assessment access; verify edits require direct authorization and revoked memberships stop access.
4. Confirm staff MFA and /login?staff=1 -> /app/grc-staff. Customer Desk access and unrelated ERP routes must fail.
5. Let authorized staff create an organization/draft, invite a customer admin and transfer ownership with a reason. Submission must wait for customer ownership.
6. Verify answer/evidence/status/assignment history, staff-only detail and customer timeline redaction.
7. Test optional organization/user email controls together. Clarification, security, verification and invitations remain mandatory.
8. Verify a released report/private evidence download still obeys current organization and assessment permissions.

## Validation and skipped work

Local validation passed: **69 backend tests, 23 Chromium scenarios, both HTTP security suites, migration, lint, TypeScript/build and syntax/diff checks**. English/Arabic mobile signup, organization switching and native staff history were visually reviewed.

**Skipped:** production verification-email delay investigation, provider delivery records, SPF/DKIM/DMARC and recipient spam placement, as requested. Local grc.local email is intentionally muted; do not unmute its test backlog.

This release preparation does not deploy to production. Rolling back code alone after schema/identity changes is not a supported recovery plan; restore a rehearsed backup if full rollback is necessary.
