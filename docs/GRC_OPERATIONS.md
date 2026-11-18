# GRC operations

[README](../README.md) · [Developer introduction](introduction.md) · [Changelog](CHANGELOG.md)

## Local environment

The new site is `grc.local`. Its local preview runs on port **8005** and its isolated MariaDB instance uses port **13306**, loopback binding and `sites/.grc-db/mysql.sock`. The shared MariaDB service was already unhealthy; this task did not repair it or migrate its existing sites. Do not repoint existing sites to the GRC development database.

Run commands below as the **frappe** OS user inside WSL `alphax_bench`, from `/home/frappe/frappe-bench`. Select Node 24 first:

```bash
export PATH=/home/frappe/.nvm/versions/node/v24.18.1/bin:/home/frappe/.local/bin:/usr/local/bin:/usr/bin:/bin
```

Start the existing local database and preview after a restart:

```bash
./env/bin/python apps/ia_maturity/scripts/provision_local.py
./env/bin/python apps/ia_maturity/scripts/serve_local.py
```

The provisioner leaves an existing site unchanged. A fresh environment also needs the normal bench Redis processes, supported Frappe/ERPNext installations and their dependencies. This development server and database launcher are not production service definitions.

For initial local activation/fixtures only:

```bash
./env/bin/python apps/ia_maturity/scripts/activate_local.py
./env/bin/python apps/ia_maturity/scripts/seed_local.py
```

These scripts target only the isolated `grc.local` configuration. Local emails are muted and the scheduler is disabled. Verification email delivery, reminders and MFA enrollment emails therefore need a real email service for production validation.

During setup, the bench's editable Frappe package metadata was aligned with its installed source, its declared cryptography/pyOpenSSL dependencies were aligned, and the existing `neo_connect` package was registered in the Python environment because the bench already listed it. No application behavior depends on neo_connect or customizations in other apps.

## Frontend build

React source is in `apps/ia_maturity/grc`. Use npm and its committed lockfile.

```bash
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site grc.local migrate
```

The app's build script compiles TypeScript/Vite, writes bundles under `ia_maturity/public/grc`, and generates `www/grc.html` and `www/grc-site.html`. These generated files are intentionally ignored by Git and must be built during deployment. Doppio is not a runtime requirement.

For hot reload use `npm --prefix apps/ia_maturity/grc run dev`; inspect `proxyOptions.ts` for the local Frappe proxy target. The built preview on port 8005 is the validated configuration.

## Tests

Use an isolated site with GRC enabled. Integration fixtures are reserved test organizations/accounts; do not run against production.

```bash
bench --site grc.local run-tests --module ia_maturity.grc.test_access --skip-test-records --skip-before-tests
./env/bin/python apps/ia_maturity/scripts/http_acceptance.py
./env/bin/python apps/ia_maturity/scripts/profile_http_acceptance.py
npm --prefix apps/ia_maturity/grc run lint
npm --prefix apps/ia_maturity/grc run test:e2e
npm --prefix apps/ia_maturity/grc audit --omit=dev
```

Playwright needs Chromium installed once:

```bash
cd apps/ia_maturity/grc
npx playwright install chromium
```

The integration suite creates its own fixtures. `--skip-before-tests` avoids ERPNext's unrelated all-role fixture setup, which conflicts with the intentional separate-account policy. The original baseline suite was run with GRC disabled before activation; its legacy public portal expectations are not the GRC-mode contract.

The HTTP test temporarily revokes/restores the demo consultant assignment, creates/removes a demo API key, and tests a demo staff password reset. Browser tests edit the demo draft. Run these suites sequentially against the local fixture site.

## Production activation

For v1.6.0 → v1.7.0 on grc.neotec.ai, use the [version-specific upgrade checklist](RELEASE_v1.7.0.md), including native PDF dependencies and designated-site activation.


Install the app and its frontend dependencies on a supported bench. Back up the target site first. Enable GRC only on the designated site:

```bash
bench --site YOUR_GRC_SITE set-config grc_enabled 1
bench --site YOUR_GRC_SITE migrate
bench build --app ia_maturity
```

Set the correct HTTPS `host_name`, configure an outgoing Email Account, enroll staff MFA, enable workers/scheduler and perform normal supervised process restarts. Turn off `developer_mode` and `allow_tests`; unmute emails only after verifying recipients and delivery. Do not copy local demo credentials or test accounts into production.

Platform operators configure Frappe infrastructure using separate ERP/platform accounts. IA/GRC staff sign in directly to the custom `/grc/auditor` workspace; the old `/app/grc-staff` bookmark redirects there. A new staff account may have no assigned customers or assessments. The optional Getting started panel explains department invitations, assignments and review, can be dismissed and reopened, and does not require a selection. Customer accounts have no Desk access; general Desk/ERP routes remain denied to GRC staff. Assign at least one organization administrator to each customer, then assign consultants/reviewers at customer and assessment levels.

PDF generation uses the app-declared WeasyPrint 67.x dependency and bundled Noto Sans Arabic fonts. Install its required native text/rendering libraries. Report resources are embedded and the renderer refuses external fetches. Verify English and Arabic PDFs on the deployment image.

Private attachments and report PDFs must remain private. Configure the reverse proxy using standard Frappe protected-file behavior; never expose the private site directory or backups as static content. Apply upload/request-size limits consistent with the app's 10 MB evidence limit.

## Readiness and monitoring

Read-only readiness:

```bash
bench --site YOUR_GRC_SITE execute ia_maturity.grc.health.check
```

The local helper `scripts/check_release.py` runs the check for `grc.local`. A successful configuration check is necessary but does not replace delivery, security, restore or business acceptance. Local readiness intentionally remains false.

Monitor web errors, Frappe Error Log, workers, scheduler heartbeat, Redis, database/storage capacity and Email Queue failures. The GRC settings screen shows tracked reminder delivery history. Standard Frappe Email Queue owns transport retries. Revoked recipients' queued tracked messages are expired when organization access is removed.

### Verification email delivery

From v2.15.1, customer verification codes use immediate Frappe SMTP delivery in the HTTP request. They retain native Email Queue records but do not wait for the scheduled queue flush or shared workers. Configure the normal default outgoing Email Account; no new SMTP credentials, queues or settings are introduced. Normal invitations, reminders, reports and password-login MFA retain their existing delivery behavior.

The endpoint returns success only after the native Email Queue status is `Sent`. SMTP acceptance does not guarantee inbox placement or eliminate the provider's delivery delay. If sending fails, is muted or is suspended, the endpoint returns a delivery error and expires the registration and unsent email records for that attempt, preventing later scheduled retries of that failed code. Fix the outgoing configuration or site-wide suspension and request a fresh code after the normal cooldown. Do not unmute a local test site to run regression tests.

Run `bench --site grc.local run-tests --module ia_maturity.grc.test_verification_email --skip-test-records --skip-before-tests` on the isolated site. Tests execute real queue construction and send/status handling with SMTP mocked and native commits suppressed inside the test transaction. Coverage includes immediate sending, SMTP errors, missing accounts, suspension, muting, Arabic content, code expiry, single use and MFA preservation. See [workflow diagrams](introduction.md#immediate-verification-email-v2151) and [release notes](RELEASE_v2.15.1.md).

### Signup verification rate limits

Verification requests have a 60-second per-email cooldown, five accepted requests per email per hour and 30 attempts per IP per hour. The email window begins at the first accepted request. Rejected cooldown retries do not consume another hourly slot; invalid signup fields are validated before reserving email allowance. All attempts with a valid email identifier still count toward the IP limit. Ineligible addresses receive the same public response and email limits, so the endpoint does not reveal account eligibility through quota responses. A delivery failure still counts as an accepted attempt.

HTTP 429 responses include `retry_after_seconds`. The normal signup/email-code screen shows a countdown and blocks resubmission for the same email until it expires. An existing lockout retains its original expiry after upgrade; this fix does not reset production counters. Do not repeatedly retry or clear all Redis data. Existing verified customers can use password sign-in and authorized organization controls instead of registering again.

To diagnose a reported lockout, read only the targeted site's `grc:SITE:request-email:SHA256_EMAIL`, `request-cooldown` and `request-ip` counters and their TTLs. Normalize email by trimming and lowercasing before hashing. Avoid exposing emails, request bodies, verification codes or tokens in logs. A 429 indicates a request limit, not proof that any email was sent or received. Read the original validation/mail error separately when earlier requests failed.

Regression checks on the disposable site: `bench --site grc.local run-tests --module ia_maturity.grc.test_signup_rate_limit --skip-test-records --skip-before-tests`, `./env/bin/python apps/ia_maturity/scripts/signup_rate_limit_http.py`, and `cd apps/ia_maturity/grc && npx playwright test tests/signup.spec.ts`. The HTTP check requires muted mail and uses unknown demonstration addresses without sending messages.

Check MFA enrollment and delivery with a real staff account; verify that customer email codes never authenticate staff or ERP accounts. Test private report access after membership/auditor revocation. Verify normal ERP operations with a separate ERP account.

## Backups and restoration

```bash
bench --site YOUR_GRC_SITE backup --with-files
```

Retain encrypted off-host copies of the database, public/private files and site configuration/encryption key. Restrict backup access and define retention plus recovery objectives.

The supplied `scripts/restore_rehearsal.py` is deliberately local-only: it checks the isolated socket/database identity, restores the newest SQL backup into a new disposable schema, compares core GRC row counts, validates file archive paths, then drops only its own temporary schema. It does not restore production services or alter the live schema.

A production drill must restore into a separate bench/site with matching app revisions, database and file backups, encryption key and dependencies. Keep email/scheduler disabled during the drill. Validate login/MFA, memberships, assignments, private downloads, frozen reports and queues before cutover. Record restore duration and verification results.

## Rollback

Before deployment, retain the previous app revision and a complete database/file/config backup. A code rollback alone is insufficient after schema/data migration. Restore the matching backup into a separate environment and validate before switching traffic.

Disabling `grc_enabled` restores legacy application behavior and removes the GRC request boundary. It is not a safe emergency access-control rollback for active GRC users. Suspend access or restore the validated release instead.

The browser journey reads an actual queued verification message with the local-only verification helper. It retains clearly named local journey records and revokes temporary staff assignments in a finally block. This does not verify live SMTP delivery.


## Profile, authenticator and email operations (v1.8.0)

Follow the [v1.8.0 deployment and troubleshooting guide](RELEASE_v1.8.0.md). Migration creates the customer MFA role and signup policy fields; restart backend processes after deployment. Use Frappe's default Email Account and Email Queue configuration for verification and report delivery. The GRC admin diagnostics page is read-only and does not replace SMTP provider delivery logs.

Reports remain release-gated. Email report sends a secure link to the current user's email, with fresh authorization on opening. Correct malformed names in User/profile fields and rotate any actually exposed credential; do not silently rewrite previously released report artifacts.


## GRC role and account MFA policies

Staff 2FA is disabled by default following the 2026-11-12 user amendment. GRC app admins configure global defaults, staff roles or individual usernames, including app admins, in Administration → Account security. Explicit existing requirements are preserved. Individual Required or Disabled takes precedence over role defaults; among multiple staff roles Required takes precedence over Disabled. Role policies override the central default. A matching role is an actual User role, not an organization membership. Other Frappe role or site MFA requirements still apply. Customers remain email OTP only, without a password option. Changes require the administrator password, are audited, and revoke affected sessions. See [MFA administration and access recovery](GRC_MFA_ADMINISTRATION.md).

## Signup and account MFA controls (v1.9.0)

Use the [v1.9.0 guide](RELEASE_v1.9.0.md) for verification links and per-account MFA policy. Deploy migration and backend restart together: shared GRC staff role flags move to a native authentication-only role on each applicable account. Existing OTP secrets remain intact.

The v1.9.0 release originally allowed the GRC app admin to manage customer/auditor MFA in Administration → Account security and confirm changes with their own password. Test outgoing email before requiring MFA for users who still need first-login enrollment. Existing sessions are revoked on policy changes. At that release, app-admin MFA remained required; see the current role and account MFA section above for the newer behavior.


## Backend identity enforcement (v1.9.1)

Deploy the [v1.9.1 security update](RELEASE_v1.9.1.md) with migration, asset build and backend restart together. MFA-required users with pre-update sessions must sign in again. Their API tokens and OAuth credentials cannot substitute for a password/authenticator session. Native OTP secrets and administrator MFA policies remain intact.

GRC password reset/change always returns to login and revokes sessions; it never automatically authenticates the account. Correct affected profile names to the person's real name and rotate any password previously exposed. Do not copy the exposed value into tickets or release notes.


## Dedicated signup (v1.10.0)

Follow the [signup release checklist](RELEASE_v1.10.0.md). Migration adds two registration metadata fields; rebuild assets and restart backend processes together. Existing pending verification links remain usable and keep manual organization setup. No existing customer organizations, memberships or auditor assignments are backfilled from historical registration text.


## Customer organizations and staff workflow update (2026-10-26)

See [task progress and validation](REQUIREMENTS_2026-10-26.md). Migrate the designated site, rebuild frontend assets and restart backend processes together. No global email setting is changed by this update.

Existing memberships keep their organization-specific roles. GRC app administrators may set an optional parent organization; cycles are rejected. Holding administrators inherit read access to descendants, while edits require direct membership. Verify hierarchy assignments with the business owner before rollout.

Optional reminder/status emails require both organization and individual permission. Existing overall user opt-outs remain effective. Verification, security, invitations and clarification requests remain mandatory. Turning off optional mail expires queued optional deliveries when still pending; mail already accepted by the provider cannot be recalled.

Staff-created drafts may await customer ownership. Use Invite Customer Admin, let the recipient verify and accept, then confirm ownership before submission. Changing an existing consultant/reviewer/customer owner requires a transfer reason. Actor and before/after changes remain in the detailed staff timeline.
