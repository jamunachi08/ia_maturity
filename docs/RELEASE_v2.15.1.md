# v2.15.1 — Immediate verification email

**Date:** 2026-11-11

Customer signup, email-code sign-in and invited-customer verification now attempt SMTP delivery during the request. Codes no longer wait for the scheduled email flush or shared background workers. The configured outgoing Email Account and native Email Queue records are retained.

[README](../README.md) · [Workflow diagrams](introduction.md#immediate-verification-email-v2151) · [Operations](GRC_OPERATIONS.md#verification-email-delivery) · [Changelog](CHANGELOG.md)

## Behavior and compatibility

- A successful response requires a persisted `Sent` queue status. This means SMTP acceptance; mailbox arrival and spam filtering remain controlled by the mail provider.
- SMTP exceptions, missing outgoing accounts, muted mail and suspended sending return a translated delivery error. The registration and its unsent queue records are expired, preventing a late retry from sending a failed attempt's code. The explicit cleanup commit is required because native SMTP sends commit before contacting the server.
- The existing 15-minute expiry, single-use hashes, 60-second cooldown, hourly/IP limits, neutral ineligible responses, invitation binding and MFA requirements remain.
- Normal onboarding invitation mail, reminders, reports and Frappe password-login MFA are unchanged. No new schema, configuration or dependencies are introduced.

## Upgrade and rollback

From v2.15.0, deploy the patch, restart the backend through the site's established service manager and clear the site's cache. There is no frontend change or migration requirement for this patch. Sites upgrading from an older release must also follow intervening release instructions. Preserve the previous revision and normal site backup before deployment.

Verify a disposable customer's Email Queue is `Sent` before the request returns, then check mailbox receipt and disable the test user. Retain the site's existing outgoing account and security policies. Do not flush Redis or alter unrelated queues. Rollback consists of restoring the prior app revision and restarting/clearing cache; failed attempts expired by this patch require a fresh code.

## Local validation

- Six native queue/SMTP-mocked integration tests passed for immediate delivery, usable single-use code, preserved MFA, SMTP error cleanup, suspension, muted mail, missing outgoing account and Arabic content.
- Eight signup rate-limit regressions passed.
- Twenty scope/onboarding regressions passed.
- After the final invitation-before-SMTP ordering change, all twelve invited-onboarding tests and all six native delivery tests passed again.
- Thirteen targeted authentication/signup regressions passed without native-runtime workarounds, including neutral eligibility, policy enforcement, single use, invitation isolation and MFA preservation. The two dynamically composed signup fixture addresses now have their Redis counters isolated between tests.
- Python syntax and Git whitespace checks passed. No frontend code changed, so a frontend rebuild is not required for this patch.

The complete access/PDF suite and the standard local migration command were also attempted, but this WSL environment hit native Python/WeasyPrint segmentation faults. A process-only garbage-collection workaround did not complete the full PDF suite. The relevant 47 tests above completed; a full-suite or successful migration result is not claimed. This patch introduces no schema changes.

Live deployment and live verification are recorded separately from these local results.
