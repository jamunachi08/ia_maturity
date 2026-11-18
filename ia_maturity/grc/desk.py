"""Restricted staff Desk boot. The staff page reads only the explicit GRC API."""
import frappe
from ia_maturity.grc import security as sec

def boot_session(boot):
    if not sec.enabled() or sec.account_type() != "Auditor":
        return
    boot.grc_staff = True
    boot.home_page = "grc-staff"
    boot.allowed_workspaces = []
    boot.module_list = ["IA Maturity"]
    boot.page_info = {k:v for k,v in (boot.get("page_info") or {}).items() if k == "grc-staff"}
    boot.reports = {}
    boot.user_info = {frappe.session.user: (boot.get("user_info") or {}).get(frappe.session.user, {})}
    boot.letter_heads = []
    boot.onboarding_tours = []
    boot.messages = []
    boot.user["can_read"] = []
    boot.user["can_write"] = []
    boot.user["can_create"] = []
    boot.user["can_delete"] = []
