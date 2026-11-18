# Release v2.4.0

**Date:** 2026-11-01

[README](../README.md) · [Developer introduction](introduction.md) · [Changelog](CHANGELOG.md) · [MFA administration and recovery](GRC_MFA_ADMINISTRATION.md)

## Changes

GRC app administrators can configure MFA defaults per GRC User role and exceptions per individual account, including app administrators. Individual policies override role defaults, and Required wins among conflicting GRC role policies. Existing defaults and account policies remain unchanged until deliberately modified; separate Frappe MFA requirements continue to apply. Changes require the administrator password, are audited, and sign out affected accounts. Disabling MFA reduces the affected accounts' sign-in protection.

## Deploy and verify

Back up the site and test on staging. Deploy the app, run `bench --site SITE migrate` to add the GRC Settings role-policy field, rebuild frontend assets with `bench build --app ia_maturity`, and restart backend services. Test a role policy, an individual exception, applicable independent Frappe requirements, and sign-in/session revocation before rollout.

Existing locked-out administrators should have the platform operator restore the Frappe OTP App setting, verify outgoing email and follow the normal authenticator enrollment or recovery procedure first. After signing in, open Administration → Account security to set policies. See the [recovery guide](GRC_MFA_ADMINISTRATION.md).
