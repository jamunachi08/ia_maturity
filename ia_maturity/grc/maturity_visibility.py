"""Visibility of the questionnaire maturity panel, independently of report delivery."""
import frappe
from frappe import _
from ia_maturity.grc.color_policy import require_manager
from ia_maturity.grc import security as sec
MODES=("Hidden","After assessment completion","Completed sections only")

def validate_mode(mode):
    if mode not in MODES:frappe.throw(_("Choose a valid Overall Maturity visibility mode."))
    return mode

def get_mode():return frappe.get_cached_doc("GRC Settings").get("overall_maturity_visibility") or "Hidden"

@frappe.whitelist()
def maturity_display_settings():
    require_manager()
    return {"mode":get_mode(),"options":list(MODES)}

@frappe.whitelist(methods=["POST"])
def save_maturity_display(mode,expected_mode=None):
    require_manager();validate_mode(mode)
    frappe.db.sql("select name from `tabDocType` where name=%s for update",("GRC Settings",))
    frappe.clear_document_cache("GRC Settings","GRC Settings")
    before=get_mode()
    if expected_mode is not None and expected_mode!=before:frappe.throw(_("Visibility changed. Reload before saving."),frappe.TimestampMismatchError)
    doc=frappe.get_single("GRC Settings");doc.overall_maturity_visibility=mode
    with sec.service_write():doc.save(ignore_permissions=True)
    sec.log("Overall maturity visibility changed",details={"before":before,"after":mode})
    return {"mode":mode,"options":list(MODES)}
