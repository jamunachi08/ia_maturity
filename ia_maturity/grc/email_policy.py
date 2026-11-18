"""GRC signup policy. Existing customers retain their verified sign-in identity."""
import re
import frappe
from frappe import _
from frappe.utils import validate_email_address

POLICIES = {"All valid emails", "Allowed domains only"}


def normalize_domains(raw):
    domains = []
    for item in re.split(r"[\s,;]+", str(raw or "")):
        if not item:
            continue
        try:
            domain = item.lstrip("@").encode("idna").decode("ascii").lower()
        except UnicodeError:
            frappe.throw(_("Enter valid email domains, one per line."))
        if len(domain) > 253 or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", domain):
            frappe.throw(_("Enter valid email domains, one per line."))
        if domain not in domains:
            domains.append(domain)
    if len(domains) > 100:
        frappe.throw(_("Use at most 100 signup email domains."))
    return "\n".join(domains)


def validate_policy(doc):
    policy = doc.signup_email_policy or "All valid emails"
    if policy not in POLICIES:
        frappe.throw(_("Choose a valid signup email policy."))
    doc.signup_email_policy = policy
    doc.signup_allowed_domains = normalize_domains(doc.signup_allowed_domains)
    if policy == "Allowed domains only" and not doc.signup_allowed_domains:
        frappe.throw(_("Add at least one allowed signup email domain."))


def check_email(email, new_account=False):
    email = str(email or "").strip().lower()
    # Frappe accepts address lists/display names; a login identifier must be one bare address.
    if len(email) > 140 or re.search(r"[\s,;<>]", email) or email.count("@") != 1 or not validate_email_address(email):
        frappe.throw(_("Enter a valid email address."))
    if new_account:
        settings = frappe.get_single("GRC Settings")
        if settings.signup_email_policy == "Allowed domains only":
            domain = email.rsplit("@", 1)[1]
            if domain not in normalize_domains(settings.signup_allowed_domains).splitlines():
                frappe.throw(_("Signup is limited to the email domains approved by your GRC administrator."))
    return email
