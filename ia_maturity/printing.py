"""Self-contained IA report downloads, independent of website assets and letterheads."""
import re

import frappe
from frappe import _
from frappe.utils.print_format import print_language

FORMATS = {"IA Maturity Report", "IA Maturity Internal Report"}


def report_html(doc, print_format, language=None):
    """Render the app-owned report fragment without Frappe's website print wrapper."""
    if doc.doctype != "IA Maturity Assessment" or print_format not in FORMATS:
        frappe.throw(_("Unsupported IA Maturity report format."))
    from frappe.www.printview import validate_print_permission
    from ia_maturity.report_data import ia_report_guard
    validate_print_permission(doc)
    ia_report_guard("internal" if print_format == "IA Maturity Internal Report" else "client")
    template = frappe.get_doc("Print Format", print_format)
    previous = frappe.form_dict.get("language")
    try:
        if language:
            frappe.form_dict.language = language
        with print_language(language or doc.language or "en"):
            body = frappe.render_template(template.html, {"doc": doc})
    finally:
        if previous is None:
            frappe.form_dict.pop("language", None)
        else:
            frappe.form_dict.language = previous
    # These reports carry their own embedded logos, fonts and styles. Never fetch
    # a site URL (or an arbitrary custom resource) while rendering a report.
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "html.parser")
    resources = [tag.get("src", "") for tag in soup.find_all(["img", "script", "iframe"])]
    resources += [tag.get("href", "") for tag in soup.find_all("link")]
    resources += [match.strip().strip("'\\\"") for match in re.findall(r"url\((.*?)\)", body, re.I)]
    if any(url and not url.startswith("data:") for url in resources):
        frappe.throw(_("This report contains a non-embedded resource. Restore the standard IA Maturity print format before downloading."))
    return '<!doctype html><html><head><meta charset="utf-8"><style>' + (
        "@page{size:A4;margin:15mm 15mm 22mm} .page:after{content:counter(page)}"
        ".topage:after{content:counter(pages)}"
        "html,body{margin:0;padding:0}body{font-family:Helvetica,Arial,sans-serif;"
        "font-size:12px;line-height:1.5;color:#181818}*{box-sizing:border-box}"
        "table{border-collapse:collapse}img{max-width:100%}"
    ) + "</style></head><body>" + body + "</body></html>"


def render_pdf(doc, print_format="IA Maturity Report", language=None):
    from ia_maturity.grc.pdf import render_html
    return render_html(report_html(doc, print_format, language))



@frappe.whitelist(allow_guest=True)
def download_pdf(doctype, name, format=None, doc=None, no_letterhead=0,
                 language=None, letterhead=None, pdf_generator=None):
    if doctype != "IA Maturity Assessment" or format not in FORMATS:
        from frappe.utils.print_format import download_pdf as core_download
        # Pass only supported arguments: older v15 builds lack pdf_generator.
        return frappe.call(core_download, doctype=doctype, name=name, format=format,
            doc=doc, no_letterhead=no_letterhead, language=language,
            letterhead=letterhead, pdf_generator=pdf_generator)
    # Always load the persisted document; a supplied JSON doc cannot replace
    # the record whose permission and report content are being checked.
    assessment = frappe.get_doc(doctype, name)
    from ia_maturity.grc import security
    if security.enabled() and assessment.get("grc_assignment") and format == "IA Maturity Report":
        # Preserve release gating and the immutable artifact on every download path.
        from ia_maturity.grc.api import download_report
        return download_report(assessment.name)
    content = render_pdf(assessment, format, language)
    frappe.local.response.filename = name.replace(" ", "-").replace("/", "-") + ".pdf"
    frappe.local.response.filecontent = content
    frappe.local.response.type = "pdf"
