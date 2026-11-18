"""Authorized PDF attachments through the site's standard outgoing email queue."""
import re
import frappe
from frappe import _
from frappe.utils import escape_html, get_url
from ia_maturity.grc import security as sec
from ia_maturity.grc import report_policy


def report_recipient(doc):
    """Only registered, currently authorized customers can receive a report."""
    user = frappe.session.user if sec.account_type() == "Customer" else doc.respondent
    if not user or user in {"Guest", "Administrator"} or sec.account_type(user) != "Customer":
        sec.deny()
    if not frappe.db.get_value("User", user, "enabled") or not sec.can_read_assessment(doc, user):
        sec.deny()
    email = frappe.db.get_value("User", user, "email")
    if not email:
        sec.deny()
    return email


@frappe.whitelist(methods=["POST"])
def email_report(name):
    from ia_maturity.grc.auth import limit
    doc = frappe.get_doc("IA Maturity Assessment", name)
    sec.require_assessment(doc)
    caps = report_policy.require_email(doc)
    user = frappe.session.user
    recipient = report_recipient(doc)
    limit("report-email", user, 5, seconds=900)
    pdf, _pdf_caps = report_policy.pdf_bytes(name, for_email=True)
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", doc.name)[:120] + ".pdf"
    url = get_url("/grc/customer/assessments/" + doc.name, allow_header_override=False)
    from ia_maturity.grc.organization_profile import assessment_kind
    kind = assessment_kind(doc)
    if caps["released"]:
        subject = _("AlphaX | Your {0} released report").format(kind)
        lead = _("Your released assessment report is attached as a PDF.")
        cta = _("View report and download PDF")
        ref_doctype, ref_name = "GRC Report Release", frappe.db.get_value(
            "GRC Report Release", {"assessment": doc.name}, "name")
    else:
        subject = _("AlphaX | Your {0} assessment report PDF").format(kind)
        lead = _("Your assessment report is attached as a PDF. This preliminary report has not been reviewed or approved.")
        cta = _("View assessment")
        ref_doctype, ref_name = doc.doctype, doc.name
    queued = frappe.sendmail(recipients=[recipient], subject=subject,
        message='<p>' + escape_html(lead) + '</p><p><a href="' +
        escape_html(url) + '">' + escape_html(cta) + '</a></p><p>' +
        escape_html(_("Sign in to view the report. Access is checked when you open the link.")) + '</p>',
        attachments=[{"fname": filename, "fcontent": pdf}],
        reference_doctype=ref_doctype, reference_name=ref_name,
        delayed=True, now=False)
    if not queued:
        frappe.throw(_("Report email could not be queued. Contact your administrator."), frappe.OutgoingEmailError)
    sec.log("Report email requested", doc.entity, doc.grc_assignment, doc.name,
        details={"recipient": recipient, "preliminary": not caps["released"]}, internal=False)
    return {"queued": True, "recipient": recipient,
        "message": _("Report PDF email queued. Delivery depends on the site's outgoing email service.")}
