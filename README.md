# AlphaX IA Maturity — Internal Audit Function Maturity Assessment

**AlphaX** product by **IRSAA Business Solutions** · Support: [erpsupport@irsaa.com](mailto:erpsupport@irsaa.com)

Built on Frappe / ERPNext (app name `ia_maturity`).

A Frappe app that turns the *IA Maturity Assessment (20 Questions / 6 Sections)* workbook into a working system:
respondents fill it in on a web portal, the server scores it, a PDF report is produced, improvement actions are
created automatically and reviewers approve the result in the desk.

* **Frappe:** version 15 **and** version 16 (tested on 15.123 and 16.52). ERPNext is **not** required; the app works on
  ERPNext sites too.
* **Python:** 3.10 – 3.12 on Frappe v15; 3.14 on Frappe v16 (v16 requires Python 3.14 and Node 24)
* **Licence:** MIT · © 2026 IRSAA Business Solutions (AlphaX)

---

## 1. What you get

| Area | What it does |
|---|---|
| **Public landing page** `/ia-assessment` (signed-out visitors) | Branded, bilingual (English / Arabic, RTL) page that explains the assessment and collects the respondent's details – work e-mail, name, job title, perspective, organisation, date, report language and privacy consent. A 6-digit code (and one-click link) is e-mailed; entering it creates the account, signs the person in and opens a pre-filled draft at Section 1. Returning users choose *Continue / view results*. No passwords. |
| **Respondent portal** `/ia-assessment` (signed in) | Login-protected page. Respondents start an assessment, answer section by section (autosaved to the server), add comments and attach evidence files, submit, then see the full results report and download the PDF. |
| **Scoring engine** (server side) | Same method as the workbook: A=25 · B=50 · C=75 · D=100; section % = points ÷ (applicable questions × 100); overall % = total points ÷ total possible; bands Critical / Low / Medium / High / Leading. Points and bands are configurable. Adds *Not applicable* answers and *gating questions*. |
| **Client and internal reports** | Two PDFs from one design. **IA Maturity Report** (client) contains only the sections enabled in *Settings > Client Report Content* — by default 01 Executive summary, 02 Results by section, 03 Peer benchmark. **IA Maturity Internal Report** (IRSAA) always contains everything and carries an *INTERNAL – not for distribution* banner; only IA Maturity staff can open it. The portal shows clients the client report only, and data of hidden sections is never sent to their browser. |
| **PDF report contents** | Executive summary, maturity scale, section bar chart (server-rendered SVG), section table, key findings, improvement roadmap (next-level practice, owner, timeframe), detailed responses, review comments, scoring method. |
| **Improvement actions** | On submission, one *IA Maturity Action* is created per A/B answer (optionally C too) with priority, due date (A: 90 days, B: 180, C: 365), owner role and the next-level practice as the recommended action. Track status, assignee and closure evidence. |
| **Review workflow** | Submitted assessments go to *Pending Review*. Reviewers use *Review → Reviewed / Approved* (with comments; reviewer and timestamp recorded). Reviewers cannot change answers. Managers can *Return to Respondent* for correction. |
| **Notifications** | Submission e-mail to the administrator mailbox (and optionally the respondent) with section scores and the PDF attached. |
| **Analytics** | Script report *IA Maturity Scores*: every assessment with section columns, or averaged **by entity** or **by respondent perspective** (perception gap between CAE, Audit Committee, management…), with chart and summary cards. |
| **Workspace** | *IA Maturity* desk workspace with shortcuts, pending-review and open-action counters. |
| **Seed data** | The 20 questions, 6 sections, framework references and owners from the workbook are loaded on install, in English **and Arabic**. |
| **Arabic / right-to-left** | One-click English ⇄ العربية switch in the portal (full RTL layout, Arabic questions, answers, guidance and report). The PDF report is produced in the assessment's *Report Language* with the bundled Noto Sans Arabic font, so Arabic renders on any server. |
| **Q13 from the issue register** | *IA Audit Issue* register (or any DocType you point it at). Q13 "average time to close audit issues" is calculated from issues closed in the last 24 months, locked for respondents and explained in the portal and report. Falls back to a manual answer when there are fewer than 5 closed issues. |
| **Anonymous peer benchmarking** | Portal and PDF show the entity's percentile, the peer median and the middle 50 % of peers for the overall score and each section, compared with the latest submitted assessment of every other entity. Hidden until at least 5 peer entities exist; never shows peer names, minimum or maximum. Staff get the *IA Maturity Benchmark* report. |

## 2. Installation

### On a bench you manage

```bash
cd ~/frappe-bench
# from a Git repository (push this folder to your Git host first):
bench get-app https://github.com/<your-org>/ia_maturity.git
# …or from the zip: unzip into apps/ then
#   ./env/bin/pip install -e apps/ia_maturity && echo ia_maturity >> sites/apps.txt

bench --site <your-site> install-app ia_maturity
bench --site <your-site> migrate
bench build --app ia_maturity
bench restart            # production (supervisor / systemd)
```

### Frappe Cloud
Push the folder to a GitHub repository, add it as a custom app in your Frappe Cloud bench group (v15 or v16),
deploy, then install it on the site.

### After installing — 5-minute setup

1. **IA Maturity Settings** (desk → search "IA Maturity Settings")
   * *Notify on Submission*: the administrator mailbox (e.g. the CAE or practice-lead address).
   * Check the points and maturity bands (defaults match the workbook).
   * Optional: *Require Evidence For Answers At* = "C and D" to stop unsupported high scores.
   * Optional: *Allowed Email Domains* to limit who can respond.
2. **Outgoing e-mail**: set up a default outgoing **Email Account** (Tools → Email Account). Without one,
   submissions still work but no e-mail is sent (an Error Log entry is written).
3. **Site host name** (needed for PDF generation in background jobs and correct links in e-mails):
   `bench --site <site> set-config host_name https://your.domain`
4. **Give people access** (see section 5).
5. Open `/ia-assessment` and try it.

## 3. Frappe v15 / v16 compatibility

One codebase installs on both versions (`frappe >=15,<17`). Version differences are handled in `ia_maturity/compat.py`:

| Topic | v15 | v16 | How the app handles it |
|---|---|---|---|
| Desk URL | `/app/...` | `/desk/...` (old `/app` links redirect) | Links built with `get_url_to_form` / `compat.desk_base()` |
| Permission hooks | `None` = no opinion | any falsy result = **deny** | `has_permission` hook returns `True`/`False` explicitly |
| Workspace | no `type` field | `type` required, new sidebar & desktop | Workspace JSON carries `type: Workspace`; v16 builds the sidebar and shows the AlphaX tile on the desktop automatically |
| Test base class | `FrappeTestCase` | `IntegrationTestCase` | Tests import whichever exists |
| `in_test` flag | `frappe.flags.in_test` | `frappe.in_test` | `compat.in_test()` |
| PDF engine | wkhtmltopdf | wkhtmltopdf by default (Chrome/WeasyPrint optional) | Print format is wkhtmltopdf-friendly (tables, inline SVG, embedded logos) |

Installing on v16:
```bash
bench init --frappe-branch version-16 --python python3.14 frappe-bench   # Node 24 required
cd frappe-bench && bench get-app <repo-url-or-path>
bench --site <site> install-app ia_maturity
```

## 4. Branding (AlphaX / IRSAA)

| Surface | Branding |
|---|---|
| Respondent portal | AlphaX header bar (mark + wordmark), AlphaX favicon, IRSAA blue accents, footer "AlphaX IA Maturity · a product of IRSAA Business Solutions · erpsupport@irsaa.com" with the IRSAA logo |
| PDF report | AlphaX logo and IRSAA-blue rule in the header; repeating footer on every page with the IRSAA logo, product/company/support line, entity, reference and *Page x of y* |
| Submission e-mail | AlphaX logo header, IRSAA-blue button, IRSAA signature line; subject starts with "AlphaX \|" |
| Desk | AlphaX mark as the desk logo (`app_logo_url`), *AlphaX IA Maturity* tile on `/apps` (staff only), AlphaX header on the workspace and on the score panel |

Brand colours (sampled from the supplied logos): AlphaX black `#181818`, IRSAA blue `#12506E`.
All names, colours and contact details live in `ia_maturity/branding.py`; logo files are in
`ia_maturity/public/images/`. Replace those to re-brand — no other code changes needed.

> **Desk logo is site-wide.** `app_logo_url` makes the AlphaX mark the navbar logo of the whole desk on the site where
> the app is installed (replacing the ERPNext/Frappe logo). Remove that line from `hooks.py` if you don't want this.

> **PDF footer needs the patched wkhtmltopdf** (0.12.6 "with patched qt"), which is the standard Frappe production
> install. Distribution packages (`apt install wkhtmltopdf`) ignore PDF headers/footers. Check with
> `wkhtmltopdf --version`.

## 5. Roles and access

| Role | Who | Can |
|---|---|---|
| **IA Assessment Respondent** (portal role, no desk) | Client CAE, Audit Committee members, managers | Create, answer, submit and print **their own** assessments; see actions raised from them. |
| **IA Maturity Reviewer** | Engagement reviewers | Read all assessments, set review status/comments, update actions, run reports. |
| **IA Maturity Manager** | Practice lead / administrator | Everything, including templates, settings, entities, cancel/amend. |

**Adding respondents**
* *Self sign-up*: enable sign-up in Website Settings. With *Auto-assign Respondent Role on Sign-up* ticked,
  people who register themselves (from allowed domains) get the respondent role automatically. Users created by an
  administrator never get it automatically — add the role yourself (this keeps staff accounts clean).
* *Invite*: create a **Website User** and add the role *IA Assessment Respondent*.
* *Restrict to one client*: add a **User Permission** for the user on *IA Maturity Entity* = that client. The
  portal then only offers that entity.

Respondents can register a new entity from the portal (turn off with *Respondents Can Register a New Entity*).
If the entity name already exists and the user has no access to it, they are asked to contact the administrator.

## 6. Day-to-day use

**Respondent:** log in → `/ia-assessment` → *Start assessment* (entity, perspective, job title, date) → answer six
sections (progress is saved automatically; leave and come back any time) → *Submit and generate report* →
*Download PDF report*.

**Staff (desk):**
* *IA Maturity Assessment* list shows review status; the form shows the score panel, answers, section scores.
  Staff can also fill in an assessment on someone's behalf directly in the desk grid.
* Buttons: *Open in Portal*, *Report PDF*, *View → Improvement Actions*, *Review → Reviewed / Approved* (asks for a
  comment).
* *Review → Return to Respondent* (Managers): asks what to correct, cancels the submission and gives the respondent an
  amended draft with all answers kept; the reviewer's note is shown at the top of their questionnaire.
* *IA Maturity Action*: assign owners, track status; overdue actions show red in the list.
* *IA Maturity Scores* report: filter by entity/template/date; *Group By → Respondent Perspective* for a
  perception-gap view.

**Changing the questionnaire:** edit *IA Maturity Template* or use *New Version* on the template form. Every answer
row stores a snapshot of the question and option text, so editing a template never changes submitted assessments.

## 7. Scoring rules (as implemented)

* Points per answer: Settings (default A 25, B 50, C 75, D 100). D is the maximum.
* **N/A** (only where *Allow 'Not Applicable'* is ticked on the question — Q20 in the seed) is excluded from the
  denominator.
* Section % = section points ÷ (applicable questions × max points), rounded to 1 decimal.
* Overall %:
  * *Points (each question equal)* — default, identical to the workbook (sections with 4 questions weigh more), or
  * *Section Weights* — weighted average of section % using the template's section weights.
* Level = highest band whose minimum ≤ score.
* **Gating:** a gating question answered at its trigger level caps the *overall level* (the score is unchanged and
  the report explains the cap). Seed: Q1 (independence) answered A caps the overall level at *Low*.
* Submission requires every question to be answered (and evidence, if configured).

> Design note: the workbook's scale can never go below 25 % (all A = 25 %). If you prefer a 0–100 range, set the
> points to A 0 · B 33.33 · C 66.67 · D 100 in Settings and review the band thresholds — no code change needed.

## 8. Data model

| DocType | Type | Purpose |
|---|---|---|
| IA Maturity Settings | Single | Points, bands, rules, notifications, portal options |
| IA Maturity Band | Child | Maturity band (name, min %, colour, interpretation) |
| IA Maturity Template | Master | Versioned questionnaire; child tables *Template Section* and *Template Question* |
| IA Maturity Entity | Master | Organisation being assessed (sector, CMA-listed, regulators) |
| IA Maturity Assessment | Submittable | Header, answers (*Assessment Answer*), scores (*Section Score*), review fields |
| IA Maturity Action | Transaction | Improvement action raised from an A/B(/C) answer |
| IA Audit Issue | Transaction | Audit-issue register (raised / closed dates) used to calculate Q13 |

## 9. Code map

```
ia_maturity/
├── compat.py                Frappe v15 / v16 differences (desk URL, test flag)
├── branding.py              AlphaX / IRSAA names, colours, logos (single place to re-brand)
├── hooks.py                 install hooks, portal menu, permission hooks, jinja helpers
├── install.py               roles, default settings, seed template (setup_data/iia_gias_20q*.json, Arabic in *_ar)
├── scoring.py               pure scoring engine (used everywhere)
├── report_data.py           report context (English / Arabic) + server-side SVG chart + embedded Arabic font
├── i18n.py                  English / Arabic report strings, level names, bidi helper
├── issues.py                issue-register statistics and Q13 auto-calculation
├── benchmark.py             anonymous peer benchmarking (quartiles, percentile, minimum-peer rule)
├── patches/v1_3/            upgrade patch: Arabic seed text, new settings defaults
├── api.py                   whitelisted portal API (bootstrap / save / submit / delete draft)
├── notifications.py         submission e-mails: internal PDF to admin, client PDF to respondent
├── registration.py          landing-page sign-up: e-mail code / link, rate limits, account + pre-filled draft
├── templates/ia_maturity_landing.html   public landing page (EN/AR)
├── permissions.py           role helpers, sign-up hook, action row-level permissions
├── www/ia-assessment.html   respondent portal (single page, no build step)
├── www/ia_assessment.py     portal page controller (login required)
└── ia_maturity/
    ├── doctype/…            DocTypes, controllers, desk JS, tests
    ├── print_format/ia_maturity_report (client), ia_maturity_internal_report (IRSAA)
    ├── report/ia_maturity_scores, report/ia_maturity_benchmark
    └── workspace/ia_maturity
```

## 10. Tests

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app ia_maturity
```
27 tests (run on both v15 and v16) cover: seed vs workbook structure, all-C = 75 % High, all-A = 25 % Critical, a mixed
pattern against the Excel formula, gating cap, N/A exclusion and validation, incomplete-submission block, action
creation and cancellation, section weighting, return-to-respondent, reviewer approval without edit rights, respondent
role only on self sign-up, PDF rendering, the Arabic seed / Arabic report / RTL PDF, Q13 auto-calculation (locked
answer, minimum sample, thresholds) peer benchmarking (minimum-peer rule, percentile, latest-per-entity) and the client/internal split (hidden sections
absent from client data and PDF, settings switches, clients blocked from the internal report) and the landing-page
sign-up (pre-filled draft, wrong-code lock-out, free e-mail and required-field checks, staff accounts refused,
resume and one-click link).

## 11. Arabic, the issue register and benchmarking

### Arabic / RTL
* Respondents switch language with the **العربية / English** button in the portal header. The choice is remembered
  in the browser and saved on the assessment as its *Report Language*, which the PDF and e-mailed report use.
* Questionnaire text: each template section and question has Arabic fields (*Section Title (Arabic)*,
  *Question (Arabic)*, *A (Arabic)* … *D (Arabic)*). The seed template ships fully translated; for your own templates,
  fill the Arabic fields — anything left blank falls back to English.
* Maturity band names and interpretations have Arabic fields in *IA Maturity Settings > Maturity Bands*.
* The Arabic translation of the seed questionnaire was prepared for this release using Saudi terminology
  (e.g. لجنة المراجعة, الرئيس التنفيذي للتدقيق). Have it reviewed by a qualified Arabic-speaking auditor before client use.
* Font: Noto Sans Arabic (SIL Open Font License, `public/fonts/OFL.txt`) is embedded in the PDF and served to the portal.
* The desk itself follows each user's Frappe language setting; this app's desk labels are English.

### Q13 – issue closure time from the register
1. Record audit issues in **IA Audit Issue** (entity, raised on, status, closed on). Days to close are computed.
2. *IA Maturity Settings > Issue Register*: the DocType and field names (defaults match IA Audit Issue — point these
   at your own issue DocType if you already keep one), look-back period (24 months), minimum closed issues (5),
   thresholds (average months: above 12 = A, above 9 = B, above 6 = C, otherwise D) and whether respondents may
   override the calculated answer.
3. Any template question with *Auto-calculate From = Issue Closure Time* uses it (Q13 in the seed). The answer is
   recalculated every time a draft is saved, frozen at submission, and the basis is printed in the report.

### Peer benchmarking
* *IA Maturity Settings > Peer Benchmarking*: on/off, show to respondents, minimum peer entities (default 5) and
  peer group (*All entities* or *Same sector* — uses the entity's Sector).
* Peers = the latest submitted assessment of every other entity on the same template. Benchmarks change as new
  assessments are submitted; the report states the date.
* Staff: *IA Maturity Benchmark* report (quartiles, median and average per section, maturity-level distribution).

## 12. Client report vs internal report

| Section | Client report (default) | Internal report |
|---|---|---|
| 01 Executive summary | ✔ | ✔ |
| 02 Results by section | ✔ | ✔ |
| 03 Peer benchmark | ✔ | ✔ |
| Key findings | – | ✔ |
| Improvement roadmap | – | ✔ |
| Detailed responses | – | ✔ |
| Reviewer comments | – | ✔ |
| Scoring method | – | ✔ |

* Change the client column in **IA Maturity Settings > Client Report Content** — it applies at once to the portal,
  the client PDF and the client e-mail (also for assessments already submitted). Section numbers adjust automatically.
* **Internal report**: desk *PDF → Internal Report (IRSAA)*, the *Internal report (IRSAA)* button that staff see in
  the portal, or *Print* (it is the doctype's default print format). Clients who try the internal format get a
  permission error.
* **E-mails on submission**: the administrator mailbox receives *[Internal]* with the internal PDF (English); the
  respondent receives a separate e-mail in their report language with the client PDF only.

## 13. Landing page and sign-up

**Flow:** visitor opens `/ia-assessment` → fills *Before you start* → receives a 6-digit code (valid 30 min) and a
one-click link → enters the code → an *IA Assessment Respondent* website user is created (or reused), signed in,
and a draft assessment is created with the entity, perspective, job title, date and report language → Section 1.

**Settings** (*IA Maturity Settings > Landing Page & Sign-up*): turn sign-up on/off, require a work e-mail (free
providers such as gmail.com are refused – list editable), code validity, optional headline override (EN/AR) and
the privacy notice shown next to the consent box (EN/AR). *Allowed Email Domains* still applies.

**Security:** codes and link keys are stored only as hashes; 5 wrong codes block the request; requests are
rate-limited per e-mail and per IP; staff (desk) accounts are never signed in this way – they use `/login`;
responses do not reveal whether an address already has an account. Every request is recorded in
**IA Maturity Registration** (useful as a lead list: who started, verified and which assessment was created).

**Requirement:** a working default outgoing *Email Account* – without it codes cannot be sent and visitors see a
clear "could not send the e-mail" message.

**Why this design (Frappe options considered)**
* *Web Form with guest access* – quick, but limited layout control, no e-mail verification, and guest
  submissions cannot be resumed securely.
* *Frappe sign-up + password* (`/login#signup`) – standard, but adds a password step and a separate page before
  the assessment; respondents often fill this in once a year.
* *Custom landing page + e-mail one-time code* (chosen) – the pattern Frappe itself uses for "login with e-mail
  link" and Frappe Cloud sign-up: one screen, verified business e-mail, no password, details captured up front.

## 14. Not included yet (suggested next steps)

* Arabic versions of the submission e-mail and of the desk labels (Frappe translation files).
* Trend view: an entity's score history across years on one chart.
* Benchmarks by respondent perspective (e.g. CAE versus Audit Committee across all entities).
