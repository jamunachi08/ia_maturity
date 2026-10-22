"""Install / migrate hooks: roles, default settings and the seed questionnaire."""

import json
import os

import frappe

from ia_maturity.scoring import DEFAULT_BANDS, DEFAULT_POINTS

SEED_TEMPLATE = "IIA GIAS Maturity Assessment (20Q)"

ROLES = [
	("IA Maturity Manager", 1),
	("IA Maturity Reviewer", 1),
	("IA Assessment Respondent", 0),  # portal-only role
]


def after_install():
	ensure_roles()
	seed_template()
	ensure_settings()
	apply_arabic_seed()
	frappe.db.commit()


def after_migrate():
	ensure_roles()
	if not frappe.db.exists("IA Maturity Template", SEED_TEMPLATE) and not frappe.db.count("IA Maturity Template"):
		seed_template()
	ensure_settings()


# Defaults for Single fields added after the first release. Single-doctype defaults are not applied
# to existing sites on migrate, so they are written once when the field has never been stored.
SETTINGS_DEFAULTS = {
	"issue_doctype": "IA Audit Issue",
	"issue_entity_field": "entity",
	"issue_opened_field": "raised_on",
	"issue_closed_field": "closed_on",
	"issue_lookback_months": 24,
	"issue_min_sample": 5,
	"lock_auto_answers": 1,
	"closure_a_above": 12,
	"closure_b_above": 9,
	"closure_c_above": 6,
	"enable_benchmarking": 1,
	"show_benchmark_to_respondents": 1,
	"benchmark_min_peers": 5,
	"benchmark_peer_group": "All entities",
	# client report: sections 01-03 only; everything else is internal
	"client_show_summary": 1,
	"client_show_sections": 1,
	"client_show_findings": 0,
	"client_show_roadmap": 0,
	"client_show_responses": 0,
	"client_show_reviewer_comments": 0,
	"client_show_scoring_method": 0,
}


def _stored_single_fields(doctype):
	return set(
		frappe.db.sql_list("select field from `tabSingles` where doctype = %s", doctype)  # nosemgrep
	)


def apply_arabic_seed(force=False):
	"""Fill Arabic text on the seed template and maturity bands (only where still empty) and enable
	auto-calculation of Q13 from the issue register."""
	path = os.path.join(os.path.dirname(__file__), "setup_data", "iia_gias_20q_ar.json")
	with open(path, encoding="utf-8") as fh:
		ar = json.load(fh)

	settings = frappe.get_single("IA Maturity Settings")
	changed = False
	for band in settings.bands:
		pair = ar["bands"].get(band.level_name)
		if pair and (force or not band.level_name_ar):
			band.level_name_ar, band.interpretation_ar = pair
			changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.save()

	if not frappe.db.exists("IA Maturity Template", SEED_TEMPLATE):
		return
	tmpl = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
	for field, value in ar["template"].items():
		if force or not tmpl.get(field):
			tmpl.set(field, value)
	for sec in tmpl.sections:
		for field, value in (ar["sections"].get(sec.section_code) or {}).items():
			if force or not sec.get(field):
				sec.set(field, value)
	for q in tmpl.questions:
		for field, value in (ar["questions"].get(q.question_code) or {}).items():
			if force or not q.get(field):
				q.set(field, value)
		if q.question_code == "Q13" and not q.auto_source:
			q.auto_source = "Issue Closure Time"
	tmpl.flags.ignore_permissions = True
	tmpl.save()


def ensure_roles():
	for role_name, desk_access in ROLES:
		if frappe.db.exists("Role", role_name):
			frappe.db.set_value("Role", role_name, "desk_access", desk_access, update_modified=False)
		else:
			frappe.get_doc(
				{"doctype": "Role", "role_name": role_name, "desk_access": desk_access, "is_custom": 0}
			).insert(ignore_permissions=True)


def ensure_settings():
	settings = frappe.get_single("IA Maturity Settings")
	changed = False
	for letter, field in (("A", "points_a"), ("B", "points_b"), ("C", "points_c"), ("D", "points_d")):
		if settings.get(field) in (None, ""):
			settings.set(field, DEFAULT_POINTS[letter])
			changed = True
	if not settings.bands:
		for band in DEFAULT_BANDS:
			settings.append("bands", band)
		changed = True
	if not settings.default_template and frappe.db.exists("IA Maturity Template", SEED_TEMPLATE):
		settings.default_template = SEED_TEMPLATE
		changed = True
	if not settings.create_actions_for:
		settings.create_actions_for = "A and B"
		changed = True
	stored = _stored_single_fields("IA Maturity Settings")
	for field, value in SETTINGS_DEFAULTS.items():
		if field not in stored and settings.get(field) in (None, "", 0):
			settings.set(field, value)
			changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.save()


def seed_template():
	if frappe.db.exists("IA Maturity Template", SEED_TEMPLATE):
		return
	path = os.path.join(os.path.dirname(__file__), "setup_data", "iia_gias_20q.json")
	with open(path, encoding="utf-8") as fh:
		data = json.load(fh)
	doc = frappe.get_doc(
		{
			"doctype": "IA Maturity Template",
			"template_name": SEED_TEMPLATE,
			"version": "1.0",
			"is_active": 1,
			"framework": "IIA Global Internal Audit Standards",
			"weighting_method": "Points (each question equal)",
			"introduction": "20 questions across 6 sections, aligned with the IIA Global Internal Audit Standards "
			"and Saudi regulatory expectations (CMA, SAMA, NCA). Select the statement that best describes "
			"current practice, not planned practice. Allow about 20 minutes. Your answers are saved as you go.",
			"answer_rule": "Select the highest level whose statement is fully met today. If a level is only "
			"partly met, select the level below it. Describe current practice, not planned practice.",
			"sections": data["sections"],
			"questions": data["questions"],
		}
	)
	doc.insert(ignore_permissions=True)
