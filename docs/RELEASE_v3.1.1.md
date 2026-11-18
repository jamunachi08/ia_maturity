# AlphaX IA Maturity v3.1.1 — Release notes

**Date:** 2026-11-17 · **Type:** stabilisation (patch) · **Schema changes:** none · **Patches:** none

## Why upgrade

| Problem in 3.1.0 | Effect | Fixed in 3.1.1 |
|---|---|---|
| `set_verification_limit_policy` ended with an undefined name | Every save of the customer email/IP verification-limit switches failed and was rolled back | Policy saves, is audited and returns the saved state |
| `save_staff` shadowed the translation helper `_` | Invalid email, ERP/customer-account conversion and self-demotion showed HTTP 500 instead of a message | Messages reach the admin; the guards were and remain enforced |
| `max(version)` field string in workbook scope setup | **App installation fails on Frappe v16** | Portable query |
| WeasyPrint 68+ removed `default_url_fetcher` | **GRC PDF reports crash** on benches with Frappe's pinned WeasyPrint 70.0 (v15 and v16) | Uses `URLFetcher(allowed_protocols={"data"})` on 68+, legacy path on 67 |
| `weasyprint>=67,<68` | Conflicts with Frappe's `WeasyPrint==70.0`; installing the app downgrades it | `weasyprint>=67,<71` |
| `/desk/grc-staff` not recognised | v16 auditor bookmarks were refused instead of redirected | Both `/app` and `/desk` paths handled |

## Deployment (Frappe Cloud)

1. Push the release to the deployment branch; Frappe Cloud installs requirements and runs `migrate`.
2. Confirm `grc_enabled` is still set on the GRC site (`bench --site SITE execute ia_maturity.grc.health.check`).
3. Smoke test: open an assessment report PDF; as a GRC App Admin, toggle a verification-limit switch with a reason and confirm it stays changed after reload.

The frontend must be rebuilt on the bench as before (`npm --prefix apps/ia_maturity/grc ci && npm --prefix apps/ia_maturity/grc run build`). No data migration is needed; rollback is redeploying 3.1.0, but note that 3.1.0 cannot render PDFs on WeasyPrint 70.

## Verification performed

On a clean Frappe **16.56.0** bench (Python 3.14, MariaDB 10.11) with `grc_enabled`:

- App installs and migrates; health check runs (non-production checks such as HTTPS/email are expected false on a test site).
- Full app suite compared with the original 3.1.0 code (given the one-line install fix it needs on v16) on an identical second site: **no regressions**.
  - Now passing: `test_switches_are_independent_and_audited` (verification-limit bug), `test_scope_is_retained_through_clarification_and_released_report` (PDF crash), and four new regression tests.
  - `test_report_a4_first_page_sections_and_escaping` moved from *error* (PDF crash) to *fail*: the stress fixture renders on 2 pages instead of 1. It does so on both WeasyPrint 67 and 70 in the test environment, so it existed before this release; confirm on staging with a real report.
- PDF fetcher verified on WeasyPrint 67.0 and 70.0: `data:` images embed; HTTP, file and stylesheet URLs are not fetched (a local listener received zero requests).
- Ruff clean; frontend `tsc`, oxlint and production build pass.

## Known issues carried forward (pre-existing, unchanged)

About 70 tests fail on v16 with the same results before and after this release. They are test-suite debt, not new defects:

- Fixtures post comments while question comments are off by default (33 errors: "Comments are disabled for question Q1").
- Test isolation: fixtures recreate the same organization membership (16 duplicate-key errors).
- Fixtures expect a default published template (7), Email Queue rows while emails are muted (3), and mock old Frappe email signatures (`add_css`, 2).

Making the suite green on v15 and v16 is recommended before Phase 2, so the new CI can block regressions.
