"""GRC admin policy for customer report PDF download and email.

Timing maps to the GRC Assessment Assignment workflow:
  After Audit  → Report Released only (historical default)
  Before Audit → from customer submission onward (Submitted … Report Released)

Download still prefers the immutable GRC Report Release PDF when present.
Before Audit without a release serves a preliminary on-the-fly PDF.

Staff (Auditor / GRC App Admin) are not limited by the customer delivery toggles;
they retain access for review once the assessment is readable.
"""
import hashlib
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc import security as sec

AFTER_AUDIT = "After Audit"
BEFORE_AUDIT = "Before Audit"

BEFORE_AUDIT_STATES = {
	"Submitted",
	"Resubmitted",
	"Under Review",
	"Clarification Required",
	"Approved",
	"Report Released",
}
AFTER_AUDIT_STATES = {"Report Released"}


def settings():
	doc = frappe.get_cached_doc("GRC Settings")
	timing = doc.get("report_access_timing") or AFTER_AUDIT
	if timing not in {AFTER_AUDIT, BEFORE_AUDIT}:
		timing = AFTER_AUDIT
	download = doc.get("allow_report_download")
	email = doc.get("allow_report_email")
	return {
		"allow_report_download": 1 if download in (None, "") else cint(download),
		"allow_report_email": 1 if email in (None, "") else cint(email),
		"report_access_timing": timing,
	}


def assignment_state(doc):
	if not doc.grc_assignment:
		return "Draft"
	return frappe.db.get_value("GRC Assessment Assignment", doc.grc_assignment, "workflow_state") or "Draft"


def timing_allows(state, timing=None):
	timing = timing or settings()["report_access_timing"]
	allowed = AFTER_AUDIT_STATES if timing == AFTER_AUDIT else BEFORE_AUDIT_STATES
	return state in allowed


def is_staff(user=None):
	return sec.is_admin(user) or sec.account_type(user) == "Auditor"


def customer_capabilities(doc):
	"""Flags for the assessment payload / ReportDelivery UI."""
	policy = settings()
	state = assignment_state(doc)
	released = bool(frappe.db.exists("GRC Report Release", {"assessment": doc.name}))
	staff = is_staff()
	if staff:
		# Staff bypass customer toggles but need a report-access role (report_access.py)
		# and a released PDF or a submitted assessment.
		from ia_maturity.grc.report_access import staff_access
		access = staff_access(doc)
		stage_ok = released or state in BEFORE_AUDIT_STATES
		download_ready = stage_ok and access["download"]
		email_ready = stage_ok and access["email"]
		view_ready = stage_ok and access["view"]
	else:
		state_ok = timing_allows(state, policy["report_access_timing"])
		download_ready = bool(policy["allow_report_download"] and state_ok and (
			released or policy["report_access_timing"] == BEFORE_AUDIT))
		email_ready = bool(policy["allow_report_email"] and state_ok and (
			released or policy["report_access_timing"] == BEFORE_AUDIT))
	return {
		**policy,
		"workflow_state": state,
		"released": released,
		"can_download_report": download_ready,
		# In-app report view: staff by role; customers whenever their PDF is available or released.
		"can_view_report": view_ready if staff else bool(download_ready or released),
		"can_email_report": email_ready,
		"report_preliminary": download_ready and not released,
	}


def require_download(doc):
	caps = customer_capabilities(doc)
	if not caps["can_download_report"]:
		if is_staff():
			frappe.throw(_("Report PDF download is not available to your role or at this stage of the review."), frappe.PermissionError)
		if not caps["allow_report_download"]:
			frappe.throw(_("Report PDF download is disabled by the GRC administrator."), frappe.PermissionError)
		frappe.throw(_("Report PDF download is not available at this stage of the review."), frappe.PermissionError)
	return caps


def require_email(doc):
	caps = customer_capabilities(doc)
	if not caps["can_email_report"]:
		if is_staff():
			frappe.throw(_("Report email is not available at this stage of the review."), frappe.PermissionError)
		if not caps["allow_report_email"]:
			frappe.throw(_("Report email is disabled by the GRC administrator."), frappe.PermissionError)
		frappe.throw(_("Report email is not available at this stage of the review."), frappe.PermissionError)
	return caps


def pdf_bytes(name, for_email=False):
	"""Authorized PDF content: released file when present, else preliminary render."""
	from ia_maturity.grc.reports import released_file
	doc = frappe.get_doc("IA Maturity Assessment", name)
	sec.require_assessment(doc)
	# Email and download are independent administrator capabilities.
	caps = require_email(doc) if for_email else require_download(doc)
	release_name = frappe.db.get_value("GRC Report Release", {"assessment": name}, "name")
	if release_name:
		_doc, release, file = released_file(name)
		payload = file.get_content()
		if hashlib.sha256(payload).hexdigest() != release.pdf_sha256:
			frappe.throw(_("The report file failed its integrity check. Contact the GRC administrator."))
		return payload, caps
	from ia_maturity.report_data import get_report_context
	from ia_maturity.grc.pdf import render
	context = get_report_context(doc, doc.language, audience="client")
	context["preliminary"] = True
	return render(context), caps
