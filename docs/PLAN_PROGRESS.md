# Combined IA/GRC plan progress

## Admin controls and assessment guidance — 2026-11-14

The requested v3.1.0 changes add audited customer-verification limit controls,
missing-answer navigation, configurable organization yes/no presentation,
single first-time assessment selection, and new-user guide/tour defaults.
Existing personal preferences and default-enabled verification protections are
preserved. Local verification and release status are reported separately from
production deployment; the user deferred live deployment for this release.
The original plan's acceptance counts are unchanged by this additional work.
Local verification: 138 backend cases (verification controls, workspace
preferences, organization profile, signup throttling, verification email,
scope/onboarding and access), 83 mocked browser cases, and two guarded native
preference cases passed. The current frontend build and targeted lint passed.
The obsolete password-based customer preference test was superseded by the
OTP-aware native acceptance suite. Local `grc.local` mail remained muted.

Last updated: 2026-11-14. This file is the durable resume record for the user's coordinating chat. Refresh it after each verified milestone and reconcile current source/Notion before continuing.

## Performance implementation — 2026-11-13 (local acceptance passed)

The user approved the separate 50-concurrent-user plan and confirmed that DevOps
will run the prepared destination diagnostics. The user subsequently requested a 3.0.2 commit and push; destination deployment
remains separate. New epic and seven tasks:
https://app.notion.com/p/4175dea8d7ef812fa173ebcd0c7889b6. Preserve the original
feature epic, its statuses and its 13/49 Done count (10/46 original plus 3 additions).

Implemented public/portal route splitting, nonblocking approved-content startup,
single-flight visible-tab session refresh, serialized authentication mutations,
write-aware read-operation-local reuse, authorized SQL dashboard pagination/counts
and bounded activity previews. No private authorization or response is cached
across requests. Independent permission review found no new bypass.

The final candidate also fixes two measured startup regressions: the small Login
component is eager to avoid React's 300 ms Suspense fallback delay; language/RTL
attributes apply in useLayoutEffect before paint, with persistence unchanged.
English repeated login cohorts proved the eager fix; final Arabic login40 proves
CLS p75 of 0.00223 desktop/0.00313 mobile, down from failing 0.8879/0.1429.
Failed reports and prior builds remain archived, not relabeled as final acceptance.

Final functional checks pass: 227 unique backend cases across 14 suites, 101
mocked/retained browser scenarios and 13 native scenarios. Native coverage retains
all four self/invited IA/GRC journeys, clarification/resubmission/approval/release,
PDFs and registered-recipient MIME through the reserved sink, staff landing/MFA
and persisted EN/AR preferences. Build, targeted lint and formatting pass. Exact
logs and hash pointers: diagnostics/performance-20261113/functional-verification-manifest.json.
Only App.tsx and i18n.tsx differ from the backend-tested intermediate source;
backend continuity is verified by the source mappings. Mail remains muted and
native test policies/preferences are restored.

Five-run paired API comparison on 5x synthetic fixture growth preserves exact
sizes/hashes for nine dashboard cases. Baseline medians 3.96–11.53 s become
91.45–120.04 ms; query p95 9,057–40,991 becomes 144–270. Use
api-comparison-repeated-final.json; earlier single-baseline/wrapper reports are
diagnostic. Mandatory JS is 529,666 raw bytes versus 886,742 baseline; gzip build
estimates are 162,350 versus 266,693. CSS is 101,040 versus 140,317 raw bytes.

Final manifest: 353 source files, source SHA256
e8e61b10c37aad3d8fd2d0ccdd3469c46e3cb1d913c3e851404328256f1132ab;
55 assets, SHA256 7baf03088d7b0cddefccef9b3a7845d3574c6aaafcdea1feb76ead709c39cb25.
All 13 provenance/cache/retained-baseline preflight checks pass. No further app
edits or heavy functional suites are planned during timing/capacity acceptance.

Final settled-font EN480/AR160 browser gates pass on the frozen RTL build:
worst dashboard ready p95 2,163.9 ms, navigation p95 134 ms, public/login LCP p75
1,212 ms and CLS p75 0.09155707. Every expected font stylesheet has registered
and loaded successfully before LCP/CLS capture. Readiness uses four numeric cards,
the complete first page, enabled controls, no blocking overlay and two stable
frame intervals. Controller timings are retained separately; 19 observer guards
and delayed/error font-settlement probes passed. Do not compare old driver-ready
or font-unsettled measurements to final settled-font native clocks.

The FINAL asserted 50-client run passes: CLI exit0, 60-second ramp plus 1,800
steady seconds, 1,862.6 seconds elapsed, 86,519 total/85,036 steady requests,
0 HTTP/semantic errors or redirects including ramp, worst route HTTP p95
168.047 ms and unchanged runtime source. All 40 native sessions passed kind/user
validation during ramp/initial cycles; 10 clients are anonymous. No session or
policy renewal occurred during the timed run. A separate 8-observation under-load
admin/manager spotcheck passes: max complete dashboard 2,206.3 ms, navigation
132.4 ms. This is not a percentile cohort. All 160 quiet recovery requests and
13 source/assets/cache/retained-baseline checks pass; public304/private/error
no-store and actual gzip parity are verified. Matching baseline48 and settled-font
baseline-login40 diagnostics completed after the quiet recovery window. All
four final login groups improve: desktop cold/warm LCP p75 152→88/104→52 ms;
mobile cold/warm 1,112→752/392→248 ms. Both comparison processes exited 0.
The earlier 86,263-request pass remains archived intermediate evidence.

Notion now records PERF-02/03/04 Done and PERF-01/05/06/07 Review. The performance
epic remains In Progress for destination baseline/hosting/field/rollout gaps.
Actual dependency relations follow the plan; owners and due dates stay unset.
Original feature tasks are unchanged: 13 Done, 26 Review, 10 Not Started (13/49,
including 10/46 original plus 3 additions). S08.02 stays Review; S08.03 stays
Not Started, with performance evidence linked separately. Final sanitized results/DevOps attachments are linked in Notion; no new app
changes are planned.

Use PERFORMANCE_RESULTS.md and PERFORMANCE_OPERATIONS.md for the frozen accepted
evidence and commands. These are local synthetic measurements,
not destination capacity, field INP or real inbox verification. Destination host
baseline/serving checks, UAT and production rollout remain deferred to DevOps.
Release 3.0.2 packages these locally verified changes; no production deployment is claimed.

## Main plan and source authority

- Combined plan: https://app.notion.com/p/4155dea8d7ef8111b3e2c61cbbaa5da7
- Preserved Excel baseline: https://app.notion.com/p/4155dea8d7ef81fdb1e7f74f88e1df21
- Epic: https://app.notion.com/p/4155dea8d7ef812d828cce3ad2704d75
- Project: https://app.notion.com/p/4145dea8d7ef807096d4dc0dd48019b0
- Parallel lanes: https://app.notion.com/p/4155dea8d7ef81d8b2afc43336a0dc65
- Excel register (112 entries): https://app.notion.com/p/4155dea8d7ef81f080b5c91d67baa974
- DOCX register (79 entries): https://app.notion.com/p/4155dea8d7ef81d9b2d8ec8b6fd7dcf3

Sources: `C:\Users\kdpan\Downloads\GRC_Maturity_Questionnaire V1.0.xlsx` SHA256 `0b3da727eab7fd9042f5cadcc26dc43c30d3a8f774ffac759f4b24fd03867ab8`; `C:\Users\kdpan\Downloads\GRC Assessment Platform — Development Scope v1.docx` SHA256 `68ebf8fbbd01987d8a573a91105250d7b3485b585d308d2b2636b9b070d0c309`.

The original plan is retained. DOCX explicitly supersedes all-46 mandatory runtime scope with Awareness plus at least one chosen Governance/Risk/Compliance section. Full46 remains the complete-content oracle. Self signup chooses IA/GRC; invitations pin type. Profile is reusable organization data plus frozen submitted snapshots. Use13 named topics; the DOCX's15-topic note is inconsistent. IA20 and historical reports remain intact. HR release, payments and combined leadership dashboard are excluded.

## Current priority and progress

The final customer journey authorized on2026-11-12 is implemented and locally demo-validated. Current checkout is v2.17.0 plus uncommitted demo changes. Exact accepted leaves: **11/47 Done,26 Review,10 Not Started**; this is **10/46 original baseline Done plus1 new PDF attachment leaf**. The larger source backlog includes work beyond the final pasted demo journey. Notion hierarchy is reconciled:1 Epic,14 Sub-task,47 Task tags across62 records. The epic remains In Progress because broader original criteria remain.

Accepted demo cycle: all4 self/invited IA/GRC customer-to-auditor review/release paths plus two-manager second-type approval;36 browser scenarios total (15 journey UI,13 profile UI,5 live,1 targeted mobile preview,2 actual mobile rechecks). Backend:26 department/journey +8 instrument +12 identity/report +6 immediate email +8 original profile +79 retained access/security/history +20 retained scope/onboarding +5 classification +21 native MFA policy =185 tests, all passed.8 actual PDFs text-checked and16 released pages visually inspected, including full selected responses/scoring. Build/TypeScript, lint0errors/3 existing warnings, diff formatting and repeated migration passed. Local SMTP sink validates native immediate sending/MIME; real inbox delivery is not claimed. Retained79 access regressions passed without skips after aligning superseded password assertions and explicit department fixtures. A custom report-band color regression was fixed; the exact PDF color test passed again.

Runbook: `docs/DEMO_JOURNEY.md`. Current validation evidence: `diagnostics/demo-cycle-20261112/`, final browser run `mwdo2j8o`; complete source progress is `PLAN_BACKLOG.json`. Profile S03.01 is now Done: basics-only department grants cannot read/edit profile/regulator or full assessment/PDF artifacts, and historic snapshots remain frozen. Do not reopen completed Profile work.

No commit/push, version release or production deployment has been authorized for this demo work. The earlier profile-release authorization was scoped to v2.17.0. Original historical records below remain for traceability; this section and the final journey record are current.

## Profile phase baseline (2026-11-11)

User requested implementing Profile first: S03.01-S03.05. This reorders implementation priority without marking unfinished department/interface prerequisites complete. Implement current organization-authorized Profile capability; record any department-grant-dependent acceptance separately.

At implementation kickoff: v2.16.1, clean working tree, local grc.local preview HTTP200 on port8005. Profile implementation is locally verified and included in release v2.17.0. Engineering completion: **4/46 exact Done leaves;1 Review;41 Not Started**. Planning coverage191/191 is separate from implementation completion. The user authorized commit/push of the profile work on 2026-11-11; v2.17.0 packages this work. No production deployment has been performed.

| Task | Notion | Current state |
|---|---|---|
| S03.01 organization profile and snapshots | https://app.notion.com/p/4155dea8d7ef81d6822fe059f0a877f2 | Review: storage, snapshot/history and current organization authorization passed; future restricted department grants remain |
| S03.02 industries/sectors/Other | https://app.notion.com/p/4155dea8d7ef8162a11df5e318a4ca29 | Done, locally verified |
| S03.03 nationality/CR/MISA | https://app.notion.com/p/4155dea8d7ef81fbaf0dd5bd8d01e0b7 | Done, locally verified |
| S03.04 licenses/expiry/N/A | https://app.notion.com/p/4155dea8d7ef814185cdfd4124b4aaf7 | Done, locally verified |
| S03.05 regulators/responses | https://app.notion.com/p/4155dea8d7ef81adbb4ae90ef354594d | Done, locally verified |

## Profile acceptance

Required name, workbook industry and dependent sector, Other text when selected, and nationality. First3 nationality choices allow optional10-digit CR as text; fourth hides and clears CR. MISA applies to choices2/3/4. License text or explicit N/A is mandatory. Detail rows optional; every started row complete name/YesNo/expiry, Yes cannot have past expiry. N/A hides and excludes inactive detail rows without requiring deletion. General5 regulators plus sector override if key exists (including empty), otherwise industry fallback, plus nationality MISA. Optional regulator Yes/No and Other never change score/question scope. Organization profile reused for GRC; IA bypasses. All applicable validation on server and EN/AR UI.

## Verification and next action

Implemented company-profile service/catalog, structured Entity/license/regulator fields, authorized API methods, translated server validation, GRC scope/answer/submission gates, immutable profile snapshots and snapshot-only report context. Assessment classification is pinned so later template discovery changes cannot bypass the GRC gate. Added Company profile tab and GRC profile-before-questions UI, EN/AR validation, mobile wrapping and server-date expiry checks. IA bypasses this profile gate; personal-user profile APIs are unchanged.

Verified on grc.local (muted local site):

- `bench --site grc.local migrate`: passed, including repeated idempotent migration and classification backfill.
- `bench --site grc.local run-tests --module ia_maturity.grc.test_organization_profile --skip-test-records --skip-before-tests`:8/8 passed. Covers actual submission/snapshot/report history, Arabic validation, authorization/revocation, stale writes and workbook rules.
- Same command with `ia_maturity.grc.test_scope_onboarding`:20/20 existing regression tests passed.
- `npm run build`: production build and TypeScript passed; existing font asset path notices remain.
- `npm run lint`:0 errors,3 pre-existing warnings in PageTour.tsx, Templates.tsx and SiteEditor.tsx. Targeted changed-file lint passed0 errors/warnings.
- `npx playwright test organization-profile.spec.ts`:13/13 route-mocked actual-UI scenarios passed, including GRC gate/IA bypass and EN/AR320px/390px long labels. These mocks do not prove backend persistence.
- `GRC_RUN_PROFILE_LIVE=1 npx playwright test organization-profile-live.spec.ts`:1/1 unmocked browser/API/database round-trip passed. Test restored its changed value; the coordinator removed only its reserved organization/membership/transient activity fixture after verification.
- Exact ordered23 industry/278 sector,120 keyed override (including10 empty), industry-regulator and five general-regulator parity against the workbook audit passed. Git diff formatting passed.

Evidence: bench `diagnostics/profile-phase-20261111/` (backend and scope logs); `ui-mock-13/` contains JSON and six reviewed screenshots. Local preview was reloaded for new API imports and remains on8005 (task-owned server, no production action).

## Historical resume point (superseded by final journey below)

Read `PLAN_BACKLOG.json` and reconcile Notion before coding. Do not redo the completed Profile tasks. Next logical milestone is S00.01 shared interface/ownership contracts and S00.02 source-owner decisions, followed by S09/S10 department foundation/security. Then close S03.01's remaining basics-only shared-profile restriction acceptance. Other source assumptions include Director override operations, safe domain duplicate handling and IRSAA Arabic question content. Do not silently choose broader privileges or invent approved content.

The workbook importer/full46 questionnaire, topic/scoring/report changes, department invitations/sharing/revisions and final UAT/rollout remain pending per the46-leaf backlog. Profile-only validation does not certify the entire GRC instrument or production.

Do not count source-only code as verified. Do not mark S03.01 fully Done while future restricted department-share acceptance is still unimplemented. Commit/push is authorized for v2.17.0; deployment remains outside this request.

## Profile release verification (v2.17.0)

On 2026-11-11, release preparation reran 8 profile backend tests and 23 combined profile/scope browser tests successfully after the optional-section fix. Build/typecheck passed; lint has zero errors and three existing warnings. Source acceptance statuses and Done/46 counts are unchanged. See [release notes](RELEASE_v2.17.0.md).


## Final customer journey implementation (2026-11-12)

The user authorized end-to-end demo implementation, parallel independent agents, updating existing Notion tasks and adding uncovered tasks under the epic. The final pasted journey supersedes historical customer password requirements: customers use email OTP every sign-in; staff authentication remains password/MFA. Signup sector is deferred to GRC company profile. PDF emailing attaches the assessment PDF to registered customer email.

Notion hierarchy updated on all61 original records:1 Epic,14 Sub-task,46 Task tags. S11.01 and S11 renamed for OTP-only onboarding with explicit source amendment. New S07.04 PDF attachment delivery: https://app.notion.com/p/4165dea8d7ef81ae8c1efd09b3d0d850 under existing S07; baseline46 preserved,47 total leaves. Current accepted Done baseline remains4/46 until integrated checks accepted. No commit, push, production deployment or real inbox delivery is claimed.

Ownership: coordinator owns departments/security/invitation/API/setup integration; identity agent owns customer auth/MFA and report backend/PDF; instrument agent owns workbook/scoring/scope/schema metadata; frontend agent owns React and browser tests. Mutating local grc.local suites run serially.

Frozen demo contracts: bootstrap allowed_assessment_types, audit_type_access per entity, department_memberships, can_manage_departments. Department staff and customer grants are server-owned. Assessment grc_department/grc_assessment_type/grc_invited_sections/grc_invitation/report ID are pinned. Invitations store company, assessment_type, minimum_sections and inviting staff; email/company/type/minima immutable. request_audit_type requires source-manager approval then target-manager acceptance before new grant. Scope uses Awareness/Risk/Compliance/Governance codes. GRC requires Awareness + >=1 optional; IA skips scope. Profile APIs unchanged.

Initial checks: local migrate passed; exact46/184/13 source extraction and8 pure content/scoring/scope tests passed; frontend production build passed and9 mocked browser checks passed;10 identity/report backend +6 immediate-email tests passed. New department negative tests and final unmocked four-path demo cycle remain in progress. Keep fixtures/logs/PDF renders outside Git under diagnostics/demo-cycle-20261112. Local mail stays muted except isolated native SMTP sink test server; real provider delivery is separate.


User delivery decision (2026-11-12): skip real inbox delivery for now; test OTP/PDF delivery against the live provider after deployment. Local mail remains muted and native SMTP-sink validation is the accepted local scope. Do not ask for a recipient again during this task.


## Final accepted validation and handoff (2026-11-12)

The requested local demo implementation is complete. Final26/26 department/journey tests passed (`final-departments-backend-26.log`), including IA-only invitation email wording.8/8 instrument,12/12 identity/report,6/6 native immediate email,8/8 original profile and79/79 retained security/ERP/private-file/workflow/history tests passed:139 backend tests total. All79 retained cases were kept with no skips; obsolete customer-password/MFA assertions now test OTP-only denial and retain staff native MFA coverage. Exact custom/frozen report-band regression passed after preserving vector color bands behind HTML EN/AR labels (`final-report-color-backend.log`). No original released files were rewritten; fresh frozen-context IA/GRC render QA is in `actual-pdfs/frozen-color-qa.json`.

Frontend:36 scenarios passed (15 journey UI +13 original profile regressions +5 unmocked full demo +1 preview visibility +2 actual Arabic390px released-report checks). Final live run `mwdo2j8o`; `final-live-results.json`, `final-mobile-results.json`, `actual-pdfs/final-mwdo2j8o-pdf-qa.json` and `final-screenshots/` retain evidence.8 actual preliminary/released PDFs text-checked, all16 final released pages visually inspected, selected scope/response/scoring/profile parity accepted. Mobile inline PDF preview is hidden where unsupported; download/email actions remain.

Production build/TypeScript passed; lint0 errors/3 pre-existing warnings; Python compile and Git formatting passed; final migration repeated successfully. Local demo Before Audit, Preliminary scorecard, after-submission display and full report-detail flags restored after retained tests; emails remain muted. The acceptance server on8007 uses reserved non-network SMTP transport only. User explicitly deferred real provider/inbox testing until live deployment. No commit/push, new release or production deployment occurred.

Notion exact counts:11/47 Done,26 Review,10 Not Started; original10/46 Done plus1 additional PDF attachment task. All62 requirement records have correct Epic/Sub-task/Task tags and parent rollups. The broader epic remains In Progress. Review notes list the original unfulfilled criteria; do not interpret the local final-journey acceptance as full Excel/DOCX compliance or IRSAA business UAT.

Next: preserve accepted evidence/private local fixtures; wait for user instructions on commit/release/deployment or broader source work. Do not rerun accepted suites without a new change/failure, and do not request or send real test mail before live-deployment instruction.


Final affected-module maintenance: all20 original scope/onboarding,5 classification/default and21 central/native MFA-policy tests were preserved and passed without skips. These test-only alignments replace superseded customer-password assumptions, add explicit department fixtures, and retain historical IA scope/release and staff/ERP MFA coverage. No runtime changes were needed in this phase. Exact total is185 passing backend tests. Logs: `final-retained-scope.log`, `final-retained-types.log`, `final-retained-mfa-backend.log`. The central/native policy, original authentication-role memberships and local Before Audit/full-report flags were restored after tests (`mfa21-baseline-restored.json`); local mail stays muted. Final login/signup/bootstrap readiness checks returnedHTTP200. There is no remaining required implementation or validation for the requested local demo slice.

## Staff authentication amendment (2026-11-12, accepted locally)

User now explicitly requests staff 2FA disabled by default with admin role and
username controls. This supersedes the retained mandatory staff default above;
customers remain email OTP only, no password option. New S11.05 under S11:
https://app.notion.com/p/4165dea8d7ef81b5a019e0098b2d1b96. Original 46-leaf baseline
unchanged; 48 total leaves (12 Done,26 Review,10 Not Started). Original10/46 Done
plus2 additional Done leaves;63 hierarchy-tagged Notion records. S11 rolls up
1/5 Done and4 Review. Broader epic stays In Progress.

Backend coordinator owns policy precedence/native role synchronization and demo
configuration. Independent agents completed Account security UI/browser checks
and backend test updates/read-only review. Individual overrides win over role
policies; Required wins among multiple roles; roles override the global default.
Existing explicit and unrelated ERP requirements remain preserved. Mutating
backend suites ran serially.125 affected backend tests passed:28 staff MFA
(including legacy IA roles, native challenge/replay and current-admin logout),79
retained access/security/workflow/report tests,12 identity/report and6 immediate
email tests. Native Contact synchronization is isolated in the central-policy
test helper because its unrelated background retry runs synchronously in tests;
native MFA behavior remains unmocked. Initial fixture-only email/contact failures
were corrected; the final28-case run passed cleanly with no skips.

13 browser checks passed:11 mocked admin/precedence/customer/authorization/EN-AR
mobile/keyboard checks and2 unmocked native-browser scenarios. Actual admin role
Required and username Disabled changes were exercised, both department native
challenges verified, policies restored, and all6 manual staff password-only
logins proved. Build/TypeScript, targeted lint, Python compile, migration and Git
formatting passed. Evidence: `diagnostics/staff-mfa-default-20261112/` and
`diagnostics/demo-cycle-20261112/staff-mfa-frontend-{build,browser}.log`.

Local preview8007 restarted with current code; central staff default Disabled,
manual6 user policies Default/opt-in0. Customers remain email OTP only. The
demo guide, README, operations and MFA administration guide reflect the change.
No commit/push/release/deployment; real mail remains muted and inbox checks stay
deferred until live deployment. Previous185-backend/36-browser totals are the
earlier journey checkpoint;125/13 above are this amendment's affected checks.

## Staff first-login UX correction (2026-11-12, accepted locally)

User screenshot showed `/app/grc-staff` with Frappe chrome and empty selectors.
Root cause was Login.tsx explicitly overriding the server's custom staff home
when `staff=1`. Removed that override, completed staff role-home mappings, removed
the custom shell's Staff Desk link and added a non-cached authenticated legacy
302 redirect. IA-only staff branding now uses Internal Audit, not GRC.

Parallel UI owner added optional, per-user dismiss/reopen Getting started,
permission-based invitation/assignment links, clear empty-state next steps,
hidden empty filters and no Start assessment without an eligible organization.
Keyboard/Arabic/mobile were verified. Invitation permission follows the existing
department-only policy (including reviewers when server capability permits);
no new role restrictions were invented. Required customer OTP/profile/scope/
answer gates and ERP/tenant security are preserved. Guide and operations updated.

79 retained backend access/workflow/security/report tests passed.32 browser
scenarios passed:7 welcome mocks,4 real fresh-login/legacy redirect/invitation
cancellation/Arabic mobile cases,16 customer demo UI regressions,3 existing page
tour cases and2 actual native MFA/default-login cases. All6 manual staff accounts
still sign in with password only and land directly in the custom app. No skips in
the final accepted runs. Legacy test helpers/labels were aligned to the current
OTP-only customer and explicit staff sign-in flow. Desktop IA/GRC and Arabic390px
screenshots were visually inspected. Build/TypeScript, targeted lint0/0, Python
compile, Git formatting and clear-cache passed; local8007 server restarted.
Evidence: `diagnostics/staff-first-login-20261112/` plus
`diagnostics/staff-first-login-frontend-{build,browser,lint}.log`.

S11.06 Done: https://app.notion.com/p/4165dea8d7ef8150ba9fc81fb80ea9a8.
Tracker:13/49 Done,26 Review,10 Not Started; original10/46 Done plus3 additional
Done leaves.64 hierarchy-tagged records; S11 is2/6 Done and4 Review. Broader epic
remains In Progress. Source uncommitted; no release/push/deployment. Real inbox
delivery remains deferred and local mail stays muted. Fresh `landing20261112`
staff fixture is private; no customer invitation was sent by this validation.

## Eight-role IA/GRC UX review (2026-11-12, accepted locally)

Reviewed customer, consultant, reviewer and manager workflows in both audit
types. Fixed stalled profile/scope draft Continue, OTP/invitation recovery,
empty/filter/start guidance, save failure/exit behavior, unanswered-question
navigation, review/clarification/approval/release next steps, eligible first
assignment roster, management scope, two-manager next actors, type-specific
organization pages and scoped follow-up controls. Optional guidance/dialogs
have safe cancel/back/close paths; mandatory customer gates remain enforced.
Shared profile/preferences/security/help checked, bilingual guides regenerated.
Three independent agents owned customer/consultant, assessment/reviewer and
manager modules; coordinator integrated shared shell, translation and API work.

Final accepted counts:147 unique browser scenarios (140 mocked/retained+7 live)
and137 backend tests (30 department,79 retained access,8 profile,20 scope).
Native cycles cover self/invited IA/GRC, consultant/reviewer handling, actual
clarification/correction/resubmission for both types, preliminary/official PDF
download and reserved SMTP attachments, second-type approvals and cross-dept
denial. Two additional live manager cases check roster/cancel/type tabs/help.
No skips in final accepted runs; repeated rechecks are not double-counted.
TypeScript/Vite build passed; targeted lint21 files0 errors/0 warnings. All25
pages of four bilingual help PDFs rendered and visually inspected, with EN/AR
mobile screenshots reviewed. Evidence: `diagnostics/ux-role-cycle-20261112/`;
coverage and exact accepted logs: `UX_ROLE_REVIEW_2026-11-12.md`.

Notion was updated only after frontend acceptance. Existing affected tasks
received targeted evidence and current summaries; S08.02 records the full role
review and retains Review for broader unfinished criteria. S11.06 remains Done.
No new duplicate task or status inflation:13/49 Done,26 Review,10 Not Started;
original10/46 Done+3 additional Done;64 hierarchy-tagged records. S08 rolls up
1/3 Done,1 Review,1 Not Started including its existing migration/UAT leaf.
Broader concurrency/domain/invitation metadata/Director/selective-sharing/mixed
revisions/approved Arabic source/rollout criteria remain open as recorded.

Server8007 current; no schema changes needed for computed capabilities. Source
uncommitted; no commit/push/release/deployment. Local mail stays muted and real
inbox checks remain deferred by user until live deployment. Manual demo fixtures
remain separate from consumed final `uxliveb20261112` acceptance customers.

## Source packaging v3.0.0 (2026-11-12)

User requested the Frappe app commit workflow. Packaged the complete validated
journey/authentication/role UX changes as v3.0.0; major bump from2.17.0 reflects
customer password/API-token/session incompatibility and explicit staff department
entitlements. Versions aligned in Python/root/frontend/lockfile. Changelog,
README, release/upgrade notes and introduction architecture/entity/workflow
diagrams updated. Independent read-only review found no accidental private
credentials or runtime artifacts in pending source. Build/TypeScript and Git
formatting passed again after metadata/docs; accepted behavioral suites were
not repeated because implementation did not change. Build emits the existing
frontend chunk-size advisory; no build errors. Local commit/tag only; no remote
push, deployment or real inbox mail. Exact task statuses/counts unchanged.
