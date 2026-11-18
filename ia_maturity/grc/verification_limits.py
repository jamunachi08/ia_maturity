"""Admin tools for targeted customer verification rate limits."""
import ipaddress
import frappe
from frappe import _
from ia_maturity.grc import auth, security as sec
from ia_maturity.grc.email_policy import check_email

POLICY_FIELDS = {"email": "verification_email_limit_enabled", "ip": "verification_ip_limit_enabled"}


def limit_enabled(kind, for_update=False):
    """Fail closed for older sites that have no stored setting yet."""
    field = POLICY_FIELDS[kind]
    query = "select value from `tabSingles` where doctype=%s and field=%s"
    if for_update:
        query += " for update"
    rows = frappe.db.sql(query,
                         ("GRC Settings", field))
    return not rows or str(rows[0][0]) != "0"


@frappe.whitelist()
def verification_limit_policy():
    sec.require_admin()
    return {kind: limit_enabled(kind) for kind in POLICY_FIELDS}


@frappe.whitelist(methods=["POST"])
def set_verification_limit_policy(email_enabled, ip_enabled, reason):
    sec.require_admin()
    values = {"email": email_enabled, "ip": ip_enabled}
    for value in values.values():
        if value not in (0, 1, "0", "1", False, True):
            frappe.throw(_("Choose enabled or disabled for each verification limit."))
    reason = str(reason or "").strip()
    if not 3 <= len(reason) <= 500:
        frappe.throw(_("Enter a reason between 3 and 500 characters."))
    before = {kind: limit_enabled(kind, for_update=True) for kind in POLICY_FIELDS}
    after = {kind: bool(int(value)) for kind, value in values.items()}
    if before != after:
        for kind, field in POLICY_FIELDS.items():
            frappe.db.set_single_value("GRC Settings", field, int(after[kind]))
        sec.log("Verification limit policy changed", details={"before": before, "after": after, "reason": reason})
    return after


def _keys(kind, target):
    if kind == "email":
        target = check_email(target)
        kinds = ("request-email", "request-cooldown")
    elif kind == "ip":
        target = str(target or "").strip()
        try:
            ipaddress.ip_address(target)
        except ValueError:
            frappe.throw(_("Enter a valid IP address."))
        kinds = ("request-ip", "verify-ip")
    else:
        frappe.throw(_("Choose email or IP address."))
    return target, [(name, f"grc:{frappe.local.site}:{name}:{auth.digest(target)}") for name in kinds]


@frappe.whitelist(methods=["POST"])
def verification_limit_status(kind, target):
    sec.require_admin()
    target, keys = _keys(kind, target)
    limits = []
    for name, key in keys:
        value = frappe.cache.get(key)
        ttl = frappe.cache.ttl(key) if value is not None else -2
        limits.append({"kind": name, "count": int(value) if value is not None else 0,
                       "remaining_seconds": max(0, ttl), "active": value is not None})
    return {"kind": kind, "target": target, "limits": limits}


@frappe.whitelist(methods=["POST"])
def clear_verification_limits(kind, target, reason):
    sec.require_admin()
    target, keys = _keys(kind, target)
    reason = str(reason or "").strip()
    if not 3 <= len(reason) <= 500:
        frappe.throw(_("Enter a reason between 3 and 500 characters."))
    # Record the requested action before the nontransactional cache mutation.
    sec.log("Verification limits reset requested", details={"kind": kind, "target": target, "reason": reason})
    frappe.db.commit()
    frappe.cache.delete(*(key for _, key in keys))
    return {"kind": kind, "target": target, "cleared": [name for name, _ in keys]}
