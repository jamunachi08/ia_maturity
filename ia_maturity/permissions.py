"""Permission helpers and the User sign-up hook."""

import frappe

RESPONDENT = "IA Assessment Respondent"
STAFF_ROLES = {"IA Maturity Manager", "IA Maturity Reviewer", "System Manager", "Administrator"}


def is_staff(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(STAFF_ROLES & set(frappe.get_roles(user)))


def show_on_apps_screen():
	return is_staff()


def allowed_domains():
	raw = frappe.db.get_single_value("IA Maturity Settings", "allowed_domains") or ""
	return [d.strip().lower().lstrip("@") for d in raw.replace(",", "\n").splitlines() if d.strip()]


def email_domain_allowed(email):
	domains = allowed_domains()
	if not domains:
		return True
	return (email or "").split("@")[-1].lower() in domains


def on_user_created(doc, method=None):
	"""Give self-registered website users the respondent role (if enabled and their domain is allowed).

	Only self sign-ups (session user is Guest) qualify. Users created by an administrator are left
	alone: Frappe saves every new user as a Website User until desk roles are added, so assigning
	here would also tag staff accounts. Administrators add the role themselves when inviting.
	"""
	if doc.name in ("Administrator", "Guest") or doc.user_type != "Website User":
		return
	if frappe.session.user != "Guest":
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
		# Must be True, not None: Frappe v16 treats any falsy hook result as "deny".
		# Hooks can only restrict, so True simply defers to the normal role permissions.
		return True
	if ptype not in ("read", "print", "report", None):
		return False
	owner, respondent = frappe.db.get_value("IA Maturity Assessment", doc.assessment, ["owner", "respondent"]) or (
		None,
		None,
	)
	return user in (owner, respondent)
