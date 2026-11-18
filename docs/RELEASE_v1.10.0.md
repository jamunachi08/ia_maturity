# v1.10.0 — Dedicated signup and organization information

[README](../README.md) · [Changelog](CHANGELOG.md) · [Developer guide](introduction.md#dedicated-signup-and-organization-details)

## Customer experience

Create an account now shows only the signup form. The Password/Email code tabs remain on normal sign-in.

Signup collects email, full name, organization name, sector and consent. After successful email verification, a new organization is created with the verified email as contact, and the new customer becomes its Organization Admin. The customer can start an assessment without re-entering organization details.

Existing organization names do not grant access or overwrite records. A customer joining one must accept an invitation. Pending invitations suppress automatic organization creation. Conflicts show authenticated setup with the customer's own submitted information and an invitation explanation.

## Backend and compatibility

All submitted organization fields are validated by the backend. Account/organization creation still requires a valid, unexpired, single-use email proof. MFA, profile-name protection, tenant isolation and ERP routing remain unchanged.

Migration adds grc_organization_sector and grc_organization_signup to IA Maturity Registration. Existing links and API clients that omit both organization parameters keep the previous manual onboarding flow after email verification. Historical registrations do not automatically create organizations or memberships.

## DevOps upgrade

From the bench root, after reviewing local changes and taking a backup:

~~~bash
cd ~/frappe-bench
bench --site grc.neotec.ai backup --with-files
git -C apps/ia_maturity status --short
git -C apps/ia_maturity fetch origin --tags
git -C apps/ia_maturity pull --ff-only origin main
git -C apps/ia_maturity describe --tags --exact-match
npm --prefix apps/ia_maturity/grc ci
bench build --app ia_maturity
bench --site grc.neotec.ai migrate
bench --site grc.neotec.ai clear-cache
bench restart
~~~

Verify v1.10.0, or a specifically reviewed later release. Use the production service/container restart equivalent where appropriate. Backend, migration and frontend assets must be deployed together.

## Acceptance

1. Open /signup and /login?signup=1: no Password/Email code selector appears.
2. Check organization name and sector on desktop and Arabic mobile layouts.
3. Submit incomplete organization data: the server rejects it before queueing verification email.
4. Submit valid signup details: only a pending registration exists before verification.
5. Verify the email: a new organization and Organization Admin membership appear, using the verified contact email.
6. Try an existing organization name and an invited email: neither bypasses invitation/membership controls.
7. Confirm existing customers and old verification links retain their intended access.
8. Check Back to sign in, Administrator login and required MFA.

Local validation: 50 backend integration cases, 19 browser scenarios, both HTTP suites, schema migration, lint/build and screenshot review. Production deployment and real inbox delivery remain DevOps acceptance steps.
