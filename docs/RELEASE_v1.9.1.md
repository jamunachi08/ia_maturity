# v1.9.1 — Backend MFA validation and safe profile names

[README](../README.md) · [Changelog](CHANGELOG.md) · [Developer guide](introduction.md#backend-identity-enforcement)

## What changed

- First, middle and last names are checked on the backend, including direct User updates. Values matching the current password or a combined display name are rejected; password changes/reset cannot reuse a profile name.
- Unsafe legacy names are masked in profile values, live owner labels, staff lists, bootstrap and login JSON/cookies. Users see a correction notice instead of a password-like name.
- Login, profile and authenticator forms submit validation to the backend. Password inputs remain separate from personal details with explicit autocomplete purposes.
- Required MFA is verified before session creation using Frappe's native challenge, account, password hash, encrypted OTP secret and current authenticator code. Successful challenges are consumed atomically; missing, invalid, expired, cross-account and reused proofs are rejected.
- Native sessions carry server-created MFA proof checked on later GRC requests. Browser flags cannot supply that proof. API tokens/OAuth cannot bypass MFA for an account that requires it.
- GRC password recovery validates the native reset key or old password and native password-strength policy, consumes the key and revokes sessions. It returns to login without creating an authenticated session.
- Administrator/normal ERP login and recovery remain native. Admin customer/auditor Default/Required/Disabled policies remain intact; app-admin MFA stays mandatory.

## Deployment impact

MFA-required users with pre-update sessions must sign in again. Existing authenticator secrets remain valid. GRC integrations using tokens for MFA-required users now receive authentication denial; a token is not accepted as an alternative MFA flow. Keep **System Settings → Two Factor Authentication → OTP App** enabled for required accounts.

This update masks detectable unsafe saved names but does not invent real names or alter frozen released reports. Correct each affected account using the person's confirmed name and rotate any password previously exposed. A one-way current password hash cannot detect every historical password that happens to look like a valid name; review known affected accounts explicitly.

## DevOps checklist

Run from the **bench root**, not its sites directory, after reviewing local changes and taking a backup:

~~~bash
cd ~/frappe-bench
bench --site grc.neotec.ai backup --with-files
git -C apps/ia_maturity status --short
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity describe --tags --exact-match
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site grc.neotec.ai migrate
bench --site grc.neotec.ai clear-cache
bench restart
~~~

Verify **v1.9.1** or the specifically reviewed later tag before proceeding. Use the production container/service equivalent of bench restart if needed. Deploy backend hooks and frontend assets together. Upgrades from before v1.9.0 also need its MFA-role migration; keep the existing encryption key and site settings.

## Acceptance

1. Correct an affected first/last name. Confirm profile, staff list and current assessment owner show the real name.
2. Try a current password in name fields, including a letters-only test password and a split first/last-name combination, through direct requests. The backend must reject it without echoing it.
3. For a customer and auditor with required MFA, submit a missing/wrong code: no dashboard session may result. Complete a fresh valid challenge successfully, then verify the same challenge cannot be reused.
4. Verify an old unmarked session and an API token cannot bypass required MFA. Changing a browser flag must not grant access.
5. Complete password recovery. It must return to login and require the configured MFA. Reusing the reset link must fail.
6. Check admin MFA policy changes, customer optional/disabled MFA, tenant isolation and Administrator ERP login.
7. Check English/Arabic login and profile forms, including server error display.

Local coverage: 46 backend integration cases, 18 browser scenarios, both HTTP suites, lint and production build. Tests use the isolated grc.local site with muted email. Production SMTP delivery and deployment remain DevOps acceptance steps.

If rollback is necessary, restore coordinated database, app and file backups. Prefer a forward fix; rolling back to earlier authentication code restores the addressed bypass paths.
