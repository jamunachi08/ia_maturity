# v1.8.0 — Profile security, signup policy and report delivery

[README](../README.md) · [Changelog](CHANGELOG.md) · [Introduction](introduction.md)

## Changes and limits

- Customers can enroll an authenticator from **My profile → Account security**. Enrollment uses Frappe's native OTP secret storage and login challenge. GRC staff MFA remains mandatory, and built-in Administrator keeps normal ERP authentication.
- Personal details and security forms are separate. Personal-name validation rejects malformed names and a value matching the user's current password. Malformed saved names are blanked in profile responses, with a correction notice; current owner labels fall back to the account email until corrected.
- Signup accepts all valid personal and organizational email addresses by default. **Auditor dashboard → Administration → Settings → Signup email policy** can restrict new accounts to exact domains. List subdomains separately. Existing accounts retain login access. This GRC setting replaces the legacy organizational-email restrictions on GRC-enabled sites only.
- Verification and report email use **frappe.sendmail**, the site's existing default outgoing Email Account, and Frappe Email Queue. There is no second SMTP configuration in GRC.
- Assessment pages always explain PDF availability. **Download PDF** and **Email report** become active after reviewer release. Email report sends an authenticated link to the requesting user's own sign-in email. It does not send an attachment, bearer token, scores, or an arbitrary third-party email; opening the link checks current authorization and revocation.
- Released PDFs and report API context retain the frozen release snapshot. Current owner labels and future report generation use corrected, validated personal names.

The reported password-like owner value comes from stored personal-name data. The exact original cause has not been reproduced; autofill separation and backend validation are preventive fixes. This release does not infer the client's real name or silently rewrite immutable reports.

## Deploy from the bench root

Back up the database and files and review local changes before updating. Use the same environment that runs the production bench.

~~~bash
cd ~/frappe-bench
bench --site grc.neotec.ai backup --with-files
git -C apps/ia_maturity status --short
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity describe --tags --exact-match
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site grc.neotec.ai migrate
bench --site grc.neotec.ai clear-cache
bench restart
~~~

Confirm the deployed revision is **v1.8.0**. If main has moved, deploy the reviewed v1.8.0 tag using your normal deployment procedure. Do not run npm from the sites directory with an apps-relative prefix. Keep the existing designated-site grc_enabled setting.

**Migration and backend restart are required.** Migration adds the authentication-only GRC Customer MFA role and the signup policy fields. The role has no document permissions. Restart the web and worker processes using your equivalent service/container commands if bench does not manage them. Node 24 and the PDF dependencies from [v1.7.0](RELEASE_v1.7.0.md) remain required.

Migration does not overwrite SMTP credentials, an existing GRC signup policy, users' passwords, or real names. The new GRC policy defaults to all valid emails even if legacy IA settings blocked personal domains. Review the policy after deployment if the site requires restrictions.

## Correct the affected client's profile

1. If the displayed value is an actual password, have the account owner change it immediately and replace it anywhere else it was reused. Do not paste it into tickets, logs or documentation.
2. Enter the real first/middle/last name in **My profile → Personal details**. If the administrator has locked these fields, temporarily allow the required fields in GRC Settings or have the platform administrator correct the User record.
3. Refresh the assessment. The Owner label uses the current valid name, not the old copied assessment label.
4. An already released PDF remains immutable. If it contains sensitive data, the platform operator must handle access and replacement under the organization's record-retention process. Changing the profile cannot retract screenshots or files already downloaded.

## Customer authenticator setup

1. The platform administrator enables **Two Factor Authentication** with method **OTP App** in Frappe System Settings. Keep existing GRC staff MFA requirements enabled.
2. The customer signs in and opens **My profile → Account security → Set up authenticator**.
3. Enter the current password. Email-only customers first set a password using the normal password recovery flow.
4. Scan the QR code in an authenticator app and enter the current six-digit code within ten minutes.
5. Confirm activation. All account sessions are revoked, and the customer signs in again using password plus Frappe's authenticator challenge.
6. Email-code/link verification and password recovery do not bypass activated MFA. Lost authenticator recovery is managed by a platform administrator through Frappe's recovery process; no self-service disable or secret-reveal endpoint is provided.

The QR setup secret is encrypted in Redis, bound to the authenticated session and expires after ten minutes. It enters Frappe's encrypted native storage only after a valid code. Responses containing setup information use Cache-Control: no-store.

## Email setup and delivery investigation

Use the existing **Frappe Email Account** setup. Confirm **Enable Outgoing**, **Default Outgoing**, sender identity, SMTP host/port and the provider's required TLS/authentication settings. Save credentials only in Frappe. Configure the production host_name so links use the correct HTTPS hostname.

The GRC admin can open **Settings → Email delivery diagnostics** for read-only account, queue, scheduler and worker checks. Diagnostics contain no mail bodies, recipient lists, passwords or raw SMTP traces. A platform ERP account can inspect **Email Queue** and **Error Log** in Desk.

- **No queue record:** check the actual signup response, eligible account, spam/rate limits, domain policy and outgoing-account errors. Existing staff/ERP accounts do not receive customer login codes.
- **Not Sent / Sending:** verify workers, scheduler, email queue suspension, site mute_emails, and the account's awaiting-password flag. Inspect stalled jobs.
- **Error:** inspect the specific Email Queue record. SMTP authentication, TLS, connectivity, provider quota, recipient and relay errors require corresponding provider/server corrections. Share only redacted error text.
- **Sent:** the SMTP server accepted the message; this does not prove inbox delivery. Check spam/quarantine, provider delivery logs, sender SPF/DKIM/DMARC and bounce handling.
- **Expired code:** request a new verification email after delivery is working. Codes are single-use and expire after fifteen minutes; resending invalidates older pending codes.

Queue entries are created through Frappe's normal transaction and sent asynchronously. The UI says queued, not delivered. No production SMTP test or inbox delivery has been verified by this release.

## Acceptance and rollback

Verify personal and organizational signup addresses, a restrictive admin policy, existing-user login after restrictions, real verification delivery, customer MFA enrollment/relogin, Administrator ERP login, staff MFA, current owner labels, and PDF/email controls before and after release. Check that an unassigned/revoked auditor and another customer's user cannot download or email the report. Verify EN/AR and mobile profile screens.

Automated local coverage includes 36 backend integration tests, 16 browser scenarios, both HTTP security suites, frontend lint and the bench build. Browser coverage exercises native customer MFA, actual queued verification emails, the review/release journey, PDF bytes and report-link email requests. Test email delivery is muted; local success is not evidence of production inbox delivery.

Do not roll back code to a version that lacks enforcement for enrolled customer MFA while leaving enrolled accounts active. Prefer a forward fix; otherwise restore a coordinated database/files/code backup and follow the site's security recovery procedure. Preserve the existing encryption key and native OTP defaults in backups.
