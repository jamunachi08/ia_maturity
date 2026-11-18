import frappe
from frappe.model.document import Document

class GRCActivity(Document):
    def on_trash(self):
        from ia_maturity.grc.security import enabled
        if enabled() and not (frappe.flags.in_test or frappe.flags.in_uninstall):
            frappe.throw("Activity history is append-only.", frappe.PermissionError)
