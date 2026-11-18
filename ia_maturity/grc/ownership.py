"""Admin-controlled customer ownership, enforced in every staff access predicate."""
from contextlib import contextmanager
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc import security as sec
from ia_maturity.grc.read_cache import read_cached


@contextmanager
def writing():
    old = frappe.flags.get("grc_ownership_write")
    frappe.flags.grc_ownership_write = True
    try:
        with sec.service_write():
            yield
    finally:
        frappe.flags.grc_ownership_write = old


@read_cached
def staff_allowed(entity, user):
    from ia_maturity.grc import departments as dept
    if len(dept.entity_types(entity)) > 1 and dept.entity_types(entity) & dept.staff_types(user):
        return True  # Explicit second-department grants supersede a single global owner.
    row = frappe.db.get_value("IA Maturity Entity", entity, ["grc_ownership_locked", "grc_auditor_owner"], as_dict=True)
    if not row or not row.grc_ownership_locked:
        return True
    if user == row.grc_auditor_owner:
        return True
    return bool(frappe.db.exists("Auditor Customer Assignment", {
        "entity": entity, "auditor": user, "active": 1, "grc_lock_exception": 1}))


def guard(doc):
    if frappe.flags.get("grc_ownership_write"):
        return
    before = doc.get_doc_before_save()
    fields = ("grc_auditor_owner", "grc_ownership_locked", "grc_onboarding_invitation") if doc.doctype == "IA Maturity Entity" else ("grc_lock_exception",)
    if any((before.get(k) if before else None) != doc.get(k) and (before or doc.get(k)) for k in fields):
        frappe.throw(_("Use the administrator ownership controls to change ownership or access exceptions."))
    if doc.doctype == "Auditor Customer Assignment":
        entity = frappe.db.get_value("IA Maturity Entity", doc.entity, ["grc_ownership_locked", "grc_auditor_owner"], as_dict=True)
        if entity and entity.grc_ownership_locked:
            if not before or any(before.get(k) != doc.get(k) for k in ("active", "auditor", "responsibility", "entity")):
                frappe.throw(_("Use the administrator ownership controls for this locked customer."))


@frappe.whitelist()
def ownership_settings():
    sec.require_admin()
    return {"auto_lock": bool(cint(frappe.db.get_single_value("GRC Settings", "onboarding_auto_lock"))),
        "attention_hours": cint(frappe.db.get_single_value("GRC Settings", "onboarding_attention_hours")) or 48}


@frappe.whitelist(methods=["POST"])
def save_ownership_settings(auto_lock, attention_hours, reason):
    sec.require_admin()
    validate_reason(reason)
    if not 1 <= cint(attention_hours) <= 720:
        frappe.throw(_("Choose an inactivity threshold between 1 and 720 hours."))
    before = ownership_settings()
    with sec.service_write():
        doc = frappe.get_single("GRC Settings")
        doc.onboarding_auto_lock, doc.onboarding_attention_hours = int(bool(cint(auto_lock))), cint(attention_hours)
        doc.save(ignore_permissions=True)
    sec.log("Onboarding defaults changed", details={"before": before, "after": ownership_settings(), "reason": reason})
    return ownership_settings()


def validate_reason(reason):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        frappe.throw(_("Enter a reason of up to 2000 characters."))


@frappe.whitelist()
def customer_ownership(entity):
    sec.require_admin()
    doc = frappe.get_doc("IA Maturity Entity", entity)
    return {"entity": entity, "auditor": doc.grc_auditor_owner, "locked": bool(doc.grc_ownership_locked), "modified": doc.modified,
        "exceptions": frappe.get_all("Auditor Customer Assignment", filters={"entity": entity, "active": 1, "grc_lock_exception": 1}, fields=["auditor", "responsibility"])}


@frappe.whitelist(methods=["POST"])
def set_customer_ownership(entity, auditor, locked, exceptions, reason, modified):
    sec.require_admin()
    validate_reason(reason)
    doc = frappe.get_doc("IA Maturity Entity", entity, for_update=True)
    if str(doc.modified) != str(modified):
        frappe.throw(_("Customer ownership changed. Reload before saving."), frappe.TimestampMismatchError)
    from ia_maturity.grc.onboarding import can_invite
    if not auditor or not can_invite(auditor) or not frappe.db.get_value("User", auditor, "enabled"):
        frappe.throw(_("Choose an active auditor or consultant as the owner."))
    exceptions = frappe.parse_json(exceptions) if isinstance(exceptions, str) else exceptions
    if not isinstance(exceptions, list):
        sec.deny()
    wanted = set()
    for row in exceptions:
        if not isinstance(row, dict) or row.get("responsibility") not in {"Manager", "Consultant", "Reviewer"}:
            sec.deny()
        user = row.get("auditor")
        if sec.account_type(user) != "Auditor" or not frappe.db.get_value("User", user, "enabled"):
            frappe.throw(_("Choose active staff for access exceptions."))
        wanted.add((user, row["responsibility"]))
    before = customer_ownership(entity)
    old_owner = doc.grc_auditor_owner
    with writing():
        doc.grc_auditor_owner, doc.grc_ownership_locked = auditor, int(bool(cint(locked)))
        doc.save(ignore_permissions=True)
        # Move live consultant allocations before revocation hooks clear them.
        if old_owner and old_owner != auditor:
            for assignment in frappe.get_all("GRC Assessment Assignment", filters={"entity": entity,
                    "consultant": old_owner, "workflow_state": ["!=", "Report Released"]}, pluck="name"):
                frappe.db.set_value("GRC Assessment Assignment", assignment, "consultant", auditor)
        records = frappe.get_all("Auditor Customer Assignment", filters={"entity": entity}, fields=["name", "auditor", "responsibility", "grc_lock_exception", "active"])
        for row in records:
            record = frappe.get_doc("Auditor Customer Assignment", row.name)
            key = (row.auditor, row.responsibility)
            record.grc_lock_exception = int(key in wanted)
            if key == (auditor, "Consultant") or key in wanted:
                record.active = 1
            elif row.grc_lock_exception or old_owner != auditor and row.auditor == old_owner or doc.grc_ownership_locked:
                record.active = 0
            record.save(ignore_permissions=True)
        existing = {(r.auditor, r.responsibility) for r in records}
        for user, responsibility in (wanted | {(auditor, "Consultant")}) - existing:
            frappe.get_doc({"doctype": "Auditor Customer Assignment", "entity": entity, "auditor": user,
                "responsibility": responsibility, "active": 1, "grc_lock_exception": int((user, responsibility) in wanted)}).insert(ignore_permissions=True)
    sec.log("Customer ownership changed", entity, details={"before": before, "after": customer_ownership(entity), "reason": reason})
    return customer_ownership(entity)
