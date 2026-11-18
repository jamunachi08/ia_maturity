# Release v3.0.0: IA/GRC customer journey and role UX

Customers use email OTP for signup and every later sign-in. Self-signup chooses
Internal Audit or GRC; department invitations pin recipient, company, audit type
and minimum scope. GRC requires the reusable company profile, Awareness and at
least one other section. IA retains its direct 20-question journey. Submission
shows preliminary results and a matching report, followed by assigned reviewer
clarification/approval and a separate official release. Authorized email delivery
attaches the PDF to the registered customer email.

Staff land in the custom workspace. Every IA/GRC customer, consultant, reviewer
and manager path has capability-aware next actions, meaningful empty/error states
and safe cancellation for optional steps. Four bilingual PDF guides accompany
the revised help. Staff2FA defaults Disabled; app admins can configure global,
role or individual username rules. Customers have no password option.

## Breaking changes and upgrade preparation

Version2.17.0 becomes3.0.0 because customer authentication and staff entitlement
behavior change. This version does not declare the broader source backlog done.

1. Back up the target site's database, private/public files and encryption key.
   Rehearse upgrade and restore on an isolated copy before production rollout.
2. Inventory existing customers, historical assessment types, organization
   assignments and IA/GRC staff. Customer password/API-token integrations need
   replacement; pre-OTP customer sessions are rejected at the next guarded
   request. Customers must have access to their registered inbox.
3. Record each staff member's department and Consultant/Reviewer/Manager
   responsibility explicitly. Existing role names are not accepted as proof of
   department membership. App admins retain configuration access; staff without
   active department membership will have no department work after upgrade.
4. Verify production outgoing mail and immediate-send behavior before enabling
   customer access. OTP is sent synchronously through native transport; ordinary
   invitation/report jobs still need the normal workers/scheduler. SMTP acceptance
   alone does not prove inbox delivery. Local acceptance used only reserved test
   mail; real inbox delivery is explicitly deferred until live deployment.

## Deployment procedure

These are operator instructions, not actions performed by this commit.

1. Install this revision, install the app dependencies with the supported
   Frappe15/Node24 environment and run `bench --site YOUR_GRC_SITE migrate`.
   Setup remains gated by the site's existing `grc_enabled` activation.
2. Migration adds GRC Department, GRC Department Staff, GRC Department Grant and
   GRC Audit Type Request DocTypes plus department/source/scope fields. Missing
   historical customer grants are derived from their own assessments; existing
   populated department values/grants are preserved. Staff memberships are not
   inferred or silently granted. Review ambiguous legacy records explicitly.
3. GRC setup installs the independently versioned46-question workbook seed;
   IA20 and already-submitted snapshots/released report bytes remain unchanged.
   Review active/default templates per type and the mandatory/optional sections.
   The source GRC question content is English; Arabic UI/help validation is not
   approval of an Arabic translation of the questionnaire source.
4. Through the app's authorized administration path, configure staff department
   memberships and verify active company grants, assignments and named reviewers.
   Configure manager membership as an app administrator, then check both manager
   request stages. An existing company grant is not an automatic cross-department
   assessment permission.
5. Review Account security before reopening staff access. New/unconfigured
   staff defaults are Disabled; explicit existing global/user/role policies and
   unrelated ERP MFA coverage are preserved. Username overrides win over role
   policies; Required wins across multiple roles; roles override the global
   default. An Enabled global policy permits voluntary staff enrollment;
   Enforced requires it by default. Policy changes require admin password
   authorization and may revoke affected sessions.
6. Run `bench build --app ia_maturity`, clear site caches and restart services
   using the site's normal deployment process. Verify the custom staff home
   `/grc/auditor`; authenticated legacy `/app/grc-staff` bookmarks redirect with
   a non-cached302 response.
7. Perform customer/auditor/manager UAT for IA and GRC. Verify self/invited
   identity locks, save/resume/required answers, selected-scope results,
   clarification/resubmit, preliminary/official PDFs, cross-department denial
   and source-manager then target-manager additional-audit approval. Test real
   OTP and PDF inbox delivery on live configuration as requested by the user.

Rollback requires the rehearsed backup/restore process with matching app code;
checking out old code alone does not undo new department/authentication state.
Do not delete grants, response snapshots or released artifacts as an ad hoc fix.
The broader migration/maintenance/rollback/UAT task remains unfinished.

## Validation and limits

Latest role review accepted147 unique browser scenarios:140 mocked/retained
and7 live, covering all eight role/type combinations, plus137 backend tests.
All25 pages of the four bilingual help PDFs were rendered and visually reviewed.
Build/TypeScript, targeted lint21 files0 errors/0 warnings and Git formatting
passed. Earlier journey, immediate-mail and staff2FA milestones have separate
evidence; counts are not added across overlapping runs.

The exact source tracker remains13/49 Done,26 Review,10 Not Started:10/46 of the
original baseline plus three additional Done leaves. Approved Arabic source,
safe domain/concurrency criteria, richer invitation metadata, advanced import,
Director/selective sharing/transfers and mixed-version section revisions are
among the unfinished broader requirements. See the authoritative task records.

No production deployment or external mail was performed. Local demo credentials,
OTPs, invitation tokens, traces and site configuration are outside source control.
The guarded demo fixture and acceptance SMTP runner must never run on production.

[README](../README.md) · [Changelog](CHANGELOG.md) ·
[Architecture and workflows](introduction.md#iagrc-customer-and-staff-journey-v300) ·
[Demo runbook](DEMO_JOURNEY.md) · [UX evidence](UX_ROLE_REVIEW_2026-11-12.md) ·
[Progress](PLAN_PROGRESS.md)
