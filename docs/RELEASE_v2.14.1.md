# v2.14.1 — Customer signup retry correction

**Date:** 2026-11-11

Normal customer signup could exhaust the five-per-hour email allowance through invalid form submissions or requests made during the one-minute cooldown. Validation now happens before eligible requests reserve email allowance, and cooldown/hourly checks reserve one slot atomically. The signup and email-code screens show the server's remaining wait and prevent premature resubmission.

[README](../README.md) · [Developer introduction and flow](introduction.md#signup-verification-retry-handling-v2141) · [Changelog](CHANGELOG.md) · [Operations](GRC_OPERATIONS.md#signup-verification-rate-limits)

## Behavior and compatibility

- Keep the 60-second email cooldown, five accepted email requests per hour and 30 attempts per IP per hour.
- Keep neutral responses for ineligible addresses, existing verification/MFA gates and auditor invitation attribution.
- Return `retry_after_seconds` in application rate-limit error JSON. The normal signup screen uses a countdown tied to the normalized email, with Arabic/RTL support.
- Preserve existing counter expiries. Upgrading does not clear a current lockout. Legacy email counters with no expiry receive a bounded lifetime.
- Mail-queue failures still consume an accepted attempt. This change does not claim email delivery or remove IP abuse protection.
- No schema changes, new settings or dependency changes are required. The invitation page uses the shared backend correction; this patch's frontend countdown applies to normal signup/email-code screens.

## Upgrade

Deploy the app patch and rebuild frontend assets using the existing Node 24 build procedure, then restart the backend and clear application caches through the normal site-specific release procedure. See [Operations](GRC_OPERATIONS.md). Updating only the JavaScript does not change server rate limits. Existing Redis lockouts should expire naturally; do not flush Redis or remove unrelated counters.

This release preparation does not deploy automatically or change production records/settings.

## Validation

- 106 backend tests passed on disposable `grc.local`: signup throttling (8), access/authentication (78) and scope/onboarding (20).
- All three signup browser tests passed, covering form validation, countdown expiry, Enter-key retries, normalized email handling and Arabic mobile layout. The Arabic countdown screenshot was visually reviewed.
- Real HTTP checks passed for invalid signup retries, `retry_after_seconds`, preserved hourly limits and concurrent requests. The HTTP script sends no email and requires the muted disposable site.
- Frontend lint and production build passed with zero errors and three existing warnings in PageTour, Templates and SiteEditor. Python syntax and whitespace checks passed.
