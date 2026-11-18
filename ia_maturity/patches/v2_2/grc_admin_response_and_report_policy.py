"""v2.2: comment/attachment questionnaire defaults and report delivery policy defaults.

Existing questionnaires keep comments and attachments enabled. Report download/email
remain allowed after Report Released (After Audit).
"""
import frappe


def execute():
	_backfill_template_defaults()
	_backfill_answer_flags()
	_ensure_report_settings()


def _backfill_template_defaults():
	if not frappe.db.has_column("IA Maturity Template", "default_allow_comment"):
		return
	for name in frappe.get_all("IA Maturity Template", pluck="name"):
		values = {}
		comment = frappe.db.get_value("IA Maturity Template", name, "default_allow_comment")
		attachment = frappe.db.get_value("IA Maturity Template", name, "default_allow_attachment")
		if comment in (None, ""):
			values["default_allow_comment"] = 1
		if attachment in (None, ""):
			values["default_allow_attachment"] = 1
		if values:
			frappe.db.set_value("IA Maturity Template", name, values, update_modified=False)


def _backfill_answer_flags():
	"""Existing answer rows default to allowing comment and attachment.

	New Check columns often materialize as 0 for legacy rows; treat the first
	migration as enabling both so current questionnaires keep working.
	"""
	if not frappe.db.has_column("IA Maturity Assessment Answer", "allow_comment"):
		return
	frappe.db.sql(
		"""update `tabIA Maturity Assessment Answer`
		set allow_comment = 1, allow_attachment = 1"""
	)


def _ensure_report_settings():
	stored = {r[0] for r in frappe.db.sql(
		"select field from `tabSingles` where doctype=%s", "GRC Settings")}
	if "allow_report_download" not in stored:
		frappe.db.set_single_value("GRC Settings", "allow_report_download", 1)
	if "allow_report_email" not in stored:
		frappe.db.set_single_value("GRC Settings", "allow_report_email", 1)
	if "report_access_timing" not in stored:
		frappe.db.set_single_value("GRC Settings", "report_access_timing", "After Audit")
