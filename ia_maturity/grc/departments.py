"""Server-owned IA/GRC entitlements, staff membership and second-audit approval.

Organization membership never grants a second department. Department membership
never grants a different department's assessments, even on a shared company.
"""
import frappe
from frappe import _
from frappe.utils import cint, now_datetime
from ia_maturity.grc import security as sec
from ia_maturity.grc.read_cache import read_cached

BUILTIN_TYPES = ("Internal Audit", "GRC")
DEPARTMENT_TABLES = ("GRC Department", "GRC Department Staff", "GRC Department Grant", "GRC Audit Type Request")


def types():
    """Every configured assessment type (department), active or not, in display order."""
    from ia_maturity.grc.assessment_types import type_names
    return tuple(type_names()) or BUILTIN_TYPES


def validate_type(value):
    if value not in types():
        frappe.throw(_("Choose a valid assessment type."))
    if ready() and not frappe.db.get_value("GRC Department", value, "active"):
        frappe.throw(_("This department is inactive."))
    return value


def ready():
    return frappe.db.table_exists("GRC Department Grant")


@read_cached
def memberships(user=None):
    if not ready():
        return []
    return frappe.get_all("GRC Department Staff", filters={"user": user or frappe.session.user, "active": 1},
        fields=["name", "department", "role", "active", "user"])


@read_cached
def staff_types(user=None):
    user = user or frappe.session.user
    if sec.is_admin(user):
        return set(types())
    if sec.account_type(user) != "Auditor" or not frappe.db.get_value("User", user, "enabled"):
        return set()
    return {r.department for r in memberships(user) if frappe.db.get_value("GRC Department", r.department, "active")}


@read_cached
def manager(department, user=None):
    user = user or frappe.session.user
    if not frappe.db.get_value("User", user, "enabled"):
        return False
    if department not in types() or not frappe.db.get_value("GRC Department", department, "active"):
        return False
    return sec.is_admin(user) or any(r.department == department and r.role == "Manager" for r in memberships(user))


@read_cached
def grants(entity):
    if not ready():
        return []
    return frappe.get_all("GRC Department Grant", filters={"entity": entity, "active": 1},
        fields=["name", "department", "profile_access", "active"])


@read_cached
def entity_types(entity):
    return {r.department for r in grants(entity)}


def can_access_entity(entity, user=None):
    user = user or frappe.session.user
    if sec.is_admin(user):
        return True
    if sec.account_type(user) == "Auditor":
        return bool(entity_types(entity) & staff_types(user))
    return True  # Customer membership is checked separately by security.py.


def kind(doc):
    if doc.get("grc_department"):
        return doc.grc_department
    if doc.get("grc_assessment_type"):
        return doc.grc_assessment_type
    if doc.get("assessment"):
        return frappe.db.get_value("IA Maturity Assessment", doc.assessment, "grc_assessment_type") or "Internal Audit"
    if doc.get("template"):
        return frappe.db.get_value("IA Maturity Template", doc.template, "assessment_type") or "Internal Audit"
    if doc.get("entity"):
        types = entity_types(doc.entity)
        if len(types) == 1:
            return next(iter(types))


def can_read(doc, user=None):
    user = user or frappe.session.user
    if sec.is_admin(user):
        return True
    dept = kind(doc)
    if dept and dept not in entity_types(doc.entity):
        return False
    if dept and sec.account_type(user) == "Auditor" and not any(g.department == dept and g.profile_access for g in grants(doc.entity)):
        return False  # Basics-only grants cannot disclose full-profile assessment artifacts.
    return sec.account_type(user) != "Auditor" or (dept in staff_types(user) if dept else False)


def can_profile(entity, user=None):
    user = user or frappe.session.user
    return sec.is_admin(user) or sec.account_type(user) != "Auditor" or any(
        g.profile_access and g.department in staff_types(user) for g in grants(entity))


def allowed_types(entity=None, user=None):
    user = user or frappe.session.user
    if sec.is_admin(user) or sec.account_type(user) == "Auditor":
        return sorted(staff_types(user))
    entities = [entity] if entity else sec.entities(user)
    allowed = set()
    for name in entities:
        existing = entity_types(name)
        # A first-time customer has a choice; an existing grant fixes entitlement.
        allowed |= existing or (set(types()) if not frappe.db.exists("GRC Department Grant", {"entity": name}) else set())
    pending = frappe.get_all("GRC Onboarding Invitation", filters={"email": user,
        "status": ["not in", ["Completed", "Revoked", "Pending Invitation Approval"]]}, pluck="assessment_type")
    return sorted(set(filter(None, pending)) if pending else allowed)


def grant(entity, department, source, profile_access=1):
    """Internal helper. Callers must hold company lock and validate their transition."""
    name = frappe.db.get_value("GRC Department Grant", {"entity": entity, "department": department}, "name")
    doc = frappe.get_doc("GRC Department Grant", name) if name else frappe.new_doc("GRC Department Grant")
    doc.update(dict(entity=entity, department=validate_type(department), active=1,
        profile_access=cint(profile_access), source=source))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    return doc


def ensure_start(entity, department):
    validate_type(department)
    frappe.db.sql("select name from `tabIA Maturity Entity` where name=%s for update", entity)
    if sec.account_type() == "Auditor" and department not in staff_types():
        sec.deny()
    current = entity_types(entity)
    if department in current:
        return
    if sec.is_admin():
        grant(entity, department, "Administrator")
    elif not current and not frappe.db.exists("GRC Department Grant", {"entity": entity}):
        if sec.account_type() == "Customer" and frappe.db.exists("GRC Onboarding Invitation", {
            "email": frappe.session.user, "status": ["not in", ["Completed", "Revoked"]]}):
            frappe.throw(_("Complete your department invitation first."))
        grant(entity, department, "First audit choice")
    else:
        frappe.throw(_("A department manager must approve a second audit type."), frappe.PermissionError)


def bootstrap_access():
    entities = sec.entities()
    return {"allowed_assessment_types": allowed_types(),
        "audit_type_access": {e: allowed_types(e) for e in entities},
        "department_memberships": memberships(),
        "can_manage_departments": any(manager(d) for d in types())}


@frappe.whitelist()
def department_staff():
    sec.require_login()
    managed = [d for d in types() if manager(d)]
    if not managed:
        sec.deny()
    rows = frappe.get_all("GRC Department Staff", filters={"department": ["in", managed]},
        fields=["name", "user", "department", "role", "active"])
    from ia_maturity.grc.identity import display_name
    for row in rows:
        row["full_name"] = display_name(row.user)
    return rows


@frappe.whitelist(methods=["POST"])
def save_department_staff(user, department, role="Consultant", active=1):
    sec.require_login()
    validate_type(department)
    if not manager(department) or role not in {"Consultant", "Reviewer", "Manager"}:
        sec.deny()
    if role == "Manager" and not sec.is_admin():
        sec.deny()
    if sec.account_type(user) != "Auditor":
        frappe.throw(_("Select an existing staff account."))
    if user == frappe.session.user and not cint(active):
        frappe.throw(_("Keep your own department access active."))
    name = frappe.db.get_value("GRC Department Staff", {"user": user, "department": department}, "name")
    doc = frappe.get_doc("GRC Department Staff", name) if name else frappe.new_doc("GRC Department Staff")
    doc.update(dict(user=user, department=department, role=role, active=cint(active)))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    if not cint(active):
        # Expire unsent department PDFs when staff entitlement is revoked.
        for row in frappe.get_all("Email Queue", filters={"reference_doctype": "IA Maturity Assessment",
            "status": ["in", ["Not Sent", "Error", "Partially Sent"]]}, fields=["name", "reference_name", "owner"]):
            if row.owner == user and frappe.db.get_value("IA Maturity Assessment", row.reference_name, "grc_assessment_type") == department:
                frappe.db.set_value("Email Queue", row.name, "status", "Expired")
    sec.log("Department staff updated", details={"user": user, "department": department, "role": role, "active": doc.active})
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def request_audit_type(entity, assessment_type):
    sec.require_entity(entity, manage=True)
    if sec.account_type() != "Customer":
        sec.deny()
    return create_audit_request(entity, assessment_type, frappe.session.user)


def create_audit_request(entity, assessment_type, customer):
    """Internal transition used after customer authorization or trusted invite precheck."""
    department = validate_type(assessment_type)
    frappe.db.sql("select name from `tabIA Maturity Entity` where name=%s for update", entity)
    current = entity_types(entity)
    if not current or department in current:
        frappe.throw(_("Choose an additional audit type."))
    existing = frappe.db.get_value("GRC Audit Type Request", {"entity": entity, "department": department,
        "status": ["in", ["Pending Source Approval", "Pending Target Approval"]]}, "name")
    if existing:
        return {"name": existing, "status": frappe.db.get_value("GRC Audit Type Request", existing, "status")}
    with sec.service_write():
        doc = frappe.get_doc({"doctype": "GRC Audit Type Request", "entity": entity, "department": department,
            "source_department": sorted(current)[0], "requested_by": customer,
            "status": "Pending Source Approval"}).insert(ignore_permissions=True)
    sec.log("Additional audit requested", entity=entity, details={"request": doc.name}, internal=False)
    return {"name": doc.name, "status": doc.status}


def invitation_precheck(email, department, company):
    """Return only a pending result to the sender, never another department's company."""
    owned = sorted(frappe.get_all("GRC Organization Membership", filters={"user": email,
        "membership_role": "Organization Admin", "active": 1}, pluck="entity"))
    existing_types = set().union(*(entity_types(e) for e in owned)) if owned else set()
    if not existing_types or department in existing_types:
        return None
    source = company if company in owned else next((e for e in owned if entity_types(e)), None)
    if not source:
        return None
    request = create_audit_request(source, department, email)
    return {"name": request["name"], "status": "Pending manager approval", "pending_approval": True}


@frappe.whitelist()
def audit_type_requests(entity=None):
    sec.require_login()
    filters = {"entity": entity} if entity else {}
    if entity and sec.account_type() == "Customer":
        sec.require_entity(entity)
    rows = frappe.get_all("GRC Audit Type Request", filters=filters, fields=["*"], order_by="creation desc")
    visible = []
    for row in rows:
        customer = sec.account_type() == "Customer" and row.entity in sec.entities()
        source = manager(row.source_department)
        target = bool(row.source_approved_by) and manager(row.department)
        if not (customer or source or target):
            continue
        visible.append({k: row.get(k) for k in ("name", "entity", "department", "source_department", "status",
            "requested_by", "reason", "creation")})
        visible[-1]["assessment_type"] = row.department
        visible[-1]["can_decide"] = bool(not customer and (source if row.status == "Pending Source Approval" else target)
            and row.status in {"Pending Source Approval", "Pending Target Approval"})
    return visible


@frappe.whitelist(methods=["POST"])
def decide_audit_type_request(name, approve, reason=""):
    sec.require_login()
    doc = frappe.get_doc("GRC Audit Type Request", name, for_update=True)
    if doc.status not in {"Pending Source Approval", "Pending Target Approval"}:
        frappe.throw(_("This request has already been decided."))
    department = doc.source_department if doc.status == "Pending Source Approval" else doc.department
    if not manager(department):
        sec.deny()
    if (doc.source_department not in entity_types(doc.entity)
            or sec.membership(doc.entity, doc.requested_by) != "Organization Admin"
            or not frappe.db.get_value("User", doc.requested_by, "enabled")):
        frappe.throw(_("The requesting customer's organization access has changed. Submit a new request."))
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        frappe.throw(_("Enter an approval or rejection reason."))
    frappe.db.sql("select name from `tabIA Maturity Entity` where name=%s for update", doc.entity)
    if not cint(approve):
        doc.status = "Rejected"
    elif doc.status == "Pending Source Approval":
        doc.status, doc.source_approved_by = "Pending Target Approval", frappe.session.user
    else:
        grant(doc.entity, doc.department, doc.name)
        doc.status, doc.approved_by = "Approved", frappe.session.user
    doc.reason, doc.decided_on = reason.strip(), now_datetime()
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Additional audit request decided", doc.entity, details={"request": doc.name, "status": doc.status}, internal=False)
    return {"name": doc.name, "status": doc.status}


def guard(doc, method=None):
    if not sec.enabled() or frappe.flags.get("in_migrate") or frappe.flags.get("in_install"):
        return
    if not frappe.flags.get("grc_service_write"):
        sec.deny()


def setup():
    if not ready():
        return
    with sec.service_write():
        from ia_maturity.grc.assessment_types import BUILTIN, _has_type_columns
        for department, values in BUILTIN.items():
            if not frappe.db.exists("GRC Department", department):
                frappe.get_doc({"doctype": "GRC Department", "department_name": department,
                    "report_prefix": values["report_prefix"], "active": 1}).insert(ignore_permissions=True)
            if _has_type_columns():
                # Fill the assessment-type fields once; admin edits to labels are kept.
                current = frappe.db.get_value("GRC Department", department, ["label", "behaviour", "is_system"], as_dict=True)
                if not current.is_system or not current.label:
                    patch = {"is_system": 1, "behaviour": values["behaviour"]}
                    if not current.label:
                        patch.update({key: values[key] for key in ("label", "label_ar", "description", "description_ar",
                            "requires_company_profile", "icon", "sort_order")})
                    frappe.db.set_value("GRC Department", department, patch, update_modified=False)
        frappe.db.add_unique("GRC Department Staff", ["user", "department"])
        frappe.db.add_unique("GRC Department Grant", ["entity", "department"])
        # Infer historical customer grants from their own assessments only. Staff
        # memberships need explicit configuration; role names are not provenance.
        for row in frappe.get_all("IA Maturity Assessment", fields=["name", "entity", "grc_assessment_type", "grc_department"]):
            department = row.grc_assessment_type or "Internal Audit"
            if not row.grc_department:
                frappe.db.set_value("IA Maturity Assessment", row.name, "grc_department", department, update_modified=False)
            if not frappe.db.exists("GRC Department Grant", {"entity": row.entity, "department": department}):
                grant(row.entity, department, "Historical assessment migration")
        for dt in ("GRC Assessment Assignment", "GRC Activity", "GRC Follow Up", "GRC Report Release", "GRC Reminder Delivery", "IA Audit Issue"):
            for row in frappe.get_all(dt, filters={"grc_department": ["is", "not set"]}, fields=["*"]):
                department = kind(row)
                if department:
                    frappe.db.set_value(dt, row.name, "grc_department", department, update_modified=False)
