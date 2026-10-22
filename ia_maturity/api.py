"""Whitelisted API used by the respondent portal (/ia-assessment).

All methods run with the caller's permissions: respondents only see and change
their own assessments (DocPerm "if_owner"), staff see everything their roles allow.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from ia_maturity.permissions import RESPONDENT, email_domain_allowed, is_staff
from ia_maturity.report_data import get_report_context
from ia_maturity.scoring import LETTERS, LEVEL_NAMES, NA, get_config

DOCTYPE = "IA Maturity Assessment"
PRINT_FORMAT = "IA Maturity Report"


def _require_access():
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)
	if not (is_staff(user) or RESPONDENT in frappe.get_roles(user)):
		frappe.throw(
			_("Your account does not have access to the maturity assessment. Contact the administrator."),
			frappe.PermissionError,
		)


def _parse(data):
	if isinstance(data, str):
		data = json.loads(data or "{}")
	return frappe._dict(data or {})


def _template_payload(name):
	t = frappe.get_cached_doc("IA Maturity Template", name)
	return {
		"name": t.name,
		"version": t.version,
		"framework": t.framework,
		"introduction": t.introduction or "",
		"answer_rule": t.answer_rule or "",
		"weighting_method": t.weighting_method,
		"sections": [
			{"code": s.section_code, "title": s.section_title, "reference": s.reference or ""} for s in t.sections
		],
		"question_count": len(t.questions),
	}


def _serialize(doc):
	ptype_write = doc.docstatus == 0 and doc.has_permission("write")
	payload = {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"editable": bool(ptype_write),
		"entity": doc.entity,
		"template": doc.template,
		"assessment_date": str(doc.assessment_date or ""),
		"job_title": doc.job_title or "",
		"respondent_role": doc.respondent_role or "",
		"respondent_name": doc.respondent_name or "",
		"overall_score": doc.overall_score,
		"maturity_level": doc.maturity_level,
		"answered_count": doc.answered_count,
		"question_count": doc.question_count,
		"review_status": doc.review_status or "",
		"modified": str(doc.modified),
		"returned_comments": (
			frappe.db.get_value(DOCTYPE, doc.amended_from, "reviewer_comments") if doc.amended_from else ""
		)
		or "",
		"template_info": _template_payload(doc.template),
		"questions": [
			{
				"code": a.question_code,
				"section": a.section_code,
				"label": a.short_label or "",
				"text": a.question_text,
				"guidance": a.guidance or "",
				"options": [a.option_a, a.option_b, a.option_c, a.option_d],
				"allow_na": cint(a.allow_na),
				"selected": a.selected_option or "",
				"comment": a.comment or "",
				"evidence": a.evidence or "",
			}
			for a in doc.answers
		],
		"section_scores": [
			{"code": s.section_code, "pct": s.score_pct, "level": s.maturity_level} for s in doc.section_scores
		],
	}
	if doc.docstatus == 1:
		payload["report"] = get_report_context(doc)
		payload["pdf_url"] = "/api/method/frappe.utils.print_format.download_pdf?" + frappe.utils.urlencode(
			{"doctype": DOCTYPE, "name": doc.name, "format": PRINT_FORMAT, "no_letterhead": 1}
		)
	return payload


@frappe.whitelist()
def bootstrap():
	"""Initial data for the portal home screen."""
	_require_access()
	user = frappe.session.user
	settings = frappe.get_cached_doc("IA Maturity Settings")
	config = get_config()
	template = settings.default_template
	if not template or not frappe.db.get_value("IA Maturity Template", template, "is_active"):
		template = frappe.db.get_value("IA Maturity Template", {"is_active": 1}, "name", order_by="modified desc")

	filters = {} if is_staff(user) else {"owner": user}
	mine = frappe.get_list(
		DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"entity",
			"assessment_date",
			"docstatus",
			"overall_score",
			"maturity_level",
			"answered_count",
			"question_count",
			"review_status",
			"amended_from",
			"modified",
		],
		order_by="modified desc",
		limit_page_length=100,
	)
	for m in mine:
		m["assessment_date"] = str(m["assessment_date"] or "")
		m["modified"] = str(m["modified"])

	entities = frappe.get_list(
		"IA Maturity Entity", filters={"is_active": 1}, pluck="name", order_by="entity_name asc", limit_page_length=500
	)
	full_name, email = frappe.db.get_value("User", user, ["full_name", "email"])
	return {
		"user": {"name": user, "full_name": full_name, "email": email, "is_staff": is_staff(user)},
		"template": _template_payload(template) if template else None,
		"assessments": mine,
		"entities": entities,
		"allow_new_entity": cint(settings.allow_new_entity),
		"evidence_required_from": settings.evidence_required_from or "",
		"points": config.points,
		"level_names": LEVEL_NAMES,
		"bands": config.bands,
		"respondent_roles": [
			r
			for r in (frappe.get_meta(DOCTYPE).get_field("respondent_role").options or "").split("\n")
			if r
		],
	}


@frappe.whitelist()
def get_assessment(name):
	_require_access()
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("read")
	return _serialize(doc)


def _resolve_entity(data):
	settings = frappe.get_cached_doc("IA Maturity Settings")
	new_name = (data.get("new_entity") or "").strip()
	if new_name:
		if not cint(settings.allow_new_entity) and not is_staff():
			frappe.throw(_("Registering a new entity is disabled. Select an entity from the list."))
		if frappe.db.exists("IA Maturity Entity", new_name):
			if not frappe.has_permission("IA Maturity Entity", "read", new_name):
				frappe.throw(
					_("Entity {0} is already registered. Ask the administrator to give you access.").format(new_name)
				)
			return new_name
		entity = frappe.get_doc(
			{
				"doctype": "IA Maturity Entity",
				"entity_name": new_name,
				"contact_email": frappe.db.get_value("User", frappe.session.user, "email"),
			}
		).insert(ignore_permissions=True)
		# keep User Permission restrictions consistent for restricted users
		if frappe.db.exists("User Permission", {"user": frappe.session.user, "allow": "IA Maturity Entity"}):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": frappe.session.user,
					"allow": "IA Maturity Entity",
					"for_value": entity.name,
				}
			).insert(ignore_permissions=True)
		return entity.name
	entity = data.get("entity")
	if not entity:
		frappe.throw(_("Select the entity being assessed."))
	if not frappe.db.exists("IA Maturity Entity", entity) or not frappe.has_permission(
		"IA Maturity Entity", "read", entity
	):
		frappe.throw(_("You do not have access to entity {0}.").format(entity), frappe.PermissionError)
	return entity


@frappe.whitelist(methods=["POST"])
def save_assessment(data):
	"""Create or update a draft. `answers` is {question_code: {selected, comment, evidence}}."""
	_require_access()
	data = _parse(data)
	user = frappe.session.user
	if not is_staff(user) and not email_domain_allowed(frappe.db.get_value("User", user, "email")):
		frappe.throw(_("This assessment is limited to approved company e-mail domains."), frappe.PermissionError)

	if data.get("name"):
		doc = frappe.get_doc(DOCTYPE, data.name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("This assessment has already been submitted and can no longer be changed."))
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.respondent = user
		doc.template = data.get("template") or frappe.db.get_single_value("IA Maturity Settings", "default_template")
		if not doc.template:
			frappe.throw(_("No active questionnaire template is configured."))
		doc.load_questions()

	if "entity" in data or "new_entity" in data:
		doc.entity = _resolve_entity(data)
	for field in ("job_title", "respondent_role"):
		if field in data:
			doc.set(field, (data.get(field) or "").strip())
	if data.get("assessment_date"):
		doc.assessment_date = getdate(data.assessment_date)
	elif not doc.assessment_date:
		doc.assessment_date = today()

	answers = data.get("answers") or {}
	if answers:
		rows = {a.question_code: a for a in doc.answers}
		for code, ans in answers.items():
			row = rows.get(code)
			if not row:
				continue
			ans = ans or {}
			if "selected" in ans:
				sel = (ans.get("selected") or "").strip()
				if sel and sel not in LETTERS and sel != NA:
					frappe.throw(_("Invalid answer for {0}").format(code))
				row.selected_option = sel
			if "comment" in ans:
				row.comment = (ans.get("comment") or "")[:5000]
			if "evidence" in ans:
				row.evidence = ans.get("evidence") or ""

	doc.save()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def submit_assessment(name):
	_require_access()
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("submit")
	if doc.docstatus != 0:
		frappe.throw(_("This assessment is already submitted."))
	doc.submit()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def delete_draft(name):
	_require_access()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.docstatus != 0:
		frappe.throw(_("Only drafts can be deleted."))
	if doc.owner != frappe.session.user and not is_staff():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)
	return {"deleted": name}
