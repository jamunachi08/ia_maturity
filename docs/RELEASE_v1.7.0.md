# v1.7.0 — Public journey, ERP previews and reliable PDFs

[README](../README.md) · [Changelog](CHANGELOG.md) · [Introduction](introduction.md) · [Operations](GRC_OPERATIONS.md)

## Scope

Fixes the reported ContentNotFoundError / “broken image links” error when downloading **IA Maturity Report** or **IA Maturity Internal Report** through Frappe's standard PDF endpoint. The failure was reproduced through the production UI on **grc.neotec.ai**, running v1.6.0, with assessment **IAMA-2026-00001**. No production records or settings were changed during diagnosis.

App-owned report HTML, logos and fonts are rendered without Frappe's general print wrapper or website asset URLs. WeasyPrint replaces wkhtmltopdf for these two formats and legacy email attachments, preserving content settings, internal-only access, English/Arabic layout and permissions. Other DocTypes and formats continue through Frappe's PDF method. Existing GRC releases return their frozen private PDF and are not regenerated.

Adds a Saudi-inspired green/sand website, English/Arabic navigation, direct /signup, mobile navigation and guidance through the complete customer journey. This design does not claim government affiliation, certification or formal standards conformance.

Separate fictional, read-only ERP previews are available at /grc/demo/customer and /grc/demo/auditor. They grant no customer/auditor permissions and query no real organization or assessment records. Normal ERP users retain their existing login destination.

## Prerequisites

- Supported Frappe v15 bench; validation used Frappe 15.118.0 / ERPNext 15.119.3. GRC on Frappe v16 remains unverified.
- Python 3.10+ and Node 24, matching the existing frontend requirements.
- **WeasyPrint 67.x**, now declared in pyproject.toml. Native dependencies include Pango 1.44+. Use the [official distribution-specific installation instructions](https://doc.courtbouillon.org/weasyprint/v67.0/first_steps.html).
- On supported Ubuntu/Debian, native packages typically include libpango-1.0-0, libpangoft2-1.0-0, libharfbuzz-subset0 and the distribution's HarfBuzz package. Install through your normal package-management process.
- Transactional email, workers and scheduler for actual verification delivery and reminders. Local tests use a muted queue and do not establish production delivery.

## Upgrade from v1.6.0

Run from the production bench as its Frappe OS user. Substitute the actual site-directory name if it differs from grc.neotec.ai. Review local changes before updating; do not reset or force-push.

```bash
cd ~/frappe-bench
bench --site grc.neotec.ai backup --with-files
git -C apps/ia_maturity status --short
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity switch main
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity describe --tags --exact-match
./env/bin/pip install -e apps/ia_maturity
./env/bin/python -m weasyprint --info
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
```

The release tag is **v1.7.0**. If main has moved beyond it, deploy the reviewed tag through your normal release workflow rather than assuming latest main is identical.

### Activate the GRC homepage on the designated site

The production root displayed the legacy assessment landing page during diagnosis. GRC activation is explicit and site-specific:

```bash
bench --site grc.neotec.ai set-config grc_enabled 1
bench --site grc.neotec.ai migrate
bench --site grc.neotec.ai clear-cache
bench restart
```

This changes **that site's** homepage to grc-site, enables React login/signup and GRC security, requires staff MFA, and replaces generic signup with verified customer onboarding. Subsequent install/migrate on an already enabled site reapplies the GRC homepage. Unrelated sites are not enabled and their homepages are unchanged.

Before first activation, review existing legacy users, roles, organizations and assessments using the [v1.6.0 migration checklist](RELEASE_v1.6.0.md). Legacy assessments are not silently converted into GRC assignments. Infrastructure operators retain separate ERP/platform accounts. Preserve a working platform-administrator session while configuring GRC staff.

Configure HTTPS and the canonical host_name through the normal reverse-proxy/site process, then use that HTTPS URL for verification links. The incident was observed over HTTP; TLS and email are not assumed complete. Disable allow_tests and developer_mode in production and review recipients/delivery before unmuting mail.

## Post-deployment verification

1. Confirm version 1.7.0, built assets and homepage. Run: `bench --site grc.neotec.ai execute ia_maturity.grc.health.check`.
2. Open /, /login, /signup, public pages and nested routes directly, then refresh. Check English, Arabic and mobile.
3. As an authorized legacy/platform user, retry client/internal PDF buttons on IAMA-2026-00001 in both languages. Confirm unrelated ERP print formats still work.
4. Register through an actually delivered email code/link; create an organization, answer 20 questions, save/reload and submit. Final PDF must be unavailable before release.
5. As GRC admin, assign customer consultants/reviewers and allocate the assessment team. Use staff MFA to review, approve and release. Check the customer's approved scorecard and PDF.
6. Verify unassigned auditors and other customers cannot access the assessment/private PDF. Revoke an assignment and retry from an existing session.
7. ERP login must retain its existing destination. Open both demo links in the public footer; verify fictional data only.
8. Verify SMTP delivery, jobs, Arabic PDFs, protected files, backups and restoration monitoring. Health checks supplement these checks.

## Validation and limits

- 27 backend integration tests pass, including offline PDFs, release gating, immutable artifact reuse, document permissions, external-resource rejection, core delegation and site-scoped homepage setup.
- All 12 browser scenarios pass. Coverage includes actual queued single-use verification, organization setup, all 20 answers, save/reload, submission, customer/team assignments through admin UI, staff MFA, review, approval, release and PDF download.
- Public navigation, Arabic mobile, ERP previews and existing dashboard/profile controls are covered.
- Real HTTP suites pass for ERP/token denial, active-session revocation, MFA, password recovery and profile changes.
- English/Arabic client/internal PDFs generated with an unreachable host_name; rendered pages inspected for layout.
- **DevOps will install this update and perform production acceptance. Production deployment has not been performed by this change.**

The specific missing resource URL in production was not established. The fix removes site-resource fetching from the affected path. Site-customized versions of these two formats that reference external assets fail with an explicit diagnostic.

## Rollback

Back up site configuration, database and private/public files before activation. For code-only rollback, deploy the prior reviewed tag and rebuild assets through your normal workflow. If GRC was newly activated, code rollback alone does not undo roles, homepage, MFA or configuration: use the pre-activation backup and [restoration procedure](GRC_OPERATIONS.md). Never replace production with local fixtures or demo credentials.
