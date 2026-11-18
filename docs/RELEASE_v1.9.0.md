# v1.9.0 — Verified signup and admin-managed MFA

[README](../README.md) · [Changelog](CHANGELOG.md) · [Introduction](introduction.md)

## Signup verification

The GRC signup flow already required an emailed code or link before creating a User. This release makes the link explicit and prevents alternate public provisioning paths from relying on a changeable Website Settings toggle.

- **Send verification email** creates only a pending registration. It uses the default outgoing Frappe Email Account and Email Queue.
- The email contains **Verify email and continue**, plus a six-digit code as an alternative proof of mailbox access.
- Opening the URL displays a confirmation screen. A GET, preview or link scan does not consume the verification or create an account. The user clicks the confirmation button to POST the token.
- The link/code is single-use, expires after fifteen minutes and is superseded by a newer request. Domain policy is rechecked when creating the verified customer.
- Frappe's separate public sign_up endpoint is blocked on GRC-enabled sites even if generic signup is enabled in Website Settings. A User validation guard also rejects unverified Guest provisioning.
- Already-signed-in users visiting /signup must explicitly sign out before creating another account. Their existing session is no longer silently presented as a successful new signup.
- Successful verification records grc_email_verified on the User. Migration backfills it only from verified GRC registrations. **Not recorded** does not claim that an existing account has never verified through another process.
- Existing and administrator-provisioned accounts remain active. This change does not retroactively lock them out or invent evidence of email ownership.

Normal Frappe signup behavior on sites without grc_enabled is preserved. Production email delivery still needs the checks in [v1.8.0](RELEASE_v1.8.0.md).

## Admin control over customer and auditor MFA

Open **Auditor dashboard → Administration → Account security**, search for the account and choose **Edit security**.

| Policy | Behavior |
|---|---|
| Default | Requires MFA for auditors/reviewers/staff; retains enabled customer MFA. Other customers can opt in from their profile. |
| Required | Requires Frappe OTP App MFA at sign-in. A user without an enrolled authenticator follows Frappe's first-login setup email. |
| Disabled | Removes the GRC MFA requirement and prevents customer self-enrollment. Password authentication and all GRC/ERP permission boundaries remain in force. |

The admin must enter their own current password to save a change. Changes are rate-limited, audited and revoke all sessions of the affected account. Users cannot alter this policy through profile fields or generic APIs.

**GRC app-admin accounts always require MFA.** Other role or site-wide native Frappe MFA policies are not weakened. If another role or All requires MFA, disabling it through GRC is rejected with an explanation; a platform administrator must review that separate policy.

Frappe System Settings must have two-factor authentication enabled with **OTP App** before an admin requires MFA. Verify outgoing email before requiring MFA for users who have not enrolled. Email-only customers may need password recovery before using password plus OTP. Native OTP secrets are retained when a policy changes; disabling and re-enabling does not expose or silently rotate the secret.

## Upgrade

Run from the bench root after a database/files backup and local-change review:

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

Verify **v1.9.0**, or deploy that reviewed tag if main has moved. Use the production service/container restart equivalent where appropriate.

Migration adds protected User fields grc_mfa_policy and grc_email_verified. It moves GRC MFA enforcement from shared staff roles to the authentication-only **GRC Account MFA** role, synchronizing existing customer/auditor accounts and preserving their encrypted OTP secrets. Enrolled v1.8 customers migrate from GRC Customer MFA. GRC app admins and auditors retain required MFA by default. The new role grants no record access.

Do not deploy the backend without migration and restart: native Frappe role flags and per-account roles must stay consistent. Keep existing site activation, encryption keys, email settings and workers in place. Upgrading from an older release also includes [v1.8.0 profile, email and PDF changes](RELEASE_v1.8.0.md).

## Acceptance

1. In a new private session, sign up with a fresh email. Confirm no User or organization exists before verification.
2. Receive the real email, open its link, confirm the email and enter the customer dashboard. Reusing the link must fail. The six-digit code remains an alternative email verification method.
3. Confirm generic Frappe signup cannot create a User on the GRC site even when its setting is changed.
4. Visit /signup from an existing authenticated session; the page must explain that signing out is required.
5. As a GRC admin, disable a test customer's and auditor's MFA. Their active sessions must end. Password login must succeed without GRC OTP, and customer self-enrollment must be unavailable.
6. Require MFA again. Both users must receive Frappe's authenticator challenge. Check enrolled and first-enrollment accounts.
7. Check unauthorized policy writes, admin self-disable prevention, other-role MFA, tenant access and ERP isolation.
8. Confirm Administrator still uses its normal ERP login and that production verification emails arrive.

Local validation: 40 backend integration tests, 18 browser scenarios, both HTTP security suites, frontend lint and production build. Browser tests cover actual queued verification links, confirmation before creation, existing-session handling, customer/auditor policy changes and active-session revocation. Local email is muted; inbox delivery remains a production acceptance step.

For rollback, restore a coordinated database, app and files backup, or apply a forward fix. Earlier code expects different role-based MFA flags; rolling back Python alone can leave inconsistent authentication policy.
