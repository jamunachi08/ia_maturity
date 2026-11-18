# Agent handoff and resume instructions

## Performance work accepted locally — 2026-11-13

The requested local implementation and testing are complete. User confirmed
DevOps will run destination commands. The user requested the 3.0.2 commit and push; no deployment is claimed.
The performance epic is https://app.notion.com/p/4175dea8d7ef812fa173ebcd0c7889b6.
Read PERFORMANCE_RESULTS.md and PERFORMANCE_OPERATIONS.md before historical notes.

Final frozen candidate: 353-source SHA256
e8e61b10c37aad3d8fd2d0ccdd3469c46e3cb1d913c3e851404328256f1132ab;
55-asset SHA256 7baf03088d7b0cddefccef9b3a7845d3574c6aaafcdea1feb76ead709c39cb25.
Only App.tsx/i18n.tsx differ from the backend-tested source; continuity is verified.
227 backend checks apply to unchanged backend, and 101 mocked plus 13 native
scenarios were rerun successfully on the final build. Build/lint/formatting pass.
No heavy tests need repeating without a new change/failure.

Final 640 settled-font browser observations pass: worst GRC dashboard p95
2,163.9 ms, warm navigation p95 134 ms, public/login LCP p75 1,212 ms and CLS p75
0.09155707. Complete first-page/controls readiness is browser-native; driver
outliers remain separately recorded. Nineteen readiness guards and stylesheet
load/error controls pass. Field INP is unmeasured. Final matching login groups
improve 32–50%; baseline48 remains N2 diagnostic per group, not a robust p95 claim.

Asserted 50-client read workload passes: 60 s ramp plus 1,800 steady seconds,
1,862.6 s elapsed, 86,519 total/85,036 steady requests, zero errors/redirects
including ramp, worst HTTP route p95 168.047 ms, source unchanged. Under-load8,
all160 quiet recovery requests and13 provenance/cache/rollback checks pass.
Earlier failed/intermediate reports remain archived and are not final evidence.

Task-owned servers8011–8014 are stopped; existing8007 preview, DB/Redis, muted
sites, synthetic clone and private fixtures/evidence remain. Never print private
fixture credentials/cookies/OTPs. The 3.0.2 release packages this work; the performance manifest identifies the pre-release tested build.

Notion: PERF-02/03/04 Done;01/05/06/07 Review for destination/field/rollout gaps.
Epic In Progress. Dependencies match the plan; assignees/dates unset. Final results
and functional manifest are attached to PERF-06; operations and separately
copyable read-only diagnostic source are attached to PERF-05. PERF-07 links rollback.
Original feature counts remain13/49 (13Done/26Review/10NotStarted;10/46original
plus3additions). S08.02 stays Review and S08.03 NotStarted with evidence links.
No remaining local work is required. Destination hosting, field metrics, UAT,
external inbox checks and production rollout remain for DevOps/release process.

Start by reading `PLAN_PROGRESS.md`, `DEVELOPMENT.md`, current Git status and the relevant Notion task. The existing chat is the user's coordinating home; do not create another chat unless asked.

## Release status

The user requested committing the validated journey/authentication/UX work on
2026-11-12 using the Frappe app commit skill. It is packaged as v3.0.0, following
v2.17.0. The major version reflects mandatory customer OTP and explicit staff
department entitlements. Python/root/frontend/lockfile versions are aligned;
README, changelog, architecture diagrams and `RELEASE_v3.0.0.md` are current.
Local commit/tag only; remote push, production deployment and real inbox checks
remain pending. Source-task acceptance counts are unchanged. Earlier statements
below about uncommitted source refer to the pre-commit validation milestones.

## Active assignment

Latest eight-role UX review accepted locally on2026-11-12. Customer, consultant,
reviewer and manager flows were checked for both IA and GRC; clear next actions,
empty/error recovery and optional cancellation fixed. See
`UX_ROLE_REVIEW_2026-11-12.md` for the coverage matrix and exact limits.
147 unique browser scenarios (140 mocked/retained+7 live),137 backend tests,
25 bilingual help PDF pages visually reviewed; build/TypeScript and targeted
lint21 files0/0 passed. Final accepted runs have no skips. Evidence is in
`diagnostics/ux-role-cycle-20261112/`; final native fixture `uxliveb20261112`.
Original failed test-only logs are historical; use final accepted logs.

Notion updated only after frontend validation: S05.01/S05.03/S07.02/S10.03/
S11.01/S11.03/S11.04 remain Review with precise open original criteria;
S08.02 has full evidence, S11.06 stays Done, parent/epic summaries current.
No new task:13/49 Done,26 Review,10 Not Started;10/46 original+3 additions,
64 tagged records. S08 has3 original leaves including existing S08.03 migration/
rollback/UAT Not Started; do not duplicate it. Broader scope is not complete.

Current server8007 has accepted code/assets; source uncommitted, no release or
deployment. Manual fixture is separate from consumed live acceptance customers.
Real email remains muted and user-deferred until live deployment. Staff2FA
default Disabled and manual6 password-only unchanged. Do not repeat accepted
suites without new changes/failures. Next work needs a new user instruction
for broader criteria, release or deployment. Earlier milestones below retain
their historical totals and do not supersede this latest checkpoint.

Latest first-login fix accepted locally: staff now land directly in custom
`/grc/auditor`; old `/app/grc-staff` redirects302/no-store for authenticated staff.
No Staff Desk link, IA-only staff branding, clear optional dismiss/reopen Getting
started, no empty selectors or unavailable Start action.79 access backend +32
browser checks passed (including customer/tour/native-MFA regressions); all6
manual staff password-only logins remain valid. Evidence and exact details are
in PLAN_PROGRESS's latest section and `diagnostics/staff-first-login-20261112/`.
S11.06 Done. Current tracker13/49 Done,26 Review,10 Not Started (10/46 original +3
additional Done),64 tagged records; S11 is2/6 Done and4 Review. Earlier counts
below are historical. Source uncommitted; server8007 current; no real email or
production action. Use current custom landing in future tests, never accept the
old Desk page as a successful staff landing.

Latest amendment accepted locally: staff2FA defaults Disabled; app admins have
global, role and individual username controls. User overrides win, then roles
(Required wins multiple roles), then global default. Customers still use email
OTP every sign-in and have no password option.125 affected backend and13 browser
checks passed, including real admin changes/native challenges and all6 manual
staff password-only logins. See PLAN_PROGRESS's latest section and
`diagnostics/staff-mfa-default-20261112/`. Manual fixture run `manual20261112`
remains available; only staff policy changed, customer flows were not consumed.
Server8007 restarted; mail stays muted. S11.05 Done in Notion; exact tracker now
12/48 Done,26 Review,10 Not Started (original10/46 +2 additional Done),63 tagged
records. Earlier totals below are historical checkpoints. No commit/deployment.

Final pasted customer journey is locally implemented and demo-validated on2026-11-12. See `PLAN_PROGRESS.md` and `DEMO_JOURNEY.md` first. All4 self/invited IA/GRC customer/auditor cycles plus second-type two-manager approval passed.36 browser scenarios and185 backend tests passed; full-detail PDF QA inspected16 pages. All79 retained access/security/ERP/history regressions passed with no skips after explicit department fixtures and OTP-only assertion alignment. The custom/frozen report-color regression was fixed and rechecked; see PLAN_PROGRESS for exact evidence. Current code remains uncommitted v2.17.0 working changes; no release/push/deployment authorization.

Notion:11/47 exact Done,26 Review,10 Not Started; original10/46 Done plus S07.04 attachment addition. All62 requirement records have Epic/Sub-task/Task tags. S03.01 is now Done after basics-only profile/artifact restrictions were verified. Broader original criteria remain open: approved Arabic GRC content, configurable department capabilities/Director/HR-inactive foundation, selective grants/transfers, domain checks, advanced import/operator workflow, sticky topic progress, extra invitation template/reviewer/due metadata and section expansion/revision/thread history. They are not required to falsely complete before reporting the validated final demo slice, and must not be marked Done without full acceptance.

Acceptance server is loopback port8007, reserved SMTP sink only; site remains muted. Final fixture credentials are private under the local site and must never be printed or committed. The user explicitly deferred real inbox delivery until live deployment on2026-11-12; do not request a recipient again or unmute/send external mail during this local demo work. No further app source changes are planned except actual regression fixes. Browser/mobile bug fixes: invitation completion must use full navigation after access version changes; hide unsupported inline PDF preview on small screens while retaining actions.

Coordinator owns department/security/invitation/API/setup; other agent file ownership has finished. Mutating suites must remain serialized. Update Notion and both local progress records after verified changes; do not rerun accepted flows without a new change/failure.

## Implementation contract

Company profile is distinct from personal-user `grc/profile.py` and `api.save_profile`. Implemented RPCs: `api.profile_catalog()`, `api.organization_profile(entity)`, `api.save_organization_profile(entity,data,modified=None)`. Server profile keys: organization, industry_type, industry_sector, other_sector, company_nationality, cr_number, ksa_license_type, ksa_license_na, ksa_license_rows[{license_name,valid,expiry_date}], regulators[{name,answer}], other_regulator. Envelope: profile, modified, can_edit, complete. Catalog: industries[{name,sectors}], nationalities[{name,ask_cr,add_misa}], general_regulators, industry_regulators, sector_regulators keyed Industry|Sector, and fresh server_today. Reconcile actual source implementation before extending it. Assessment payload profile_required gates incomplete GRC drafts; server guards scope, answer saves and submission. grc_assessment_type is pinned; grc_profile_snapshot is immutable after submission. Existing histories use snapshots in report context.

## Historical Profile-phase boundaries

- Backend owner: company-profile service/catalog, DocTypes, organization/API/security integration and meaningful backend tests. Preserve existing permissions.
- Frontend owner: OrganizationProfile component, organization and GRC assessment integration, styles and EN/AR behavior; no backend edits.
- QA owner: dedicated organization-profile browser scenarios and independent review; no application edits.
- Coordinator: shared contract resolution, serialized fixture execution, code review, Notion updates and this progress/handoff record.

## Local environment

Bench `/home/frappe/frappe-bench`, WSL `alphax_bench`, OS user frappe. Local grc.local preview8005/database13306. Follow GRC_OPERATIONS. Default Windows sandbox WSL access may fail; authorized elevated `wsl -d alphax_bench -- bash -lc '...'` execution worked in this session. Node path inside WSL is `/home/frappe/.nvm/versions/node/v24.18.1/bin`. Never inspect or print credential files into output; existing guarded test helpers may read local reserved fixture credentials internally.

Before stopping, record changed files, commands/results, unresolved failures, Notion statuses, exact Done/46 count, and the next executable step. An incoming agent must not re-run already accepted work unless new changes or failures justify it.


Final outcome: requested local demo flow complete. Current source is uncommitted. Server8007 uses reserved native SMTP sink; real mail deferred by user until live deployment. All185 backend/36 browser checks, migration/build/formatting and full-detail PDF QA passed. Preserve the47-leaf tracker and broader uncompleted scope.

Retained affected suites also accepted:20 scope/onboarding +5 classification +21 MFA policy, no skips or runtime changes. Total185 backend +36 browser scenarios pass. All test-local policy/auth-role/report changes restored. No further required work for the local demo slice; broader source task statuses remain authoritative.
