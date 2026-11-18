# Release v2.5.0

**Date:** 2026-11-02

[README](../README.md) · [Developer introduction](introduction.md) · [Changelog](CHANGELOG.md) · [MFA administration and recovery](GRC_MFA_ADMINISTRATION.md)

## Behavior

Administration → Account security now exposes one central policy for all GRC customers, staff and app administrators, and one shared native Frappe verification method.

| Policy | Behavior |
| --- | --- |
| Enabled | Users may enroll or withdraw optional MFA from their profile after password confirmation. |
| Disabled | GRC MFA and self-enrollment are disabled. |
| Enforced | Every GRC account must sign in with a password and a second factor. |

The method is Authenticator app or Email code. Email MFA follows password verification; it is separate from passwordless customer registration. The method is site-wide and also applies to non-GRC accounts that already require MFA. Enabling Email requires an active default outgoing Email Account, ready credentials and unmuted, unsuspended mail. Verify actual delivery to a test mailbox before enabling it in production.

## Compatibility and migration

This is a minor feature release from 2.4.0 to 2.5.0. Migration preserves existing role/account behavior until an administrator explicitly saves a central policy. After adoption, central policy supersedes legacy GRC overrides and their mutation APIs reject further changes.

Migration adds hidden central policy/method/revision/platform-preservation fields to GRC Settings, plus the protected User.grc_mfa_opt_in flag. Native OTP secrets are retained. Migration does not reset an adopted central method to Authenticator.

If role All currently enforces MFA, saving central settings moves the inherited requirement to the authentication-only GRC Platform MFA role for non-GRC accounts and removes the blanket requirement from GRC accounts. New non-GRC accounts inherit the preserved requirement. Unrelated independently protected roles are not silently weakened: conflicting roles are reported for a platform administrator to review.

Admin changes require the acting administrator's password, are audited and revoke affected sessions. Pending challenges are invalidated by policy/method changes. Email and authenticator challenges are account/password-bound, short-lived, rate-limited and consumed once. Settings and user synchronization recheck the current locked central policy.

## Deploy

Use the normal backup and service-management procedure for your hosting environment. For a shell-managed bench, activate a compatible Node runtime (validated with Node 24) and run:

~~~bash
cd /path/to/frappe-bench
SITE="YOUR_LIVE_SITE"

bench --site "$SITE" backup --with-files
bench --site "$SITE" set-maintenance-mode on

git -C apps/ia_maturity status --short
# Resolve any local app changes before continuing.
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity merge --ff-only v2.5.0

npm --prefix apps/ia_maturity/grc ci
npm --prefix apps/ia_maturity/grc run build
bench build --app ia_maturity
bench --site "$SITE" migrate
bench --site "$SITE" clear-cache
bench restart
bench --site "$SITE" set-maintenance-mode off
bench version
~~~

If the bench shares this app across sites, migrate the other affected sites before restarting. No new Python dependency is introduced. Keep maintenance enabled if a deployment step fails, investigate the error, and finish the upgrade or restore the full pre-upgrade backup.

After deployment, sign in with an existing GRC app admin and save the central policy and method under Account security. Saving may sign that administrator out. Test password plus the selected factor, optional enrollment for Enabled, Disabled behavior, session revocation and non-GRC coverage. Existing locked-out administrators need the platform's trusted recovery process before changing policy.

## Validation

The isolated restored customer database uses Frappe 15.113.3. Release validation covers central policies and methods, password/role authorization, optional enrollment, stale policy caches, legacy-write races, independent native MFA requirements, platform preservation, challenge replay/expiry/account binding/rate limits, and migration persistence. The existing MFA regression suite and bilingual/mobile browser checks are also run.

Backend tests intercept outgoing transport while exercising native Frappe email generation and verification. Browser mocks check UI behavior. These tests do not establish production SMTP/inbox delivery.

## Source map

- ia_maturity/grc/mfa_policy.py: central configuration, enrollment, locking and platform preservation.
- ia_maturity/grc/mfa.py: native email/authenticator proof and verified-session enforcement.
- grc/src/pages/AccountSecurity.tsx: central admin controls and account status.
- grc/src/pages/Authenticator.tsx: profile enrollment and withdrawal.
- ia_maturity/grc/test_mfa_policy.py and grc/tests/central-mfa.spec.ts: new integration/browser coverage.
