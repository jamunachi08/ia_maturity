"""Shared release and attachment authorization for report delivery."""
import hashlib
import frappe
from frappe import _
from ia_maturity.grc import security as sec


def released_file(name):
    doc = frappe.get_doc("IA Maturity Assessment", name)
    sec.require_assessment(doc)
    release_name = frappe.db.get_value("GRC Report Release", {"assessment": name}, "name")
    if not release_name:
        sec.deny()
    release = frappe.get_doc("GRC Report Release", release_name)
    if not release.pdf_file or not frappe.db.exists("File", release.pdf_file):
        frappe.throw(_("The released PDF is unavailable. Contact your GRC administrator."))
    file = frappe.get_doc("File", release.pdf_file)
    sec.check_file_url(file.file_url)
    return doc, release, file


def content(name):
    """Customer PDF bytes with GRC admin download/timing policy enforced."""
    from ia_maturity.grc.report_policy import pdf_bytes
    payload, _caps = pdf_bytes(name)
    return payload


def released_content(name):
    """Legacy helper: released PDF only (no preliminary). Still checks download policy."""
    from ia_maturity.grc.report_policy import require_download
    doc, release, file = released_file(name)
    require_download(doc)
    payload = file.get_content()
    if hashlib.sha256(payload).hexdigest() != release.pdf_sha256:
        frappe.throw(_("The report file failed its integrity check. Contact the GRC administrator."))
    return payload
