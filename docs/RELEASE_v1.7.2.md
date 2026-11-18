# v1.7.2 — Restore built-in Administrator authentication and ERP access

[README](../README.md) · [Changelog](CHANGELOG.md) · [Introduction](introduction.md)

## Problem and correction

v1.7.1 fixed browser email validation, but Administrator still received “GRC staff must sign in using a password and authenticator code.” The server classified the built-in platform account as GRC staff because Frappe returns all roles as its effective permission set. Those synthetic roles do not represent GRC membership.

The built-in **Administrator** is now explicitly classified as ERP before examining effective roles. Session bootstrap and home routing follow account classification instead of treating every administrative principal as a portal user.

Frappe still authenticates the password and applies its own MFA policy. This patch does not disable MFA or alter user roles, passwords or site MFA settings. Separate GRC App Admin, GRC Auditor and GRC Reviewer accounts retain mandatory staff MFA and portal-only access. Platform administrative privileges for maintenance/provisioning remain intact.

## Upgrade

Run from the bench root, using the normal backup and deployment process. Review local changes before pulling.

```bash
cd ~/frappe-bench
git -C apps/ia_maturity status --short
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity fetch origin --tags
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site grc.neotec.ai clear-cache
bench restart
```

Deploy the reviewed **v1.7.2** tag if main has moved beyond it. No new schema migration is required for this patch. Complete the [v1.7.0 dependencies and activation](RELEASE_v1.7.0.md) if not already done.

**Restart the backend web processes.** Building frontend assets or clearing cache alone cannot load the changed Python classification code. Use the equivalent service/container restart if your deployment does not use bench-managed production processes.

## Verify on the deployed site

1. Hard-refresh /login or open a new private session.
2. Sign in as Administrator using its existing password and any MFA required by the site's normal Frappe policy. The custom GRC staff error must be absent, and the account should retain its normal ERP/Desk destination and access.
3. Sign in separately as a GRC app admin and auditor. Both must still receive the authenticator challenge and enter the auditor workspace.
4. Confirm GRC staff/customer accounts still cannot open /app or generic ERP APIs. Assigned-customer visibility remains unchanged.
5. If the old error persists, verify the deployed commit/tag and that every web process serving the site was restarted. Do not disable MFA or change roles as a workaround.

## Validation

All 29 backend integration tests, 15 browser scenarios, both HTTP security suites, frontend lint and the bench build passed.

The real local Administrator password login reproduced HTTP 401 before the fix and succeeded afterward. The browser test checks ERP routing, session classification, Desk access and redirect away from GRC dashboards. It uses credentials from the private local fixture file, never committed values or mocked authentication.

Backend regressions cover Administrator's effective role list, ERP classification, home routing, the login hook and Desk request boundary. Separate GRC app-admin tests verify mandatory MFA and ERP denial. Existing staff and customer security/journey suites remain in place.

Production rollout and final site acceptance remain with DevOps.
