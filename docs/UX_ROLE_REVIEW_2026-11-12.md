# IA/GRC role UX review — 2026-11-12

The requested local UX review is complete for customers, consultants, reviewers
and managers in both Internal Audit and GRC. This is local acceptance of the
requested journey; the broader combined Excel/DOCX specification, business UAT
and production rollout retain their own unfinished criteria.

## Coverage and resulting behavior

| Role, IA and GRC | Screens and next steps validated |
|---|---|
| Customer | OTP signup/login, invited identity/type locks, company profile and section gates, dashboard/start/Continue, assessment save/resume/submit, clarification correction, results and preliminary/official reports |
| Consultant | Custom landing, assignment-scoped customers, invitation creation/cancellation, recoverable filtered/empty lists, assessment read-only/waiting states and report availability |
| Reviewer | Assigned work, Begin review, clarification/customer amendment/resubmission, approval and separate release, report timing/restriction guidance |
| Manager | Actual department management scope, oversight/first assignment, eligible same-department staff, two-manager second-type approval, organization type-specific tabs, scoped follow-ups and optional configuration |

Shared Getting started, help, profile/preferences, security and optional dialogs
were checked. Optional dialogs explain their purpose and provide close, cancel
or back actions; mandatory OTP/profile/scope/required-answer gates stay enforced.
IA-only screens and help avoid offering GRC choices. English and Arabic mobile
screens were visually inspected, including 390px layouts.

## Material fixes

- GRC drafts awaiting company profile/scope now expose Continue. Dashboard
  filters have distinct empty states and recovery; stale organizations do not
  populate an ineligible Start choice. Existing drafts avoid duplicate start
  prompts. Customers see the next actor after submission/approval/release.
- OTP screens explain expiry, resend and rate-limit retry. Invitation screens
  explain pending/closed/expired/inactive/invalid states. Cancelling an unsent
  invitation resets its type/minimum selections.
- Assessment guidance follows the actual state and capabilities, including
  fullscreen focus. Missing answers show a count and first-unanswered jump.
  Save and exit preserves dirty answers on failure, blocks failed-save exit and
  provides retry. Tested provided exits/navigation save work before leaving.
- Reviewer guidance distinguishes begin review, clarification, waiting,
  approval and release. Delivery guidance uses each action's actual policy and
  availability. Approval does not imply official release.
- Managers see their management scope, which includes department grants under
  the existing server policy. First assignment loads eligible staff rather than
  only staff already assigned elsewhere. Empty rosters and locked ownership
  explain who can act. Cancelling does not mutate assignments. Decision controls
  require an explicit server capability; source and target approvals are clear.
- Organization profile tabs/capabilities and follow-up editing match server
  access. IA uses audit issues; GRC exposes permitted company-profile views.
- Role guides and four bilingual downloadable help PDFs reflect the current
  journey, staff default-off 2FA, safe optional cancellation and separate report
  release. Scope illustrations show Awareness plus at least one optional section.

## Accepted validation

All final accepted test runs passed without skips. Counts below are unique
scenarios for this review, excluding repeated rechecks and earlier milestones.

| Validation | Accepted count |
|---|---:|
| Customer/consultant browser scenarios | 19 |
| Assessment/focus/presentation browser scenarios | 40 |
| Manager/oversight browser scenarios | 22 |
| Shared role guides/profile/preferences and retained UI scenarios | 59 |
| Live workflow/browser scenarios | 7 |
| **Total browser scenarios** | **147** |
| Department backend tests | 30 |
| Retained access/security/workflow/report backend tests | 79 |
| Company-profile backend tests | 8 |
| Scope/onboarding backend tests | 20 |
| **Total backend tests** | **137** |
| Bilingual help PDF pages rendered and visually reviewed | 25 |

The seven live scenarios include four self/invited IA/GRC customer cycles
through consultant/reviewer/PDF, actual IA/GRC clarification/correction/resubmit,
two-manager second-type approval and cross-department denial, plus two IA/GRC
manager roster/cancel/company-tab/help scenarios. All eight role/type combinations
are exercised across these scenarios. Native reserved SMTP verifies matching
preliminary and released PDF attachments; it does not establish real inbox
delivery. The final accepted live fixture run is `uxliveb20261112`.

TypeScript/Vite build passed. Targeted lint of 21 files returned zero errors and
warnings. Computed capability changes need no schema migration. Backend suites
were serialized on the shared local site. Development agents had separate
customer/consultant, assessment/reviewer and manager ownership; shared shell,
translation, API and help integration had one owner.

## Evidence and task reconciliation

Transient local evidence is in `diagnostics/ux-role-cycle-20261112/`:

- `customer-final.log`, `assessment-mocked.log`,
  `assessment-final-recheck.log`, `manager-mocked-accepted.log`,
  `common-final.log`, `common-roles-final.log`, `guides-accepted.log`.
- `live-cycle-final.log`, `manager-live.log` and `screenshots/`.
- `departments-backend-30.log`, `access-backend-79.log`,
  `profile-backend-8.log`, `scope-backend-20.log`.
- `frontend-build.log`, `lint.log`, `guide-qa/results.json` and rendered guides.

Initial test-only fixture/assertion failures were corrected before final clean
runs. Historical failed logs are not accepted evidence. Private credentials,
OTPs, invitation tokens and customer evidence are excluded from source records.

Notion updates began only after frontend acceptance. Existing S05.01, S05.03,
S07.02, S10.03, S11.01, S11.03 and S11.04 retain Review with exact remaining
criteria recorded. S08.02 records the full review; S11.06 stays Done. The S08
parent and epic summaries are current. No duplicate task was created; existing
Epic/Sub-task/Task tags and parent relations are retained.

Tracker remains **13/49 Done, 26 Review, 10 Not Started**: **10/46 original
baseline Done plus three additional Done leaves**, with 64 hierarchy-tagged
records. S08 remains one Done, one Review and one Not Started; its existing
S08.03 migration/rollback/UAT task was not duplicated. Broader concurrent-submit,
safe-domain, invitation metadata, Director/selective sharing, mixed revisions,
approved Arabic source and rollout criteria are not closed by this UX review.

[Validated review task](https://app.notion.com/p/4155dea8d7ef813e86ddd49ccd9d839a)
· [Project epic](https://app.notion.com/p/4155dea8d7ef812d828cce3ad2704d75)

This review was accepted before committing. The user subsequently requested
packaging the validated source as v3.0.0 with a local commit/tag; see the
[upgrade notes](RELEASE_v3.0.0.md). No remote push or deployment performed.
Local preview is on port 8007, outgoing real mail remains muted, and the user
explicitly deferred real inbox delivery checks until live deployment. The manual
demo fixture remains separate from the consumed acceptance customer cycles.
