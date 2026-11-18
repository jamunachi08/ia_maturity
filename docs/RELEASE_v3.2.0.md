# AlphaX IA Maturity v3.2.0 — Release notes

**Date:** 2026-11-17 · **Type:** feature release · **Schema:** 2 new DocTypes, new fields on GRC Department and GRC Settings · **Patches:** none (setup hooks seed data)

## What's new, by request

| Request | Delivered | Where (GRC App Admin) |
|---|---|---|
| Colour theme from the IRSAA logo, with more combinations | IRSAA theme (default) + AlphaX Classic; create, duplicate, preview, contrast-check and set default | Themes |
| Yes/No as dropdown or buttons | Per screen layout: Dropdown, Buttons, or the global setting. Compact uses pill buttons per regulator row | Screen layouts |
| Add more assessment types | Types with EN/AR label and description, icon, order, report prefix, base behaviour, profile requirement, active switch | Assessment types |
| No second confirmation after choosing the type | Continue starts directly when organization and template are unambiguous | — |
| Admin tool for the screen look, existing + new design, choose default | Standard (existing, default) and Compact (new design) presets; duplicate, adjust, preview, make default | Screen layouts |
| Reports visible to managers, role permissions | Report access matrix (view / download / email per role), default App Admin + Manager; Reports page and in-app report view | Report access, Reports |

## Design decisions

- **Themes drive every shade.** Brand colours in the stylesheets are expressions of the theme colours (`color-mix` in OKLab), calibrated so AlphaX Classic reproduces the original colours (mean ΔE 1.5). Status colours (success, warning, danger) are fixed because they carry meaning. Guests (login, public site) receive the theme too; the last theme is cached in the browser to avoid a flash on first paint. Changing the theme never forces users to sign in again.
- **Assessment types are departments.** Each type is a GRC Department record, so staff access, customer grants, invitations and report IDs work for new types without extra setup. The *base behaviour* chooses the built-in rules (Internal Audit: starts directly and may calculate issue-register answers; GRC: section choice, self-reported answers, workbook policy). Invited minimum sections remain specific to the built-in GRC questionnaire.
- **Layouts change presentation only.** Validation, permissions and stored data are identical in every layout; the admin preview uses sample data and never saves.
- **Report access never widens the tenant boundary.** A role permission applies only inside organizations and departments the user can already read. Report lookup by ID returns the same message for "does not exist" and "not yours".

## Deployment (Frappe Cloud)

1. Push the release; Frappe Cloud runs `migrate` (seeds themes, layouts, built-in type fields and report-access defaults).
2. Rebuild the portal on the bench (`npm --prefix apps/ia_maturity/grc ci && npm --prefix apps/ia_maturity/grc run build`).
3. Sign in as a GRC App Admin and review: **Themes** (IRSAA is the default), **Screen layouts** (Standard is the default), **Assessment types**, **Report access**.
4. Tell staff about the behaviour change below before rollout.

### Behaviour change

Before 3.2.0 any staff member who could open an assessment could download or email its report. Now that needs GRC App Admin, GRC Manager, a role granted under Report access, or being the assessment's assigned consultant/reviewer (on by default). Customers are unaffected.

## Adding an assessment type (checklist)

1. Assessment types → New assessment type (name, label EN/AR, behaviour, profile requirement, prefix, icon).
2. Audit packages → classify or create its questionnaire, publish it, make it the type's default.
3. Audit access → add staff to the new department; grant it to customers or let them request it.

## Verification performed

- New regression suite `grc/test_configuration.py` (themes, layouts, report lookup isolation, custom types, report access by role, customer release policy).
- Full suite on a brand-new Frappe v16 site and on the upgraded Frappe v15 site.
- Screens checked in a browser on Frappe v16: customer start flow (direct start), Standard and Compact profile, Themes and editor, Assessment types, Report access, Screen layouts preview, manager Reports and report view, theme switch to AlphaX Classic, Arabic right-to-left for Compact and Themes.
