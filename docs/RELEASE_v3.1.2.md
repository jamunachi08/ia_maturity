# AlphaX IA Maturity v3.1.2 — Release notes

**Date:** 2026-11-17 · **Type:** fix release · **Schema changes:** none · **Patches:** none

## Why upgrade

Repairing the test suite on current Frappe exposed four defects that affect live sites. Two of them block sign-in.

| Problem | Who is affected | Fixed in 3.1.2 |
|---|---|---|
| Verification email never confirmed as sent (`sendmail(now=True)` now delivers after commit) | **Every customer** on an up-to-date v15/v16 bench: sign-up and sign-in by email code fail | Queue, then send inside the request with Frappe's own queue `send()` |
| 2FA challenge read with raw `cache.get` (Frappe now uses `set_value`) | **Staff with 2FA Enabled/Enforced**: every sign-in rejected | Read and clear both storage styles; challenge stays single-use |
| Patches are not run on a fresh install | **New GRC sites**: no Internal Audit default template; invited IA customers cannot start | Default set once at install (`install_type_defaults`) |
| Approval path skipped department rules added in 3.0 | **Manager-requested auditor onboarding** and **auditor-requested customer onboarding** fail on approval | New staff join only the departments the requester shares with the customer; new customers join the requester's department |
| Section chart too tall for six sections | **Internal Audit PDF**: scoring method on an almost empty page 2 | Chart rows 51→42 px, bars 27→24 px, cell padding 6→5 px |

Staff 2FA is off by default, which is why the 2FA defect went unnoticed; the email-code defect appears on any bench updated to current Frappe.

## Deployment (Frappe Cloud)

1. Push the release; Frappe Cloud installs requirements and runs `migrate`.
2. Check `bench --site SITE execute ia_maturity.grc.health.check` (`grc_enabled` true).
3. **Existing sites created fresh on 3.x:** if Internal Audit has no default template, run once: `bench --site SITE execute ia_maturity.install.install_type_defaults`. Upgraded sites already have it.
4. Smoke test: request a customer email code and sign in; sign in as a staff user with 2FA; open an Internal Audit report PDF (one page).

Frontend code is unchanged from 3.1.1; rebuild as usual.

## Verification performed

| Bench | Site | Result |
|---|---|---|
| Frappe 16.56.0, Python 3.14 | Brand-new site, `grc_enabled` set before install | 309 / 309 pass, twice in a row |
| Frappe 15.126.1, Python 3.12 | Brand-new site, `grc_enabled` set before install | 309 / 309 pass |

Both sites installed with a default template for each assessment type. Ruff is clean.

## Test changes worth knowing

- Security tests were not loosened. Where a test simulated an expired challenge with a raw delete, it now expires both storage styles, and the "challenge consumed" check reads both, so it can fail again (before, it could never fail on current Frappe).
- The legacy Internal Audit suites run with `grc_enabled` off for their duration, because those flows exist only on non-GRC sites.
- The delivery test now asserts the email is sent inside the request (queue `send()` called), not the old `now=True` argument.
