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
	frappe.db.commit()


def after_migrate():
	ensure_roles()
	if not frappe.db.exists("IA Maturity Template", SEED_TEMPLATE) and not frappe.db.count("IA Maturity Template"):
		seed_template()
	ensure_settings()


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
