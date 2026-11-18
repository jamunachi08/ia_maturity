"""Self-service profile with a server-enforced, administrator-owned field policy."""
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc import security as sec

PROFILE_FIELDS = (
    ("first_name", "First name", "text"),
    ("middle_name", "Middle name", "text"),
    ("last_name", "Last name", "text"),
    ("mobile_no", "Mobile number", "tel"),
    ("phone", "Phone number", "tel"),
    ("language", "Preferred language", "language"),
    ("time_zone", "Time zone", "timezone"),
)
FIELD_NAMES = {field[0] for field in PROFILE_FIELDS}
DEFAULT_EDITABLE = [field[0] for field in PROFILE_FIELDS]


def require_profile_user():
    sec.require_login()
    if not sec.enabled() or sec.account_type() not in {"Customer", "Auditor"}:
        sec.deny()


def validate_policy(value):
    value = frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(value, list) or any(not isinstance(k, str) or k not in FIELD_NAMES for k in value):
        frappe.throw(_("Select only the supported profile fields."))
    return list(dict.fromkeys(value))


def editable_fields():
    value = frappe.db.get_single_value("GRC Settings", "profile_editable_fields")
    return validate_policy(value) if value else list(DEFAULT_EDITABLE)


def field_catalog():
    return [{"fieldname": key, "label": label, "type": kind} for key, label, kind in PROFILE_FIELDS]


@frappe.whitelist()
def profile():
    require_profile_user()
    import pytz
    user = frappe.get_doc("User", frappe.session.user)
    from ia_maturity.grc.identity import safe_profile_names, display_name
    from ia_maturity.grc.mfa import status
    names, repair = safe_profile_names(user)
    return {"email": user.name, "full_name": display_name(user.name), "kind": sec.account_type(),
        "modified": str(user.modified), "values": {**{key: user.get(key) or "" for key in FIELD_NAMES}, **names},
        "name_repair_fields": repair, "authenticator": status(),
        "workspace_preferences": workspace_preferences(user),
        "editable_fields": editable_fields(), "fields": field_catalog(),
        "time_zones": pytz.common_timezones}


def set_new_user_workspace_defaults(doc, method=None):
    """Snapshot the current GRC defaults only when a GRC user is created."""
    roles = {row.role for row in doc.get("roles", [])}
    is_grc = doc.get("grc_account_type") in {"Customer", "Auditor"} or bool(
        roles & (sec.AUDITOR_ROLES | (sec.CUSTOMER_ROLES - {"IA Assessment Respondent"})))
    if not sec.enabled() or not is_grc:
        return
    for setting, field in (("new_user_page_tour_default", "grc_hide_page_tour"),
                           ("new_user_help_default", "grc_hide_help")):
        doc.set(field, int(frappe.db.get_single_value("GRC Settings", setting) == "Disabled"))


def workspace_preferences(user=None):
    user = user or frappe.get_cached_doc("User", frappe.session.user)
    return {"show_page_tour": not cint(user.get("grc_hide_page_tour")),
            "show_help": not cint(user.get("grc_hide_help"))}


@frappe.whitelist(methods=["POST"])
def save_workspace_preferences(data):
    require_profile_user()
    data = frappe.parse_json(data)
    fields = {"show_page_tour": "grc_hide_page_tour", "show_help": "grc_hide_help"}
    if not isinstance(data, dict) or set(data) - fields.keys():
        sec.deny()
    values = {}
    for key, value in data.items():
        if not isinstance(value, (bool, int, str)) or value not in (0, 1, "0", "1"):
            frappe.throw(_("Choose whether each workspace control is shown."))
        values[fields[key]] = int(not cint(value))
    if values:
        frappe.db.set_value("User", frappe.session.user, values)
        frappe.clear_cache(user=frappe.session.user)
    return workspace_preferences()


@frappe.whitelist(methods=["POST"])
def save_profile(data):
    require_profile_user()
    data = frappe.parse_json(data)
    if not isinstance(data, dict) or set(data) - set(editable_fields()):
        sec.deny()
    user = frappe.get_doc("User", frappe.session.user)
    changed = []
    import pytz
    for key, value in data.items():
        if not isinstance(value, str):
            frappe.throw(_("Invalid profile value."))
        value = value.strip()
        if len(value) > 140 or any(ord(c) < 32 for c in value):
            frappe.throw(_("Profile values must be plain text, up to 140 characters."))
        from ia_maturity.grc.identity import NAME_FIELDS, validate_name
        if key in NAME_FIELDS:
            validate_name(value, required=key == "first_name", user=user.name)
        if key == "language" and value not in {"en", "ar"}:
            frappe.throw(_("Choose English or Arabic."))
        if key == "time_zone" and value and value not in pytz.common_timezones:
            frappe.throw(_("Choose a valid time zone."))
        if (user.get(key) or "") != value:
            user.set(key, value)
            changed.append(key)
    if changed:
        with sec.service_write():
            user.save(ignore_permissions=True)
        frappe.clear_cache(user=user.name)
        sec.log("Profile updated", details={"user": user.name, "fields": changed})
    return profile()


@frappe.whitelist(methods=["POST"])
def change_password(current_password, new_password, confirm_password):
    require_profile_user()
    from ia_maturity.grc.auth import limit, reset_password
    limit("password-change", frappe.session.user, 10, seconds=900)
    if not current_password:
        frappe.throw(_("Enter your current password."))
    if not new_password or new_password != confirm_password:
        frappe.throw(_("The new passwords do not match."))
    if len(new_password) < 10:
        frappe.throw(_("Use at least 10 characters for the new password."))
    user = frappe.session.user
    from ia_maturity.grc.identity import NAME_FIELDS
    names = frappe.db.get_value("User", user, list(NAME_FIELDS) + ["full_name"])
    if new_password in (names or ()):
        frappe.throw(_("Choose a password that is different from your profile name."))
    # Core verifies the old password, enforces password policy and clears other sessions.
    # The GRC wrapper preserves mandatory staff MFA after recovery/password changes.
    reset_password(new_password, logout_all_sessions=1, old_password=current_password)
    with sec.service_write():
        frappe.get_doc({"doctype": "GRC Activity", "action": "Password changed", "actor": user,
            "internal": 1, "details": frappe.as_json({"user": user})}).insert(ignore_permissions=True)
    if frappe.session.user != "Guest":
        frappe.local.login_manager.logout()
    frappe.local.response.pop("home_page", None)
    frappe.local.response.pop("redirect_to", None)
    return {"redirect": "/login"}
