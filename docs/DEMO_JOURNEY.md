# IA/GRC customer journey demo

This runbook covers the final customer journey authorized on 2026-11-12. It is
separate from the larger Excel/DOCX backlog, business UAT and production rollout.
Use the isolated `grc.local` site for acceptance fixtures.

## Demo sequence

Run each path with a separate customer and company:

| Path | Expected customer journey | Expected staff journey |
| --- | --- | --- |
| Self-signup IA | Name/company/email, email OTP, choose Internal Audit, company selection, IA20 answers, save/resume, submit, immediate preliminary results/PDF/email | IA reviewer sees the submission; GRC staff cannot retrieve it; review, approve and release |
| Self-signup GRC | Name/company/email, email OTP, choose GRC, valid reusable company profile, Awareness plus at least one other section, scoped answers, submit and matching results/PDF/email | GRC reviewer sees the submission; IA staff cannot retrieve it; review, approve and release |
| Invited IA | IA invitation, locked email/company/type, email OTP, direct IA assessment; no GRC type choice or company-profile gate | Inviting IA consultant remains assigned; GRC staff are denied |
| Invited GRC | GRC invitation with minimum sections, locked email/company/type, email OTP, valid profile, add optional sections without removing minima, submit | Inviting GRC consultant remains assigned; IA staff are denied |

For each path verify unanswered submission fails, partial answers survive reload,
N/A counts as answered but contributes no score denominator, results match the
covered sections, the report email recipient is the registered customer and the
message contains the matching PDF attachment. An official released PDF is frozen.

For a second audit, the customer requests another audit type. The source manager
approves with a reason, then the target manager accepts. The additional type is
unavailable until both decisions complete. A rejected source request stays private
from the target department. Staff department revocation applies on the next request.

## Content and settings

The GRC template installs the original workbook's 46 questions, 184 answer
statements and 13 named topics. Section counts are Awareness 2, Governance 14,
Risk 17 and Compliance 13. Valid selected totals are 16, 19, 15, 33, 29, 32 and 46.
Awareness alone is invalid. GRC uses its own points 25/50/75/100 and band thresholds
0/35/55/75/90; it does not inherit IA gates or automatic issue answers. Approved
Arabic GRC question text is still an external content dependency; the interface
supports Arabic/RTL and retains English source questions where no approved text exists.

The local fixture explicitly configures Preliminary scorecard, Overall maturity
after assessment completion, customer scores after submission, and Before Audit
PDF access. Existing production policies are not changed by running a build.

## Local acceptance

Run from `/home/frappe/frappe-bench` inside WSL `alphax_bench`, as `frappe`, with
the documented Node 24 and bench paths. Start the existing isolated database and
normal Redis services as described in `GRC_OPERATIONS.md`.

```bash
bench --site grc.local migrate
cd apps/ia_maturity/grc
npm run build
npm run lint
```

The source-controlled `scripts/serve_demo_acceptance.py --port 8007` runs a
guarded loopback-only acceptance server. It retains native immediate Email Queue
construction, MIME generation and Sent checks, but substitutes a non-network SMTP
sink that accepts only reserved fixture recipients. The site remains muted. This
is a test runner, never a product email fallback or evidence of inbox delivery.

```bash
GRC_BASE_URL=http://127.0.0.1:8007 GRC_RUN_DEMO_CYCLE=1 \
  npx playwright test demo-cycle-live.spec.ts
```

`scripts/demo_cycle_fixture.py` is called internally by the browser tests. Its
reserved credentials/codes must not be printed into shared logs. Runtime state is
private under the local site; test screenshots, PDFs and results stay outside Git.
Run mutable database suites serially, then the browser cycle; never run fixtures
against production. See `PLAN_PROGRESS.md` for exact accepted results and remaining
work. Real email delivery requires the normal outgoing account and an explicitly
designated demo recipient; local SMTP-sink success does not certify provider or
inbox delivery.

The user explicitly deferred real inbox delivery checks until live deployment.
Keep local mail muted and use the reserved acceptance sink for this demo.


## Accepted validation snapshot

Final run `mwdo2j8o` passed all five live scenarios; total36 browser scenarios and185 backend tests passed. All79 retained access/security/history cases remain and passed without skips. Full-detail IA/GRC preliminary/released reports were checked for exact selected questions, scoring and snapshots;16 released PDF pages were visually inspected. Custom/frozen chart bands and mobile report layout were also verified. Evidence is in `diagnostics/demo-cycle-20261112/`. These checks certify the local demo slice, not the uncompleted broader backlog or production deployment.

## Fresh manual demo accounts (2026-11-12)

Use `http://localhost:8007`. Customer signup: `/signup`; customer login: `/login`;
staff login: `/login?staff=1`; staff workspace after login: `/grc/auditor`.

Staff sign-in opens the custom app directly. An old `/app/grc-staff` bookmark
redirects to that workspace. A fresh consultant can have no customers or
assessments yet: use **Getting started → Open Customer onboarding** to invite a
customer for your department, or ask your department manager for an existing
customer assignment. An assessment appears as that customer proceeds through the
journey; assigned reviewers review, approve and release the official report.
No organization/assessment selection is required just to enter the workspace.
Getting started and the page tour are optional: close or skip them, then reopen
them when needed. Empty selectors are hidden; available list filters are optional.
Required customer email OTP, valid GRC profile, section selection and answers
still gate their corresponding actions.
Use separate browser profiles/private windows for customer, consultant and reviewer.
The fresh manual run is `manual20261112`; it does not reuse completed acceptance customers.

| Department | Role | Prepared staff email |
| --- | --- | --- |
| Internal Audit | Consultant/inviter | grc-journey-manual20261112-ia-consultant@example.test |
| Internal Audit | Reviewer | grc-journey-manual20261112-ia-reviewer@example.test |
| Internal Audit | Manager | grc-journey-manual20261112-ia-manager@example.test |
| GRC | Consultant/inviter | grc-journey-manual20261112-grc-consultant@example.test |
| GRC | Reviewer | grc-journey-manual20261112-grc-reviewer@example.test |
| GRC | Manager | grc-journey-manual20261112-grc-manager@example.test |

Passwords remain in `sites/grc.local/private/demo-cycle-manual20261112.json`.
Display a selected account in your own PowerShell terminal:

```powershell
$demoAccounts = Get-Content -Raw -LiteralPath '\\wsl.localhost\alphax_bench\home\frappe\frappe-bench\sites\grc.local\private\demo-cycle-manual20261112.json' | ConvertFrom-Json
$demoAccounts.staff.ia.consultant
# Other choices: .ia.reviewer, .ia.manager, .grc.consultant, .grc.reviewer, .grc.manager
```

The following customer addresses are reserved and unused at preparation time.
They become accounts only after signup/invitation OTP verification. Customers have no password.

| Path | Customer email | Enter this exact company name |
| --- | --- | --- |
| Self IA | grc-journey-manual20261112-self-ia@example.test | Journey demo manual20261112 self ia |
| Self GRC | grc-journey-manual20261112-self-grc@example.test | Journey demo manual20261112 self grc |
| Invited IA | grc-journey-manual20261112-invited-ia@example.test | Journey demo manual20261112 invited ia |
| Invited GRC | grc-journey-manual20261112-invited-grc@example.test | Journey demo manual20261112 invited grc |

## Test-mode OTP, invitation and assignment helper

Paste this function into PowerShell once. Its output can contain a live test OTP
or private invitation link; keep that output in your own terminal.

```powershell
function Demo {
    param(
        [ValidateSet('code','login-code','invite-link','assign','evidence')]
        [string]$Action,
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$DemoValues
    )
    $demoRaw = & wsl -d alphax_bench --cd /home/frappe/frappe-bench -- ./env/bin/python apps/ia_maturity/scripts/demo_cycle_fixture.py $Action manual20261112 @DemoValues
    if ($LASTEXITCODE -ne 0) { throw 'Demo helper failed. Check the action and account.' }
    $demoResult = $demoRaw | ConvertFrom-Json
    if ($Action -eq 'invite-link') {
        'http://localhost:8007' + ([uri]$demoResult.url).PathAndQuery
    } else {
        $demoResult
    }
}
```

After clicking Send code/Send verification email in the customer browser:

```powershell
Demo code grc-journey-manual20261112-self-ia@example.test
```

Enter the returned six-digit code. Request a fresh code for each sign-in. Codes
are single-use and expire after 15 minutes; resend has a 60-second cooldown.
The helper reads the immediately Sent native email for this reserved recipient.

Staff 2FA is disabled by default following the user's later amendment today.
The six prepared manual demo staff accounts use password-only sign-in. Customers
always use emailed OTP, with no password option.

App admins open **Administration → Account security**
(`/grc/auditor/admin/security`) to set the central staff default, edit a staff
role policy, or search a username/email and edit its individual policy.
Each save requires the admin's current password. Individual Required/Disabled
overrides the role policy; Required wins among multiple role policies; role
policies override the central default. Default means inherit. Existing explicit
requirements and unrelated platform/ERP policies are preserved.

Only if an admin enables authenticator 2FA for a demo staff account, the login
asks for an Authenticator code. Generate that account's current test code:

```powershell
Demo login-code grc-journey-manual20261112-ia-reviewer@example.test
```

Use it immediately (30-second authenticator window). This is separate from the
customer email OTP; no phone enrollment is needed for these prepared fixtures.

After a consultant sends an invitation through Customer onboarding:

```powershell
Demo invite-link grc-journey-manual20261112-invited-ia@example.test
```

Open the returned URL in the customer browser. The helper keeps the test-server
origin on8007; the underlying site's normal host setting can still refer to8005.
No real message is delivered to an inbox.

## Manual customer paths

For self IA, open `/signup`, enter full name, exact company and reserved Self IA
email, accept the terms, send verification and retrieve its email OTP. After
verification choose Internal Audit, Continue, Start assessment. The IA20 questions
open without the GRC profile/section picker. Answer some questions, Save, reload
or sign out/in with a fresh email OTP to prove resume. Complete all displayed
questions and Submit for review. Results/preliminary PDF/email are available now.

For self GRC, repeat signup with the Self GRC address/company and choose GRC.
Complete company profile before the section picker. A simple valid example is
Financial Services / Banking / 100% Saudi with Saudi Commercial Registration,
optional CR `0123456789`, and explicit Not applicable — no KSA license. Regulator
answers are optional. Save profile; choose Awareness plus Risk (19 questions),
or all three optional sections (46 questions). Awareness alone is invalid.
Every displayed question must have A/B/C/D/N/A. Scope can change before the first
saved answer; invitation minima cannot be removed. Save/resume and submit.

For invited IA, sign in as the IA consultant and open Customer onboarding > Invite
customer. Enter the Invited IA email/company, Internal Audit and language; send.
Get its link with Demo invite-link and open it in the customer browser. Verify
the Internal Audit team label and locked company/email. Enter full name/consent,
send/get/enter OTP. It opens IA directly, with no type choice or GRC profile/scope.

For invited GRC, repeat using the GRC consultant and Invited GRC email/company.
Preselect Risk with mandatory Awareness. After recipient verification the GRC
profile is mandatory; Awareness/Risk are locked and the customer can add Compliance
and Governance. Complete and submit the chosen questions as in self GRC.

If automatic focus mode hides the header/report, click Normal view. IA retains
its original question-specific N/A policy (Q20); all GRC46 questions allow N/A.

## Auditor allocation, review and release

Self-signup goes to its department manager's queue. Invited customers retain the
inviting consultant. An assessment also needs its reviewer allocated before the
reviewer can act. The reserved setup helper allocates the manual consultant,
reviewer and manager, including locked invited-company access exceptions.
After the customer has created the assessment, copy its `IAMA-...` ID from the URL:

```powershell
Demo assign 'Journey demo manual20261112 self ia' 'IAMA-2026-REPLACE' 'Internal Audit'
Demo assign 'Journey demo manual20261112 self grc' 'IAMA-2026-REPLACE' 'GRC'
# For invited paths, use their exact company from the table and their own assessment ID.
```

This is local demo preparation, not a customer step. For unlocked self-created
companies a manager can instead use Assigned customers > Open > Customer
assignments > Assign customer (Consultant and Reviewer), then the assessment's
Assign team to select those people. Locked invited ownership exceptions currently
use the platform-admin controls or the reserved helper.

Sign in as the matching IA/GRC reviewer, open `/grc/auditor`, select the exact
manual company/assessment and use Begin review > Approve assessment > Release
report, confirming each dialog. Customers already have preliminary results before
this step. Refresh the customer view after release: Approved report replaces the
preliminary label and its PDF is the frozen official artifact.

For an easy score check use C for all questions and one N/A. GRC Awareness+Risk
has19 questions:18 x75 / (18 x100) =75%, level High. IA can use N/A onQ20; with
C on the other19 it also scores75% under the existing IA rules on a fresh company.

Click Email report > verify the read-only recipient > Send PDF. To verify the
reserved queued PDF was accepted by the local sink and contains the attachment:

```powershell
Demo evidence 'IAMA-2026-REPLACE'
```

Expect queue_has_pdf_attachment and transport_accepted true, the correct registered
recipient, selected section codes, and matching score. Download PDF works directly
in the customer UI. Real inbox delivery remains deferred until live deployment.

## Second audit and isolation checks

After finishing a one-type customer path, open Audit access > Request another
audit type > Send request. It must stay unavailable while Pending Source Approval.
Sign in as the source department manager, open Audit access, Approve with a reason;
then sign in as the target department manager and approve the Pending Target
Approval request. Refresh the customer workspace; the additional type is now
available. For Self IA this means IA manager first, then GRC manager.

Open the IA assessment URL while signed in as the GRC reviewer, and vice versa:
access must be denied. The other department's assessments must not appear in its
queue, including when the customer has both approved types. Try incomplete submit,
Awareness-only scope, removing invited Risk, invalid CR/profile and changing
scope after saving an answer; those actions must be blocked. Repeat the result
screen at390px and in Arabic; download/email controls remain usable.
