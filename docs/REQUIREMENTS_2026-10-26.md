# Customer and staff requirements — task tracker

Requested: 2026-10-26. Status is updated only after implementation and relevant validation.

| ID | Task and acceptance criteria | Status | Validation |
|---|---|---|---|
| R1 | Registration: visible sign-in/recovery links; neutral response for all eligible/ineligible addresses; no claim that an unsent code was sent | Completed and validated locally | Backend neutral-response/cooldown and queue-failure tests passed; browser guidance and resend flow passed |
| R2 | Multiple memberships and roles; persistent top organization switcher; optional acyclic parent; parent admins read subsidiaries, explicit direct membership required for edits; tenant isolation on all record/file paths | Completed and validated locally | Cross-tenant, inherited read-only, revocation, cycle and direct API tests |
| R3 | Resend with server cooldown and expiry; actionable queue failure; inspect local sending/queue logs and document provider/DNS evidence needed for actual delivery diagnosis | App completed and validated; production investigation skipped | Backend/browser resend checks passed. Local email muted, scheduler inactive, 19 verification queues Not Sent; provider/DNS/spam checks skipped by user on 2026-10-26 |
| R4 | Customer role and membership identity without Desk; staff roles and separate Desk login; block staff customer signup; role-aware navigation | Completed and validated locally | Role boundary and HTTP tests; staff/customer routing |
| R5 | Authorized staff organization/assessment creation, customer admin invitation, answer entry with actor audit; consultant assignment/transfer reason and ownership history | Completed and validated locally | Assigned/unassigned staff tests, invitation and transfer history tests |
| R6 | Organization and user optional reminder/status controls, both must allow; security/verification/invitations/clarifications always mandatory; clear settings | Completed and validated locally | Preference matrix, mandatory clarification and customer settings browser checks passed |
| R7 | Detailed staff Desk timeline and sanitized customer timeline: answer/evidence/status/assignment/transfer actor, timestamp and change detail; exclude internal comments | Completed and validated locally | Timeline, file deletion, redaction and authorization tests |
| V1 | Migrate isolated test site; run relevant backend, HTTP, frontend lint/build and browser suites; inspect final diff | Completed and validated locally | Migration; 69 backend tests; 23 Chromium scenarios; both HTTP security suites; lint, TypeScript/build, syntax and diff checks passed |

## Decisions

- Adopt the proposed neutral registration response and read-only holding-company defaults.
- Inherited access follows active parent-admin membership through all descendants; direct subsidiary membership is explicit authorization to edit according to that membership role.
- Optional emails require both organization and user permission. Mandatory security, verification, invitations and clarification requests bypass optional preferences.
- Existing GRC staff are portal-only in v1.10. This requirement deliberately adds a restricted staff Desk entry and scoped GRC records; customer Desk access remains denied.
- No production deployment or real customer email is part of local validation.

## Evidence and progress

- Initial inspection: repository clean; React portal and Frappe GRC services already support multiple direct memberships, customer assignments, private evidence, activity records and user reminder preferences.
- Local operations documentation specifies muted emails and disabled scheduler on grc.local. Provider processing, recipient spam placement and production SPF/DKIM/DMARC require actual provider/domain evidence.


## Implementation notes

- Staff roles: GRC Manager, GRC Consultant and GRC Reviewer; GRC App Admin and GRC Auditor remain compatible aliases. IA Maturity Manager/Reviewer retain their staff classification.
- Staff Desk entry: /login?staff=1 -> /app/grc-staff. The dedicated Desk page exposes authorized activity and links to staff workflows. General Desk/ERP pages and generic document APIs remain denied to GRC accounts.
- Staff-created organizations assign their creator as a consultant, or as an organization manager when they have the Manager staff role. Staff-created assessments may await customer ownership; submission is blocked until a customer administrator accepts an invitation or a manager explicitly assigns an active customer owner.
- Existing consultants can transfer their own assessment to another consultant already authorized for that customer. Organization managers can allocate teams only within their active organization assignments. Global staff, MFA and application settings remain restricted to GRC App Admin. Transfers retain before/after ownership, actor, time and mandatory reason.
- Holding-company hierarchy changes require GRC App Admin. Active parent-admin membership grants descendant assessment reads. Direct subsidiary membership controls writes independently; revocation applies on the next request.
- Customers see summaries of changed question codes and evidence filenames. Staff see full before/after answer changes and internal review/transfer details. Review comments are customer-visible only when explicitly requesting clarification.
- Evidence attached to historical assessment revisions and completed/superseded actions is retained. Current evidence can be deleted through the scoped portal action and produces an activity event.

## Email investigation — local evidence

Read-only inspection on 2026-10-26 of the isolated grc.local database:

| Check | Observed |
|---|---|
| Outgoing accounts | 1; default outgoing account configured; no account awaiting a password |
| Sending | Muted by site configuration |
| Queue | 82 Not Sent; no Error queue records |
| Verification queue | 19 Not Sent, created 2026-10-24 13:23 through 2026-10-25 16:08 (site time) |
| Processing | Workers present; scheduler inactive; queue not suspended |
| App verification error records | 0 matching GRC verification errors |
| Provider acceptance/delivery | No records available in this workspace |
| SPF / DKIM / DMARC | Not verified; the actual production sender domain and DKIM selector have not been supplied |
| Recipient spam filtering | Not verified; recipient headers/delivery evidence unavailable |

This is evidence of local queue-stage non-delivery, not a diagnosis of the reported production delay. Email bodies, verification codes, credentials and recipient addresses were not copied to this document.

### Skipped task list — production email-delivery investigation

Skipped by the user on 2026-10-26. These checks are excluded from this implementation's completion criteria and may be resumed separately. No production access or delivery testing will be attempted.

Deferred scope:


1. Identify the affected production site, outgoing sender/domain, provider and approximate affected send times.
2. Correlate registration creation, Email Queue creation/send_after/error/retry and provider Message-ID records. Compare app enqueue time with provider acceptance time.
3. Inspect provider defer/bounce/delivery events to separate transport delay from provider processing.
4. Verify SPF includes the actual sending service, provider DKIM signing/selector, and aligned DMARC for the From domain.
5. Inspect recipient Authentication-Results/Received headers and spam placement. A Sent queue status proves only server handoff.
6. Send a controlled verification and resend to an approved test recipient, confirming actual expiry/cooldown and inbox timing. Do not unmute the disposable site's backlog.


- Approval review required a narrower Manager scope: the new Manager role does not receive global application administration. Organization Manager assignments authorize only that organization's staff allocation, assessment management and invitations. Global controls remain with GRC App Admin.


## Final validation — 2026-10-26

| Check | Result |
|---|---|
| Isolated grc.local migration | Passed; schemas, new fields and native staff Desk page installed |
| Backend integration suite | 69 tests passed |
| HTTP authentication/access acceptance | Passed: shared login, MFA, tenant isolation, ERP routing/denial, token denial, active-session revocation, secure recovery |
| HTTP profile/password acceptance | Passed: current-password checks, old-password rejection, session logout and retained staff MFA |
| Chromium end-to-end suite | All 23 scenarios passed, including the full verified-signup, save/resume, staff assignment, review, Arabic PDF and release journey |
| New browser workflows | Neutral signup/recovery, resend cooldown/expiry, restricted staff Desk, persistent organization switching and mandatory/optional settings passed |
| Frontend lint | Passed with 0 warnings and 0 errors |
| TypeScript/Vite build | Passed; existing font-path and chunk-size notices are non-blocking |
| Python and native Desk JavaScript syntax | Passed |
| Diff formatting | Passed |
| Visual review | Desktop organization switcher, native staff timeline, Arabic mobile signup reviewed; mobile overflow assertions passed |

Regression findings corrected before completion:
- Embedded assessment timelines no longer add a second page title.
- Test-only Redis counters are isolated for reserved fixture accounts, so repeated validation does not exhaust unrelated fixture limits.
- File deletion removes matching attachments on the authorized record and records activity, while shared/historical references remain protected.
- Managers stay organization-scoped; they cannot manage global staff, MFA policies or application settings.

## Rollout notes

- Implementation was validated locally before release preparation. The user subsequently authorized committing and pushing; v2.0.0 publication is recorded below. No production deployment is included.
- Build assets, migrate the designated site and restart backend processes together when deploying.
- Customer accounts require the GRC Customer role. An account with only stale GRC classification metadata or legacy customer roles remains restricted; an administrator must explicitly verify its role and membership.
- Organization Manager assignments grant authority only within that organization. GRC App Admin retains global administration.
- Production mail-provider timing, sender authentication and spam investigation is intentionally skipped as requested; see the separate skipped task list above.


## Remote publication

- User requested pushing the changes to the configured remote.
- Release version: 1.10.0 -> 2.0.0. Major version reflects customer-role enforcement and mandatory ownership-transfer reasons.
- Python/root/frontend/lock metadata aligned; changelog, workflow diagrams and v2 upgrade notes prepared.
- Publication targets: origin/main and annotated v2.0.0. Fetched main matched origin/main before preparation. Final commit and remote/tag verification are reported in the chat after push.
