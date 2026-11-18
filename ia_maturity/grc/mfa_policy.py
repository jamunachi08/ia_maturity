"""Central GRC MFA configuration and optional account enrollment."""
import secrets

import frappe
from frappe import _
from frappe.utils import cint

from ia_maturity.grc import security as sec

POLICIES = {"Enabled", "Disabled", "Enforced"}
METHODS = {"OTP App", "Email"}
PLATFORM_ROLE = "GRC Platform MFA"


def policy():
    value = frappe.db.get_single_value("GRC Settings", "mfa_policy")
    if value and value not in POLICIES:
        frappe.throw(_("Invalid central MFA policy. Contact your administrator."))
    return value or None


def revision():
    return frappe.db.get_single_value("GRC Settings", "mfa_revision") or ""


def method():
    return frappe.db.get_single_value("System Settings", "two_factor_method")


def is_grc(doc):
    from ia_maturity.grc.schema import AUDITOR_ROLES, CUSTOMER_ROLES
    if doc.name in {"Administrator", "Guest"}:
        return False
    return bool({row.role for row in doc.roles} & (AUDITOR_ROLES | CUSTOMER_ROLES))


def sync_platform_role(doc):
    """Keep the former All-role requirement on accounts outside GRC."""
    lock_settings()
    if not policy():
        return
    preserve = cint(frappe.db.get_single_value("GRC Settings", "mfa_preserve_platform"))
    needs = preserve and not is_grc(doc) and doc.name != "Guest"
    doc.set("roles", [r for r in doc.roles if r.role != PLATFORM_ROLE or needs])
    if needs and PLATFORM_ROLE not in {r.role for r in doc.roles}:
        doc.append("roles", {"role": PLATFORM_ROLE})


def email_ready():
    return not (cint(frappe.conf.get("mute_emails")) or
        cint(frappe.db.get_default("suspend_email_queue"))) and bool(
        frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1,
                                         "awaiting_password": 0}))


def lock_settings():
    """Read current policy after locking, even if the request cached older values."""
    fields = {
        "GRC Settings": {"mfa_policy", "mfa_method", "mfa_revision", "mfa_preserve_platform",
                         "mfa_role_policies"},
        "System Settings": {"enable_two_factor_auth", "two_factor_method"},
    }
    for doctype, names in fields.items():
        rows = frappe.db.sql("select field,value from tabSingles where doctype=%s for update",
                             doctype, as_dict=True)
        current = {r.field: r.value for r in rows}
        frappe.db.value_cache.setdefault(doctype, {})
        for name in names:
            value = current.get(name)
            if name in {"enable_two_factor_auth", "mfa_preserve_platform"}:
                value = cint(value)
            frappe.db.value_cache[doctype][name] = value


def confirm_password(password):
    from frappe.utils.password import check_password
    from ia_maturity.grc.auth import limit
    limit("mfa-policy-admin", frappe.session.user, 10, seconds=900)
    if not password:
        frappe.throw(_("Enter your current password."))
    check_password(frappe.session.user, password, delete_tracker_cache=False)


@frappe.whitelist()
def security_mfa_settings():
    sec.require_admin()
    return {
        "policy": policy() or "Disabled", "method": method() if method() in METHODS else "OTP App",
        "email_ready": email_ready(),
        "blanket_mfa": bool(frappe.db.get_value("Role", "All", "two_factor_auth")),
        "centralized": bool(policy()),
    }


@frappe.whitelist(methods=["POST"])
def save_mfa_settings(policy, method, current_password):
    """Set the staff default; explicit user/role policies retain precedence."""
    sec.require_admin()
    if policy not in POLICIES or method not in METHODS:
        frappe.throw(_("Choose a valid MFA policy and verification method."))
    confirm_password(current_password)
    lock_settings()
    before = security_mfa_settings()
    before["method"] = frappe.db.get_single_value("System Settings", "two_factor_method")
    if policy != "Disabled" and method == "Email" and not email_ready():
        frappe.throw(_("Configure an active default outgoing email account before enabling email MFA."))
    from ia_maturity.grc.account_security import MFA_ROLE, LEGACY_MFA_ROLE, effective_policy
    docs = []
    for name in sorted(frappe.get_all("User", filters={"name": ["!=", "Guest"]}, pluck="name")):
        frappe.db.sql("select name from tabUser where name=%s for update", name)
        docs.append(frappe.get_doc("User", name))
    if method == "Email" and policy == "Disabled" and any(
            d.get("grc_account_type") == "Auditor" and effective_policy(d) == "Required" for d in docs
    ) and not email_ready():
        frappe.throw(_("Configure an active default outgoing email account before enabling email MFA."))
    # A GRC administrator cannot change an unrelated role's security settings.
    if policy != "Enforced":
        roles = {r.role for d in docs if is_grc(d) for r in d.roles}
        roles -= {MFA_ROLE, LEGACY_MFA_ROLE, PLATFORM_ROLE, "All"}
        blocking = frappe.get_all("Role", filters={"name": ["in", list(roles)],
                                                   "two_factor_auth": 1}, pluck="name") if roles else []
        if blocking:
            frappe.throw(_("These roles still require MFA: {0}. Ask the platform administrator to review them.")
                         .format(", ".join(sorted(blocking))))
    changed = (not before["centralized"] or before["policy"] != policy or before["method"] != method or before["blanket_mfa"]
               or not cint(frappe.db.get_single_value("System Settings", "enable_two_factor_auth")))
    if not changed:
        return {"policy": policy, "method": method, "affected": 0, "reauthenticate": False}
    preserve = before["blanket_mfa"] or cint(
        frappe.db.get_single_value("GRC Settings", "mfa_preserve_platform"))
    if preserve and not frappe.db.exists("Role", PLATFORM_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": PLATFORM_ROLE, "desk_access": 0,
                        "two_factor_auth": 1}).insert(ignore_permissions=True)
    if preserve:
        frappe.db.set_value("Role", PLATFORM_ROLE, "two_factor_auth", 1)
    frappe.db.set_single_value("GRC Settings", {
        "mfa_policy": policy, "mfa_method": method, "mfa_revision": secrets.token_hex(16),
        "mfa_preserve_platform": int(bool(preserve)),
    })
    # Native MFA remains available for non-GRC role requirements. Avoid the
    # System Settings save hook that would re-enable the blanket All role.
    frappe.db.set_single_value("System Settings", {"enable_two_factor_auth": 1,
                                                  "two_factor_method": method})
    if before["blanket_mfa"]:
        frappe.db.set_value("Role", "All", "two_factor_auth", 0)
    frappe.db.set_value("Role", MFA_ROLE, "two_factor_auth", 1)
    from ia_maturity.grc.account_security import sync_user
    affected = []
    for doc in docs:
        old_roles = {r.role for r in doc.roles}
        old_opt_in = doc.get("grc_mfa_opt_in")
        grc = is_grc(doc) and doc.name != "Administrator"
        if grc:
            # User/role requirements are separate from voluntary enrollment.
            # An old native secret alone must not opt staff into a new default.
            sync_user(doc)
        sync_platform_role(doc)
        if old_roles != {r.role for r in doc.roles} or old_opt_in != doc.get("grc_mfa_opt_in"):
            with sec.service_write():
                doc.save(ignore_permissions=True)
        if grc or before["method"] != method or before["blanket_mfa"]:
            affected.append(doc.name)
    sec.log("Central MFA policy changed", details={"before": before, "policy": policy,
        "method": method, "affected": len(affected), "platform_mfa_preserved": bool(preserve)})
    from frappe.sessions import clear_sessions
    for name in affected:
        frappe.clear_cache(user=name)
        clear_sessions(user=name, keep_current=False, force=True)
    reauthenticate = frappe.session.user in affected
    if reauthenticate:
        logout_current_request()
    return {"policy": policy, "method": method, "affected": len(affected),
            "reauthenticate": reauthenticate}


def logout_current_request():
    # Removing stored sessions alone leaves this request's session object live.
    # Frappe can write it back at the end of the request unless it is logged out.
    manager = getattr(frappe.local, "login_manager", None)
    if manager and getattr(frappe.local, "request", None):
        manager.logout()


@frappe.whitelist(methods=["POST"])
def set_optional_mfa(enabled, current_password):
    sec.require_login()
    if not sec.enabled() or sec.account_type() != "Auditor" or policy() != "Enabled":
        sec.deny()
    if str(enabled) not in {"0", "1"}:
        frappe.throw(_("Choose a valid MFA enrollment option."))
    confirm_password(current_password)
    if cint(enabled) and method() != "Email":
        frappe.throw(_("Complete authenticator setup before enabling MFA."))
    lock_settings()
    # Recheck after acquiring the same lock as admin policy changes.
    if policy() != "Enabled":
        sec.deny()
    frappe.db.sql("select name from tabUser where name=%s for update", frappe.session.user)
    from ia_maturity.grc.account_security import effective_policy
    doc = frappe.get_doc("User", frappe.session.user)
    if effective_policy(doc) != "Default":
        frappe.throw(_("Your administrator manages MFA for this account."), frappe.PermissionError)
    if cint(enabled) and (method() != "Email" or not email_ready()):
        frappe.throw(_("Email MFA is not available. Contact your administrator."))
    doc.grc_mfa_opt_in = cint(enabled)
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Optional MFA enrollment changed", details={"enabled": bool(cint(enabled)), "method": method()})
    from frappe.sessions import clear_sessions
    frappe.clear_cache(user=doc.name)
    clear_sessions(user=doc.name, keep_current=False, force=True)
    logout_current_request()
    return {"enabled": bool(cint(enabled)), "redirect": "/login"}


def validate_settings(doc):
    """Central policy changes must synchronize native roles through the service."""
    before = doc.get_doc_before_save()
    if before and not (frappe.flags.get("in_install") or frappe.flags.get("in_migrate")):
        if any(before.get(key) != doc.get(key) for key in
               ("mfa_policy", "mfa_method", "mfa_revision", "mfa_preserve_platform", "mfa_role_policies")):
            frappe.throw(_("Use Account security to change central MFA settings."))
