"""Who can see assessment reports: configurable staff roles on top of the tenant boundary.

Order of checks, all required:
  1. The user can read the assessment (organization, assignment and department boundary).
  2. The report exists at this stage (submitted onward, or released).
  3. Staff: the user has a role allowed to view/download/email reports, or is the assessment's
     assigned consultant or reviewer (when that switch is on). Admins always can.
     Customers: unchanged release policy (report_policy.py).
Defaults: GRC App Admin and GRC Manager may view, download and email; assigned staff keep access.
"""
import frappe
from frappe import _
from frappe.utils import cint

from ia_maturity.grc import security as sec

STAFF_ROLES = ("GRC App Admin", "GRC Manager", "GRC Reviewer", "GRC Consultant", "GRC Auditor")
CAPABILITIES = ("view", "download", "email")
DEFAULT_ROLES = {
    "GRC App Admin": {"view": 1, "download": 1, "email": 1},
    "GRC Manager": {"view": 1, "download": 1, "email": 1},
}


def setup():
    """Store defaults once: Frappe reads an unset Single checkbox as 0, which would switch access off."""
    stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype='GRC Settings'"))
    if "report_access_assigned_staff" not in stored:
        frappe.db.set_single_value("GRC Settings", "report_access_assigned_staff", 1)
    if "report_access_roles" not in stored:
        frappe.db.set_single_value("GRC Settings", "report_access_roles", frappe.as_json(DEFAULT_ROLES))


def policy():
    raw = frappe.get_cached_doc("GRC Settings").get("report_access_roles")
    roles = frappe.parse_json(raw) if raw else None
    if not isinstance(roles, dict):
        roles = DEFAULT_ROLES
    clean = {role: {cap: 1 if cint((roles.get(role) or {}).get(cap)) else 0 for cap in CAPABILITIES} for role in STAFF_ROLES}
    clean["GRC App Admin"] = {cap: 1 for cap in CAPABILITIES}
    assigned = frappe.get_cached_doc("GRC Settings").get("report_access_assigned_staff")
    return {"roles": clean, "assigned_staff": 1 if assigned in (None, "") else cint(assigned)}


def _assigned(doc, user):
    if not doc.get("grc_assignment"):
        return False
    row = frappe.db.get_value("GRC Assessment Assignment", doc.grc_assignment, ["consultant", "reviewer"], as_dict=True)
    return bool(row and user in {row.consultant, row.reviewer})


def staff_access(doc, user=None):
    """{view, download, email} for a staff user who can already read the assessment."""
    user = user or frappe.session.user
    if sec.is_admin(user):
        return {cap: True for cap in CAPABILITIES}
    config = policy()
    roles = sec.roles(user)
    access = {cap: any(config["roles"].get(role, {}).get(cap) for role in roles) for cap in CAPABILITIES}
    if config["assigned_staff"] and _assigned(doc, user):
        access = {cap: True for cap in CAPABILITIES}
    return access


def can_view_reports(user=None):
    """Navigation hint only: whether any role of this staff user may view reports."""
    user = user or frappe.session.user
    if sec.is_admin(user):
        return True
    if sec.account_type(user) != "Auditor":
        return False
    config = policy()
    return config["assigned_staff"] or any(config["roles"].get(r, {}).get("view") for r in sec.roles(user))


@frappe.whitelist()
def report_access_settings():
    sec.require_admin()
    return {**policy(), "staff_roles": list(STAFF_ROLES), "capabilities": list(CAPABILITIES)}


@frappe.whitelist(methods=["POST"])
def save_report_access(roles, assigned_staff=1):
    sec.require_admin()
    roles = frappe.parse_json(roles) if isinstance(roles, str) else roles
    if not isinstance(roles, dict) or any(role not in STAFF_ROLES for role in roles):
        frappe.throw(_("Choose valid staff roles."))
    clean = {}
    for role in STAFF_ROLES:
        row = roles.get(role) or {}
        if not isinstance(row, dict):
            frappe.throw(_("Choose valid report permissions."))
        values = {cap: 1 if cint(row.get(cap)) else 0 for cap in CAPABILITIES}
        if (values["download"] or values["email"]) and not values["view"]:
            frappe.throw(_("A role that can download or email reports must also be able to view them."))
        clean[role] = values
    clean["GRC App Admin"] = {cap: 1 for cap in CAPABILITIES}
    before = policy()
    doc = frappe.get_single("GRC Settings")
    doc.report_access_roles = frappe.as_json(clean)
    doc.report_access_assigned_staff = 1 if cint(assigned_staff) else 0
    with sec.service_write():
        doc.save(ignore_permissions=True)
    frappe.clear_document_cache("GRC Settings", "GRC Settings")
    sec.log("Report access changed", details={"before": before, "after": policy()})
    return policy()


@frappe.whitelist()
def report_view(name):
    """The report as structured data for the in-app view: same content as the PDF."""
    from ia_maturity.grc.report_policy import customer_capabilities
    doc = frappe.get_doc("IA Maturity Assessment", name)
    sec.require_assessment(doc)
    caps = customer_capabilities(doc)
    if not caps.get("can_view_report"):
        frappe.throw(_("This report is not available to you at this stage."), frappe.PermissionError)
    release = frappe.db.get_value("GRC Report Release", {"assessment": name}, ["report_context"], as_dict=True)
    if release and release.report_context:
        context = frappe.parse_json(release.report_context)
        context["preliminary"] = False
    else:
        from ia_maturity.report_data import get_report_context
        context = get_report_context(doc, doc.language, audience="client")
        context["preliminary"] = True
    from ia_maturity.grc.color_policy import get_ranges
    from ia_maturity.grc.report_style import report_context
    view = report_context(context, get_ranges())
    view["can_download_report"] = bool(caps.get("can_download_report"))
    view["report_id"] = doc.get("grc_report_id") or doc.name
    view["assessment"] = doc.name
    sec.log("Report viewed", doc.entity, doc.get("grc_assignment"), doc.name, details={"preliminary": context["preliminary"]})
    return view


@frappe.whitelist()
def report_list(search=None, page=1):
    """Submitted assessments whose report this user may view, newest first."""
    sec.require_login()
    page = max(1, cint(page) or 1)
    entities = sec.entities()
    if not entities:
        return {"rows": [], "page": page, "has_more": False}
    filters = {"entity": ["in", entities], "docstatus": 1}
    search = str(search or "").strip()[:80]
    or_filters = {"entity": ["like", f"%{search}%"], "grc_report_id": ["like", f"%{search}%"], "name": ["like", f"%{search}%"]} if search else None
    rows = frappe.get_all("IA Maturity Assessment", filters=filters, or_filters=or_filters,
        fields=["name", "entity", "respondent", "grc_department", "grc_assessment_type", "template", "grc_report_id",
                "grc_assignment", "overall_score", "maturity_level", "modified", "docstatus"],
        order_by="modified desc", limit_start=(page - 1) * 25, limit_page_length=26)
    from ia_maturity.grc.report_policy import customer_capabilities
    out = []
    for row in rows[:25]:
        if not sec.can_read_assessment(row):
            continue
        caps = customer_capabilities(frappe._dict(row, doctype="IA Maturity Assessment"))
        if caps.get("can_view_report"):
            out.append({"name": row.name, "entity": row.entity, "report_id": row.grc_report_id or row.name,
                "assessment_type": row.grc_assessment_type, "overall_score": row.overall_score,
                "maturity_level": row.maturity_level, "modified": row.modified,
                "state": caps.get("workflow_state"), "released": caps.get("released"),
                "can_download_report": caps.get("can_download_report")})
    return {"rows": out, "page": page, "has_more": len(rows) > 25}
