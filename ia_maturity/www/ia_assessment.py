import frappe
from frappe import _

from ia_maturity.permissions import RESPONDENT, is_staff

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/ia-assessment"
		raise frappe.Redirect
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("IA Maturity Assessment")
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.has_access = is_staff() or RESPONDENT in frappe.get_roles()
	return context
