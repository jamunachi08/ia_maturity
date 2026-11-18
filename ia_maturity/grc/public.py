"""Minimal public endpoints; never return organizations or assessment data."""
import frappe
from frappe import _
from frappe.utils import validate_email_address
from ia_maturity.grc.auth import limit


@frappe.whitelist(allow_guest=True)
def info():
    s = frappe.get_single("GRC Settings")
    result = {key: s.get(key) for key in (
        "privacy_en", "privacy_ar", "terms_en", "terms_ar", "framework_version", "content_approved")}
    from ia_maturity.grc import security as sec
    if sec.enabled() and frappe.db.exists("DocType", "GRC Site Content"):
        from ia_maturity.grc.site_content import published
        content = published()
        for key in ("privacy", "terms"):
            if 'legal.' + key in content:
                for language in ('en', 'ar'):
                    result[key + '_' + language] = content['legal.' + key].get(language, '')
    return result


@frappe.whitelist(allow_guest=True, methods=["POST"])
def consultation(full_name, email, message, organization=None, service=None):
    limit("consultation-ip", getattr(frappe.local, "request_ip", None) or "local", 5)
    if not full_name or not message or not validate_email_address(email):
        frappe.throw(_("Enter your name, work email, and request."))
    frappe.get_doc(dict(doctype="GRC Consultation Request",
        full_name=str(full_name)[:140], email=email.strip().lower()[:140],
        message=str(message)[:5000], organization=str(organization or "")[:140],
        service=str(service or "GRC consultation")[:140])).insert(ignore_permissions=True)
    return {"message": _("Your consultation request has been recorded.")}


@frappe.whitelist(allow_guest=True)
def site_content():
    """Only approved site copy is public; drafts and audit history stay private."""
    from ia_maturity.grc.site_content import published
    return published()
