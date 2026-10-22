import json

import frappe
from frappe import _
from frappe.utils import cint

from ia_maturity import branding
from ia_maturity.permissions import RESPONDENT, is_staff

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("IA Maturity Assessment")
	context.brand = branding.get_brand()
	context.brand_assets = {k: branding.asset_url(k) for k in branding.IMAGES}
	context.favicon = branding.asset_url("icon")
	context.csrf_token = frappe.sessions.get_csrf_token()

	if frappe.session.user == "Guest":
		link_key = frappe.form_dict.get("verify")
		if link_key:
			from ia_maturity.registration import verify_link

			try:
				url = verify_link(link_key)
			except frappe.ValidationError:
				url = None
				frappe.clear_messages()
			if url:
				frappe.local.flags.redirect_location = url
				raise frappe.Redirect
			context.link_invalid = True
		context.is_guest = True
		context.landing_json = json.dumps(landing_data(), ensure_ascii=False).replace("</", "<\\/")
		return context

	context.is_guest = False
	context.has_access = is_staff() or RESPONDENT in frappe.get_roles()
	return context


def landing_data():
	"""Public, non-sensitive data for the landing page (no entity names, no results)."""
	settings = frappe.get_cached_doc("IA Maturity Settings")
	template_name = settings.default_template
	sections, question_count = [], 0
	if template_name and frappe.db.exists("IA Maturity Template", template_name):
		tmpl = frappe.get_cached_doc("IA Maturity Template", template_name)
		question_count = len(tmpl.questions)
		for s in tmpl.sections:
			sections.append(
				{
					"code": s.section_code,
					"title": s.section_title,
					"title_ar": s.get("section_title_ar") or "",
					"count": sum(1 for q in tmpl.questions if q.section_code == s.section_code),
				}
			)
	roles = [r for r in (frappe.get_meta("IA Maturity Assessment").get_field("respondent_role").options or "").split("\n") if r]
	points = {
		"A": settings.points_a,
		"B": settings.points_b,
		"C": settings.points_c,
		"D": settings.points_d,
	}
	return {
		"enabled": bool(cint(settings.enable_landing_signup)),
		"headline": settings.landing_headline or "",
		"headline_ar": settings.get("landing_headline_ar") or "",
		"privacy": settings.privacy_notice or "",
		"privacy_ar": settings.get("privacy_notice_ar") or "",
		"sections": sections,
		"question_count": question_count,
		"roles": roles,
		"points": points,
		"benchmarking": bool(cint(settings.enable_benchmarking)) and bool(cint(settings.show_benchmark_to_respondents)),
		"work_email_only": bool(cint(settings.block_free_email_domains)),
		"code_minutes": cint(settings.verification_code_minutes) or 30,
	}
