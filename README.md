# AlphaX IA Maturity — Internal Audit Function Maturity Assessment

**AlphaX** product by **IRSAA Business Solutions** · Support: [erpsupport@irsaa.com](mailto:erpsupport@irsaa.com)

Built on Frappe / ERPNext (app name `ia_maturity`).

A Frappe app that turns the *IA Maturity Assessment (20 Questions / 6 Sections)* workbook into a working system:
respondents fill it in on a web portal, the server scores it, a PDF report is produced, improvement actions are
created automatically and reviewers approve the result in the desk.

* **Frappe:** version 15 (tested on 15.123). ERPNext is **not** required; the app works on ERPNext sites too.
* **Python:** 3.10 – 3.12
* **Licence:** MIT · © 2026 IRSAA Business Solutions (AlphaX)

---

## 1. What you get

| Area | What it does |
|---|---|
| **Respondent portal** `/ia-assessment` | Login-protected page. Respondents start an assessment, answer section by section (autosaved to the server), add comments and attach evidence files, submit, then see the full results report and download the PDF. |
| **Scoring engine** (server side) | Same method as the workbook: A=25 · B=50 · C=75 · D=100; section % = points ÷ (applicable questions × 100); overall % = total points ÷ total possible; bands Critical / Low / Medium / High / Leading. Points and bands are configurable. Adds *Not applicable* answers and *gating questions*. |
| **PDF report** (print format *IA Maturity Report*) | Executive summary, maturity scale, section bar chart (server-rendered SVG), section table, key findings, improvement roadmap (next-level practice, owner, timeframe), detailed responses, review comments, scoring method. |
| **Improvement actions** | On submission, one *IA Maturity Action* is created per A/B answer (optionally C too) with priority, due date (A: 90 days, B: 180, C: 365), owner role and the next-level practice as the recommended action. Track status, assignee and closure evidence. |
| **Review workflow** | Submitted assessments go to *Pending Review*. Reviewers set *Reviewed / Approved* with comments (reviewer and timestamp recorded); managers can *Return to Respondent* for correction. |
| **Notifications** | Submission e-mail to the administrator mailbox (and optionally the respondent) with section scores and the PDF attached. |
| **Analytics** | Script report *IA Maturity Scores*: every assessment with section columns, or averaged **by entity** or **by respondent perspective** (perception gap between CAE, Audit Committee, management…), with chart and summary cards. |
| **Workspace** | *IA Maturity* desk workspace with shortcuts, pending-review and open-action counters. |
| **Seed data** | The 20 questions, 6 sections, framework references and owners from the workbook are loaded on install. |

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
Push the folder to a GitHub repository, add it as a custom app in your Frappe Cloud bench group (branch for
Frappe v15), deploy, then install it on the site.

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
4. **Give people access** (see section 4).
5. Open `/ia-assessment` and try it.

## 3. Branding (AlphaX / IRSAA)

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

## 4. Roles and access

| Role | Who | Can |
|---|---|---|
| **IA Assessment Respondent** (portal role, no desk) | Client CAE, Audit Committee members, managers | Create, answer, submit and print **their own** assessments; see actions raised from them. |
| **IA Maturity Reviewer** | Engagement reviewers | Read all assessments, set review status/comments, update actions, run reports. |
| **IA Maturity Manager** | Practice lead / administrator | Everything, including templates, settings, entities, cancel/amend. |

**Adding respondents**
* *Self sign-up*: enable sign-up in Website Settings. With *Auto-assign Respondent Role on Sign-up* ticked,
  new website users from allowed domains get the respondent role automatically.
* *Invite*: create a **Website User** and add the role *IA Assessment Respondent*.
* *Restrict to one client*: add a **User Permission** for the user on *IA Maturity Entity* = that client. The
  portal then only offers that entity.

Respondents can register a new entity from the portal (turn off with *Respondents Can Register a New Entity*).
If the entity name already exists and the user has no access to it, they are asked to contact the administrator.

## 5. Day-to-day use

**Respondent:** log in → `/ia-assessment` → *Start assessment* (entity, perspective, job title, date) → answer six
sections (progress is saved automatically; leave and come back any time) → *Submit and generate report* →
*Download PDF report*.

**Staff (desk):**
* *IA Maturity Assessment* list shows review status; the form shows the score panel, answers, section scores.
  Staff can also fill in an assessment on someone's behalf directly in the desk grid.
* Buttons: *Open in Portal*, *Report PDF*, *View → Improvement Actions*, *Review → Reviewed / Approved*.
* *Review → Return to Respondent* (Managers): asks what to correct, cancels the submission and gives the respondent an
  amended draft with all answers kept; the reviewer's note is shown at the top of their questionnaire.
* *IA Maturity Action*: assign owners, track status; overdue actions show red in the list.
* *IA Maturity Scores* report: filter by entity/template/date; *Group By → Respondent Perspective* for a
  perception-gap view.

**Changing the questionnaire:** edit *IA Maturity Template* or use *New Version* on the template form. Every answer
row stores a snapshot of the question and option text, so editing a template never changes submitted assessments.

## 6. Scoring rules (as implemented)

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

## 7. Data model

| DocType | Type | Purpose |
|---|---|---|
| IA Maturity Settings | Single | Points, bands, rules, notifications, portal options |
| IA Maturity Band | Child | Maturity band (name, min %, colour, interpretation) |
| IA Maturity Template | Master | Versioned questionnaire; child tables *Template Section* and *Template Question* |
| IA Maturity Entity | Master | Organisation being assessed (sector, CMA-listed, regulators) |
| IA Maturity Assessment | Submittable | Header, answers (*Assessment Answer*), scores (*Section Score*), review fields |
| IA Maturity Action | Transaction | Improvement action raised from an A/B(/C) answer |

## 8. Code map

```
ia_maturity/
├── branding.py              AlphaX / IRSAA names, colours, logos (single place to re-brand)
├── hooks.py                 install hooks, portal menu, permission hooks, jinja helpers
├── install.py               roles, default settings, seed template (setup_data/iia_gias_20q.json)
├── scoring.py               pure scoring engine (used everywhere)
├── report_data.py           report context + server-side SVG chart
├── api.py                   whitelisted portal API (bootstrap / save / submit / delete draft)
├── notifications.py         submission e-mail with PDF
├── permissions.py           role helpers, sign-up hook, action row-level permissions
├── www/ia-assessment.html   respondent portal (single page, no build step)
├── www/ia_assessment.py     portal page controller (login required)
└── ia_maturity/
    ├── doctype/…            DocTypes, controllers, desk JS, tests
    ├── print_format/ia_maturity_report
    ├── report/ia_maturity_scores
    └── workspace/ia_maturity
```

## 9. Tests

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app ia_maturity
```
12 tests cover: seed vs workbook structure, all-C = 75 % High, all-A = 25 % Critical, a mixed pattern against the
Excel formula, gating cap, N/A exclusion and validation, incomplete-submission block, action creation and
cancellation, section weighting, return-to-respondent, and PDF/print rendering.

## 10. Not included yet (suggested next steps)

* Arabic translation / RTL for the portal and report (Frappe's translation system can be used; question text would
  need Arabic fields on the template).
* Automatic calculation of Q13 (issue closure time) from an audit-issue register, if you keep one in ERPNext.
* Anonymous peer benchmarking across entities (the *IA Maturity Scores* report already aggregates by entity).
