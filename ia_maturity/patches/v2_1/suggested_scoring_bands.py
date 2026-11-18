"""Apply the suggested score-to-maturity mapping on sites that still use the previous default.

Previous defaults: Critical 0–34, Low 35–54, Medium 55–74, High 75–89, Leading 90–100.
Suggested mapping: Critical 0–29, Low 30–49, Medium 50–69, High 70–84, Leading 85–100.

Point values (A=25, B=50, C=75, D=100), question text and section weights are unchanged.
Released GRC reports keep the frozen snapshot they were issued with. Other assessments that
still use the previous default bands are re-labelled from the same points. Custom bands are
left as stored.
"""

import frappe
from frappe.utils import flt

from ia_maturity.scoring import DEFAULT_BANDS

LEGACY_MIN = {"Critical": 0.0, "Low": 35.0, "Medium": 55.0, "High": 75.0, "Leading": 90.0}
SCORE_FIELDS = (
	"maturity_level",
	"score_level",
	"interpretation",
	"interpretation_ar",
	"gating_note",
	"gating_note_ar",
)


def execute():
	settings_updated = _update_settings()
	_update_published_policies()
	_rescore_open_assessments(settings_updated)
	frappe.clear_document_cache("IA Maturity Settings", "IA Maturity Settings")


def _is_legacy(bands):
	found = {}
	for band in bands or []:
		name = (band.get("level_name") if isinstance(band, dict) else band.level_name) or ""
		score = band.get("min_score") if isinstance(band, dict) else band.min_score
		found[name.strip()] = flt(score)
	if set(found) != set(LEGACY_MIN):
		return False
	return all(abs(found[name] - LEGACY_MIN[name]) < 0.05 for name in LEGACY_MIN)


def _copy_band(row, source):
	row.min_score = source["min_score"]
	row.max_score = source["max_score"]
	row.color = source["color"]
	row.interpretation = source["interpretation"]
	row.level_name_ar = source["level_name_ar"]
	row.interpretation_ar = source["interpretation_ar"]


def _update_settings():
	if not frappe.db.exists("DocType", "IA Maturity Settings"):
		return False
	settings = frappe.get_single("IA Maturity Settings")
	if not _is_legacy(settings.bands):
		return False
	by_name = {band["level_name"]: band for band in DEFAULT_BANDS}
	for row in settings.bands:
		_copy_band(row, by_name[row.level_name.strip()])
	settings.flags.ignore_permissions = True
	settings.save()
	return True


def _replace_policy_bands(policy):
	data = frappe.parse_json(policy) if isinstance(policy, str) else dict(policy or {})
	bands = data.get("bands") or []
	if not _is_legacy(bands):
		return None
	by_name = {band["level_name"]: dict(band) for band in DEFAULT_BANDS}
	data["bands"] = [by_name[(band.get("level_name") or "").strip()] for band in bands]
	return frappe.as_json(data)


def _update_published_policies():
	"""New assessments copy the published policy. Existing assessment snapshots are not rewritten here."""
	if not frappe.db.has_column("IA Maturity Template", "grc_policy"):
		return
	for name, policy in frappe.get_all("IA Maturity Template", fields=["name", "grc_policy"], as_list=True):
		if not policy:
			continue
		updated = _replace_policy_bands(policy)
		if updated:
			# Direct write: a published version rejects policy edits through the controller.
			frappe.db.set_value("IA Maturity Template", name, "grc_policy", updated, update_modified=False)


def _released_assessments():
	if not frappe.db.exists("DocType", "GRC Report Release"):
		return set()
	return set(frappe.get_all("GRC Report Release", pluck="assessment"))


def _rescore_open_assessments(settings_updated):
	from ia_maturity.scoring import compute, get_config

	released = _released_assessments()
	names = frappe.get_all("IA Maturity Assessment", pluck="name")
	for name in names:
		if name in released:
			continue
		doc = frappe.get_doc("IA Maturity Assessment", name)
		legacy_snapshot = False
		if doc.grc_policy_snapshot:
			updated = _replace_policy_bands(doc.grc_policy_snapshot)
			if not updated:
				continue
			doc.grc_policy_snapshot = updated
			legacy_snapshot = True
		elif not settings_updated:
			continue
		if not doc.answers or not doc.template or not frappe.db.exists("IA Maturity Template", doc.template):
			if legacy_snapshot:
				frappe.db.set_value(
					"IA Maturity Assessment",
					doc.name,
					"grc_policy_snapshot",
					doc.grc_policy_snapshot,
					update_modified=False,
				)
			continue
		template, sections = doc.template_sections()
		result = compute(
			[row.as_dict() for row in doc.answers],
			sections,
			template.weighting_method,
			get_config(doc),
		)
		values = {field: result.get(field) for field in SCORE_FIELDS}
		if legacy_snapshot:
			values["grc_policy_snapshot"] = doc.grc_policy_snapshot
		frappe.db.set_value("IA Maturity Assessment", doc.name, values, update_modified=False)
		for section in result.sections:
			frappe.db.set_value(
				"IA Maturity Section Score",
				{"parent": doc.name, "parenttype": "IA Maturity Assessment", "section_code": section.section_code},
				"maturity_level",
				section.maturity_level,
				update_modified=False,
			)
