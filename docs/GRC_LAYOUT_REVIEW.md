# GRC page and role layout review

## Scope

Reviewed on disposable `grc.local` at desktop 1440px and mobile 390px, in English and Arabic RTL. The main pass covered 99 role/route combinations (303 screenshots), a tab pass covered 255 views, and public/access pages added 48 views. These passes reported no document-width overflow, page errors or error alerts. Scrollable tables and tab strips are intentional and remain within the page width.

| Audience | Main route combinations | Main views | Tab views |
| --- | ---: | ---: | ---: |
| Customer organization administrator | 13 | 39 | 24 |
| Assigned auditor / consultant | 17 | 51 | 54 |
| Reviewer | 12 | 36 | 21 |
| GRC administrator | 35 | 108 | 78 |
| GRC manager presentation | 22 | 69 | 78 |

Customer, auditor, reviewer and admin use actual disposable-site accounts. Manager layout uses the admin demonstration data with manager bootstrap capabilities; this is presentation coverage, not an authorization test. Backend access tests separately exercise role boundaries. Membership-specific action availability and scope-selection states are covered by existing browser/backend regression suites.

## Page inventory

- All roles: overview, assessment list and detail, actions, activity/dates, profile, account security and workspace-preference tabs, notifications, Help.
- Customers: scorecards, organization profile/departments/members/invitations/issues, onboarding resume/empty states and scope confirmation.
- Auditor/reviewer: assigned customers and details, follow-ups, onboarding tracker and invitation details; consultant and reviewer assessment controls.
- Managers/admins: oversight customer/auditor/approval tabs, audit-package selection and configured editor, assessment display and report colors.
- Admin: ownership defaults and customer ownership, assignments, staff, questionnaire list/new/draft/published/preview, account security, settings, consultations and website content.
- Public/access: login, signup, password-update entry, onboarding-link error state, signed-out demo access, landing, services, catalogue, frameworks, about, resources, FAQ, contact, privacy and terms. Valid signup/MFA/onboarding controls also retain their existing browser coverage.

## Findings corrected

1. Mobile tables squeezed names and emails into unreadable fragments: minimum table/first-column widths retain readable content within horizontal scroll regions.
2. Header controls wrapped unevenly: mobile uses a two-column control grid beside the menu button, mirrored in RTL.
3. Long Help setup text overflowed flex children: allow children to shrink and wrap code/text; stack the guide picker on mobile.
4. Workspace preferences had inline checkboxes/save actions: use spaced checkbox rows and a separate save button.
5. Assessment-display controls lacked form spacing: apply shared form layout with a separate action.
6. Ownership/onboarding consent and progress controls needed separation: checkbox cards, aligned milestone timestamps, and spaced action groups.
7. Signed-out demo content touched the viewport corner: center it in a padded panel.

## Reproduction

From `apps/ia_maturity/grc`, with the local preview server running on port 8005:

```bash
node scripts/audit-layouts.cjs
node scripts/audit-layouts.cjs all tabs
node scripts/audit-public-layouts.cjs
```

These read-only scripts require the existing private local demo credentials and local OTP helper. They save screenshots and JSON manifests under `sites/grc.local/private/layout-review`; no credentials or screenshots are committed. Do not run them against production. Browser/backend suites sharing this site must run sequentially because they share database/cache state.

[Release notes](RELEASE_v2.16.1.md) · [Feature introduction](introduction.md#customer-assessment-dates-v2161) · [README](../README.md)
