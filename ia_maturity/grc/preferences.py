"""Organization and account preferences; mandatory messages always bypass opt-outs."""
import frappe
from frappe.utils import cint
from ia_maturity.grc import security as sec

def optional_allowed(entity, user, kind):
    if kind == "Clarification":
        return True
    field = "grc_optional_reminders" if kind == "Reminder" else "grc_optional_status_updates"
    return (frappe.db.get_value("User", user, "grc_email_notifications") != 0
        and frappe.db.get_value("User", user, field) != 0
        and frappe.db.get_value("IA Maturity Entity", entity, field) != 0)

def cancel_optional(entity=None, user=None):
    filters = {"status": "Queued"}
    if entity:
        filters["entity"] = entity
    if user:
        filters["recipient"] = user
    for row in frappe.get_all("GRC Reminder Delivery", filters=filters,
            fields=["name", "entity", "recipient", "notification_kind", "email_queue"]):
        if not optional_allowed(row.entity, row.recipient, row.notification_kind or "Status"):
            if row.email_queue and frappe.db.get_value("Email Queue", row.email_queue, "status") in {"Not Sent", "Error", "Partially Sent"}:
                frappe.db.set_value("Email Queue", row.email_queue, "status", "Expired")
            frappe.db.set_value("GRC Reminder Delivery", row.name, {
                "status": "Failed", "error": "Optional notification disabled before delivery."})

@frappe.whitelist(methods=["POST"])
def save_notification_preferences(email_notifications=1, optional_reminders=1, optional_status_updates=1):
    sec.require_login()
    if sec.account_type() not in {"Customer", "Auditor"}:
        sec.deny()
    values = {"grc_email_notifications": int(bool(cint(email_notifications))),
        "grc_optional_reminders": int(bool(cint(optional_reminders))),
        "grc_optional_status_updates": int(bool(cint(optional_status_updates)))}
    frappe.db.set_value("User", frappe.session.user, values)
    cancel_optional(user=frappe.session.user)
    sec.log("Notification preference updated", details=values)
    return {key.removeprefix("grc_"): value for key,value in values.items()}
