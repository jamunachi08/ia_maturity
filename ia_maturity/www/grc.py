import frappe
from ia_maturity.grc.security import enabled

no_cache = 1


def get_context(context):
    if not enabled():
        frappe.throw("GRC is not enabled on this site.", frappe.DoesNotExistError)
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.title = "AlphaX GRC"
    context.no_header = True
    context.no_footer = True
    return context
