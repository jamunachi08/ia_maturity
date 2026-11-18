"""Comment and attachment availability for questionnaire questions.

Resolution order (most specific wins):
  question override → section override → questionnaire default

At section and question, empty / missing means Inherit.
Questionnaire defaults are Checks (1/0); missing defaults to disabled.
"""
from frappe.utils import cint

ENABLED = "Enabled"
DISABLED = "Disabled"


def _tri_state(value):
	"""Return True/False for Enabled/Disabled, or None for inherit/empty."""
	if value in (None, ""):
		return None
	if value in (ENABLED, 1, "1", True):
		return True
	if value in (DISABLED, 0, "0", False):
		return False
	text = str(value).strip()
	if not text:
		return None
	if text == ENABLED:
		return True
	if text == DISABLED:
		return False
	return None


def _row_get(row, field):
	if row is None:
		return None
	if hasattr(row, "get"):
		return row.get(field)
	return getattr(row, field, None)


def resolve_flag(template, section_row, question_row, field):
	"""Resolve allow_comment or allow_attachment for one question.

	field: 'allow_comment' | 'allow_attachment'
	"""
	for row in (question_row, section_row):
		resolved = _tri_state(_row_get(row, field))
		if resolved is not None:
			return resolved
	default_key = "default_" + field
	if template is not None:
		raw = _row_get(template, default_key)
		if raw not in (None, ""):
			return bool(cint(raw))
	return False


def resolve_for_question(template, question):
	"""Return {allow_comment, allow_attachment} ints for a template question row."""
	sections = {}
	if template is not None:
		for s in template.sections or []:
			sections[_row_get(s, "section_code")] = s
	section = sections.get(_row_get(question, "section_code"))
	return {
		"allow_comment": int(resolve_flag(template, section, question, "allow_comment")),
		"allow_attachment": int(resolve_flag(template, section, question, "allow_attachment")),
	}


def flags_for_answer(row):
	"""Apply the default-off GRC master switch before per-answer flags."""
	import frappe
	if not cint(frappe.get_cached_doc("GRC Settings").get("question_extras_enabled")):
		return {"allow_comment": 0, "allow_attachment": 0}
	comment = _row_get(row, "allow_comment")
	attachment = _row_get(row, "allow_attachment")
	return {
		"allow_comment": 0 if comment in (None, "") else cint(comment),
		"allow_attachment": 0 if attachment in (None, "") else cint(attachment),
	}
