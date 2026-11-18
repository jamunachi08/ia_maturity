# Release v2.6.0

[README](../README.md) · [Changelog](CHANGELOG.md) · [Developer introduction](introduction.md)

This release adds personal Help and page-tour visibility controls and corrects assessment notification failures and MFA session invalidation.

## User changes

Open **My profile → Workspace preferences**. **Show page tour button** and **Show Help button** can be changed independently for the signed-in account. They default to visible. Hiding the page tour also stops automatic tours. Preferences persist across sign-ins and browsers and can always be restored from the profile.

The new settings are available to customer and auditor workspaces, including GRC reviewers and administrators. They do not require an administrator to unlock personal details. Existing browser tour progress and automatic-tour opt-out are retained.

## Fixes

- A customer submitting an assessment could receive **Administrator is not a valid Email Address** because workflow notifications treated the built-in User ID as an email address. Standard framework accounts are excluded, enabled recipients' email addresses are validated separately from their User IDs, and expected address/configuration failures are recorded without failing the assessment transaction.
- Central MFA changes and optional enrollment now log out the initiating HTTP request after stored-session invalidation. A changed policy requires a fresh sign-in with the selected method; an unchanged policy keeps the current session.

## Upgrade

Migration adds User.grc_hide_page_tour and User.grc_hide_help with visible-by-default behavior and preserves saved preferences. Build the frontend so the profile controls and header use the new settings. This release changes no dependency requirements or lockfiles; use the existing supported frontend toolchain.

Run from the bench with the correct production site name and a clean app checkout:

```bash
set -e
cd /path/to/frappe-bench
SITE="YOUR_LIVE_SITE"

test -z "$(git -C apps/ia_maturity status --porcelain)"
bench --site "$SITE" backup --with-files
bench --site "$SITE" set-maintenance-mode on

git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity merge --ff-only v2.6.0

npm --prefix apps/ia_maturity/grc ci
npm --prefix apps/ia_maturity/grc run build
bench build --app ia_maturity
bench --site "$SITE" migrate
bench --site "$SITE" clear-cache
bench restart

bench --site "$SITE" set-maintenance-mode off
bench version
```

If a command fails, resolve it before taking the site out of maintenance. After deployment, verify a customer submission, reviewer clarification/resubmission, released PDF access, and one central MFA change. Save and restore the two visibility controls from both customer and auditor profiles, then check a fresh sign-in. Confirm actual customer SMTP delivery using the site's normal mail configuration.

## Validation

The final release passed 135 distinct backend cases: 134 in the broad run and the authenticator replay case after fixing its test clock step. The restored customer-database audit and visibility feature checks covered 37 distinct browser cases, 52 additional HTTP checks and two security HTTP scripts. Both customer and auditor visibility journeys, six existing Help/page-tour cases, isolated site migration, and release-candidate and working-checkout frontend builds passed.

Coverage includes evidence isolation, stale saves, clarification and retained attachments, review/approval/release, frozen PDFs, action verification, follow-ups, password recovery, API-token denial, authenticator login, native email-code delivery to loopback SMTP, optional enrollment and central policy transitions.

Some isolated UI tests use mocked responses; full customer submission/review/release and central MFA transitions used the real application endpoints. External SMTP/inbox delivery, production workers, load and every concurrency interleaving are outside this local audit.
