"""Personal-name validation and safe live owner labels; never read plaintext passwords."""
import unicodedata
import frappe
from frappe import _
from ia_maturity.grc.read_cache import read_cached, read_request

NAME_FIELDS = ("first_name", "middle_name", "last_name")


def valid_name(value):
    return bool(value and any(c.isalpha() for c in value) and len(value) <= 140 and all(
        c.isalpha() or unicodedata.category(c).startswith("M")
        or unicodedata.category(c) == "Pd" or c in " .'’·\u200c\u200d" for c in value))


def validate_name(value, required=False, user=None):
    if not value and not required:
        return
    if not valid_name(value):
        frappe.throw(_("Enter a personal name using letters, spaces, hyphens or apostrophes."))
    if user and matches_password(user, value):
        frappe.throw(_("A password cannot be used as a profile name."))


@read_cached
def matches_password(user, value):
    if not value:
        return False
    from frappe.utils.password import passlibctx
    rows = frappe.db.sql("""select password from `__Auth`
        where doctype='User' and name=%s and fieldname='password' and encrypted=0 limit 1""", user)
    return bool(rows and passlibctx.verify(value, rows[0][0]))


def name_values(user):
    values = [user.get(field) or "" for field in NAME_FIELDS]
    return set(filter(None, values + [user.get("full_name") or "",
        " ".join(filter(None, values)), " ".join(filter(None, [values[0], values[2]]))]))


def validate_password_name(user, password):
    if password and password in name_values(user):
        frappe.throw(_("Choose a password that is different from your profile name."))


def validate_user_names(doc, method=None):
    """Run before core User.validate consumes new_password; protect all document writes."""
    from ia_maturity.grc import security as sec
    if not sec.enabled() or doc.name in {"Guest", "Administrator"}:
        return
    roles = {row.role for row in doc.roles}
    if doc.get("grc_account_type") not in {"Customer", "Auditor"} and not roles & (sec.CUSTOMER_ROLES | sec.AUDITOR_ROLES):
        return
    before = doc.get_doc_before_save()
    changed = not before or any((doc.get(k) or "") != (before.get(k) or "") for k in NAME_FIELDS)
    if changed:
        for field in NAME_FIELDS:
            validate_name(doc.get(field) or "", required=field == "first_name", user=doc.name)
        if any(matches_password(doc.name, value) for value in name_values({field: doc.get(field) for field in NAME_FIELDS})):
            frappe.throw(_("A password cannot be used as a profile name."))
    validate_password_name(doc, doc.get("new_password"))


def safe_profile_names(user):
    values = {field: user.get(field) or "" for field in NAME_FIELDS}
    invalid = [field for field, value in values.items() if value and not valid_name(value)]
    # Check the stored hash too: an all-letter password can look like a valid personal name.
    if user.get("name"):
        invalid.extend(field for field, value in values.items()
            if field not in invalid and matches_password(user.name, value))
        combined = [" ".join(filter(None, values.values())),
            " ".join(filter(None, [values["first_name"], values["last_name"]]))]
        if any(matches_password(user.name, value) for value in combined):
            invalid = [field for field, value in values.items() if value]
    return {field: "" if field in invalid else value for field, value in values.items()}, invalid


@read_request
@read_cached
def display_name(user):
    doc = frappe.db.get_value("User", user, ["name", *NAME_FIELDS], as_dict=True)
    if not doc:
        return user
    values, invalid = safe_profile_names(doc)
    return user if invalid else " ".join(v for v in values.values() if v) or user
