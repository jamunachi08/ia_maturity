"""Submission e-mail to the administrator (and optionally the respondent)."""

import frappe
from frappe import _
from frappe.utils import escape_html, get_url

from ia_maturity.branding import get_brand
from ia_maturity.report_data import get_report_context

PRINT_FORMAT = "IA Maturity Report"


def send_submission_email(assessment):
	try:
		doc = frappe.get_doc("IA Maturity Assessment", assessment)
		settings = frappe.get_single("IA Maturity Settings")
		recipients = []
		if settings.notify_email:
			recipients.append(settings.notify_email)
		if settings.notify_respondent and doc.respondent_email:
			recipients.append(doc.respondent_email)
		recipients = list(dict.fromkeys(recipients))
		if not recipients:
			return

		ctx = get_report_context(doc)
		rows = "".join(
			f"<tr><td style='padding:4px 10px'>{escape_html(s['title'])}</td>"
			f"<td style='padding:4px 10px;text-align:right'>{s['pct']:g}%</td>"
			f"<td style='padding:4px 10px'>{escape_html(s['level'])}</td></tr>"
			for s in ctx["sections"]
		)
		link = get_url(f"/app/ia-maturity-assessment/{doc.name}")
		brand = get_brand()
		message = f"""
		<div style="font-family:Helvetica,Arial,sans-serif;color:{brand.ink};max-width:640px">
		<div style="background:{brand.ink};padding:14px 18px;border-radius:8px 8px 0 0">
		 <img src="{brand.images.logo_white}" alt="{brand.product}" height="44" style="height:44px;width:auto;display:block">
		</div>
		<div style="height:4px;background:{brand.primary}"></div>
		<div style="padding:16px 4px">
		<p>{_("A new Internal Audit maturity assessment has been submitted.")}</p>
		<table style="border-collapse:collapse;font-size:14px">
		<tr><td style='padding:2px 10px'><b>{_("Entity")}</b></td><td>{escape_html(doc.entity)}</td></tr>
		<tr><td style='padding:2px 10px'><b>{_("Respondent")}</b></td><td>{escape_html(doc.respondent_name or '')}
		 &lt;{escape_html(doc.respondent_email or '')}&gt; {escape_html(doc.job_title or '')}</td></tr>
		<tr><td style='padding:2px 10px'><b>{_("Overall score")}</b></td>
		 <td><b>{ctx['overall']:g}% ({escape_html(ctx['level'])})</b></td></tr>
		<tr><td style='padding:2px 10px'><b>{_("Findings")}</b></td>
		 <td>{doc.findings_count} ({doc.immediate_count} {_("immediate")})</td></tr>
		</table>
		<h4>{_("Section scores")}</h4><table style="border-collapse:collapse;font-size:14px">{rows}</table>
		{f"<p><i>{escape_html(doc.gating_note)}</i></p>" if doc.gating_note else ""}
		<p><a href="{link}" style="display:inline-block;background:{brand.primary};color:#fff;padding:9px 16px;
		 border-radius:6px;text-decoration:none;font-weight:600">{_("Open the assessment")}</a></p>
		</div>
		<div style="border-top:1px solid #D9E1E6;padding-top:12px;font-size:12px;color:{brand.slate}">
		 <img src="{brand.images.company_logo}" alt="{brand.company}" height="26" style="height:26px;width:auto;vertical-align:middle">
		 &nbsp;{brand.product_title} · {brand.company} · <a href="mailto:{brand.support_email}" style="color:{brand.primary}">{brand.support_email}</a>
		</div></div>"""

		attachments = []
		if settings.attach_pdf:
			try:
				attachments.append(
					frappe.attach_print(doc.doctype, doc.name, print_format=PRINT_FORMAT, doc=doc)
				)
			except Exception:
				frappe.log_error(title="IA Maturity: PDF attachment failed")

		frappe.sendmail(
			recipients=recipients,
			subject=_("AlphaX | IA Maturity Assessment – {0} – {1}% ({2})").format(
				doc.entity, f"{ctx['overall']:g}", ctx["level"]
			),
			message=message,
			attachments=attachments,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(title="IA Maturity: submission e-mail failed")
