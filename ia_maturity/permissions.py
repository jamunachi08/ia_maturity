"""Permission helpers and the User sign-up hook."""

import frappe

RESPONDENT = "IA Assessment Respondent"
STAFF_ROLES = {"IA Maturity Manager", "IA Maturity Reviewer", "System Manager", "Administrator"}


def is_staff(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(STAFF_ROLES & set(frappe.get_roles(user)))


def allowed_domains():
	raw = frappe.db.get_single_value("IA Maturity Settings", "allowed_domains") or ""
	return [d.strip().lower().lstrip("@") for d in raw.replace(",", "\n").splitlines() if d.strip()]


def email_domain_allowed(email):
	domains = allowed_domains()
	if not domains:
		return True
	return (email or "").split("@")[-1].lower() in domains


def on_user_created(doc, method=None):
	"""Give new website users the respondent role (if enabled and their domain is allowed)."""
	if doc.name in ("Administrator", "Guest") or doc.user_type != "Website User":
		return
	if not frappe.db.get_single_value("IA Maturity Settings", "auto_assign_respondent_role"):
		return
	if not email_domain_allowed(doc.email):
		return
	if RESPONDENT not in [r.role for r in doc.roles]:
		doc.add_roles(RESPONDENT)


# IA Maturity Action: respondents see actions raised from their own assessments ----------
def _respondent_only(user):
	return not is_staff(user) and RESPONDENT in frappe.get_roles(user)


def action_query_conditions(user=None):
	user = user or frappe.session.user
	if not _respondent_only(user):
		return ""
	u = frappe.db.escape(user)
	return (
		"`tabIA Maturity Action`.assessment in (select name from `tabIA Maturity Assessment` "
		f"where owner = {u} or respondent = {u})"
	)


def action_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if not _respondent_only(user):
		return None  # fall back to standard role permissions
	if ptype not in ("read", "print", "report", None):
		return False
	owner, respondent = frappe.db.get_value("IA Maturity Assessment", doc.assessment, ["owner", "respondent"]) or (
		None,
		None,
	)
	return user in (owner, respondent)
