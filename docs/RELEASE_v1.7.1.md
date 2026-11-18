# v1.7.1 — Accept Frappe usernames at password login

[README](../README.md) · [Changelog](CHANGELOG.md) · [Introduction](introduction.md)

Password login incorrectly used an email input, so browsers rejected Administrator before sending any request to Frappe. Password sign-in now accepts **Email or username**, with an Arabic translation. The server still verifies credentials, enabled status, MFA and access. Customer signup, email-code sign-in and recovery remain email-only.

This patch does not change account roles, routing, MFA, database schema or PDF behavior.

## Upgrade from v1.7.0

Run from the bench root, not its sites directory:

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

Do not discard local changes. Deploy the reviewed **v1.7.1** tag if main has advanced further. There is no new schema migration for this frontend patch. If v1.7.0 setup is incomplete, finish its [dependency and activation checklist](RELEASE_v1.7.0.md).

Hard-refresh /login. Enter Administrator and its existing password; the request should reach normal Frappe authentication without the browser asking for an email address. Verify normal ERP and GRC destinations and staff MFA remain intact. The release neither creates accounts nor resets passwords.

## Validation

All 14 browser scenarios, frontend lint and the production bench build passed.

- Browser regression checks Administrator is sent unchanged to the login endpoint and a server rejection is displayed. This test stubs the response rather than using real Administrator credentials.
- Email-only modes still reject a non-email identifier.
- Existing browser suites exercise real customer/staff/ERP sign-in, MFA and the complete assessment journey.
