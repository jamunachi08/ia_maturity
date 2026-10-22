"""Submission e-mails.

* Administrator mailbox  -> full INTERNAL report (English) with findings, roadmap and all answers.
* Respondent (optional)  -> CLIENT report only (sections chosen in Settings > Client Report Content),
                            in the assessment's report language.
"""

import frappe
from frappe import _
from frappe.utils import escape_html, get_url, get_url_to_form

from ia_maturity.branding import get_brand
from ia_maturity.report_data import get_report_context

CLIENT_FORMAT = "IA Maturity Report"
INTERNAL_FORMAT = "IA Maturity Internal Report"


def _attach(doc, print_format, language, as_admin=False):
	"""Render a PDF attachment in a given report language (and, for the internal report, with staff rights)."""
	user = frappe.session.user
	previous_lang = frappe.form_dict.get("language")
	try:
		frappe.form_dict["language"] = language
		if as_admin:
			frappe.set_user("Administrator")
		return frappe.attach_print(doc.doctype, doc.name, print_format=print_format, doc=doc)
	except Exception:
		frappe.log_error(title=f"IA Maturity: PDF attachment failed ({print_format})")
		return None
	finally:
		if as_admin:
			frappe.set_user(user)
		if previous_lang is None:
			frappe.form_dict.pop("language", None)
		else:
			frappe.form_dict["language"] = previous_lang


def _frame(brand, body):
	return f"""
	<div style="font-family:Helvetica,Arial,sans-serif;color:{brand.ink};max-width:640px">
	<div style="background:{brand.ink};padding:14px 18px;border-radius:8px 8px 0 0">
	 <img src="{brand.images.logo_white}" alt="{brand.product}" height="44" style="height:44px;width:auto;display:block">
	</div>
	<div style="height:4px;background:{brand.primary}"></div>
	<div style="padding:16px 4px">{body}</div>
	<div style="border-top:1px solid #D9E1E6;padding-top:12px;font-size:12px;color:{brand.slate}">
	 <img src="{brand.images.company_logo}" alt="{brand.company}" height="26" style="height:26px;width:auto;vertical-align:middle">
	 &nbsp;{brand.product_title} · {brand.company} ·
	 <a href="mailto:{brand.support_email}" style="color:{brand.primary}">{brand.support_email}</a>
	</div></div>"""


def _button(brand, link, label):
	return (
		f'<p><a href="{link}" style="display:inline-block;background:{brand.primary};color:#fff;padding:9px 16px;'
		f'border-radius:6px;text-decoration:none;font-weight:600">{label}</a></p>'
	)


def send_submission_email(assessment):
	try:
		doc = frappe.get_doc("IA Maturity Assessment", assessment)
		settings = frappe.get_single("IA Maturity Settings")
		brand = get_brand()
		subject = _("AlphaX | IA Maturity Assessment – {0} – {1}% ({2})")

		# ---------------------------------------------------------------- administrator: internal report
		if settings.notify_email:
			ctx = get_report_context(doc, "en", include_benchmark=False, audience="internal")
			rows = "".join(
				f"<tr><td style='padding:4px 10px'>{escape_html(s['title'])}</td>"
				f"<td style='padding:4px 10px;text-align:right'>{s['pct']:g}%</td>"
				f"<td style='padding:4px 10px'>{escape_html(s['level'])}</td></tr>"
				for s in ctx["sections"]
			)
			body = f"""
			<p><b style="color:#B42318">{_("INTERNAL")}</b> – {_("A new Internal Audit maturity assessment has been submitted.")}</p>
			<table style="border-collapse:collapse;font-size:14px">
			<tr><td style='padding:2px 10px'><b>{_("Entity")}</b></td><td>{escape_html(doc.entity)}</td></tr>
			<tr><td style='padding:2px 10px'><b>{_("Respondent")}</b></td><td>{escape_html(doc.respondent_name or '')}
			 &lt;{escape_html(doc.respondent_email or '')}&gt; {escape_html(doc.job_title or '')}</td></tr>
			<tr><td style='padding:2px 10px'><b>{_("Overall score")}</b></td>
			 <td><b>{ctx['overall']:g}% ({escape_html(ctx['level'])})</b></td></tr>
			<tr><td style='padding:2px 10px'><b>{_("Findings")}</b></td>
			 <td>{doc.findings_count} ({doc.immediate_count} {_("immediate")})</td></tr>
			<tr><td style='padding:2px 10px'><b>{_("Report language")}</b></td><td>{escape_html(doc.language or 'en')}</td></tr>
			</table>
			<h4>{_("Section scores")}</h4><table style="border-collapse:collapse;font-size:14px">{rows}</table>
			{f"<p><i>{escape_html(doc.gating_note)}</i></p>" if doc.gating_note else ""}
			<p style="font-size:12px;color:#5A6562">{_("Attached: the internal report (all sections). The respondent receives the client report only.")}</p>
			{_button(brand, get_url_to_form(doc.doctype, doc.name), _("Open the assessment"))}"""
			attachment = _attach(doc, INTERNAL_FORMAT, "en", as_admin=True) if settings.attach_pdf else None
			frappe.sendmail(
				recipients=[settings.notify_email],
				subject=_("[Internal] ") + subject.format(doc.entity, f"{ctx['overall']:g}", ctx["level"]),
				message=_frame(brand, body),
				attachments=[attachment] if attachment else [],
				reference_doctype=doc.doctype,
				reference_name=doc.name,
			)

		# ---------------------------------------------------------------- respondent: client report
		if settings.notify_respondent and doc.respondent_email and doc.respondent_email != settings.notify_email:
			lang = doc.language or "en"
			ctx = get_report_context(doc, lang, include_benchmark=False, audience="client")
			link = get_url(f"/ia-assessment?name={doc.name}")
			if lang == "ar":
				body = f"""<div dir="rtl" style="text-align:right">
				<p>شكراً لكم على إكمال تقييم نضج وظيفة التدقيق الداخلي لـ <b>{escape_html(doc.entity)}</b>.</p>
				<p>النتيجة العامة: <b dir="ltr">{ctx['overall']:g}%</b> ({escape_html(ctx['level_label'])}).</p>
				<p>تقرير النتائج مرفق، ويمكنكم الاطلاع عليه في أي وقت عبر البوابة.</p>
				{_button(brand, link, "عرض التقرير")}</div>"""
				subj = f"AlphaX | تقييم نضج التدقيق الداخلي – {doc.entity}"
			else:
				body = f"""
				<p>{_("Thank you for completing the Internal Audit maturity assessment for")} <b>{escape_html(doc.entity)}</b>.</p>
				<p>{_("Overall score")}: <b>{ctx['overall']:g}%</b> ({escape_html(ctx['level_label'])}).</p>
				<p>{_("Your results report is attached. You can also view it at any time in the portal.")}</p>
				{_button(brand, link, _("View your report"))}"""
				subj = _("AlphaX | Internal Audit Maturity Assessment – {0}").format(doc.entity)
			attachment = _attach(doc, CLIENT_FORMAT, lang) if settings.attach_pdf else None
			frappe.sendmail(
				recipients=[doc.respondent_email],
				subject=subj,
				message=_frame(brand, body),
				attachments=[attachment] if attachment else [],
				reference_doctype=doc.doctype,
				reference_name=doc.name,
			)
	except Exception:
		frappe.log_error(title="IA Maturity: submission e-mail failed")
