"""Explicit GRC API surface. Every record operation enforces membership/assignment."""
# Whitelisted endpoints are re-exported here so the portal can call ia_maturity.grc.api.<method>.
# Those imports are intentional (see [tool.ruff.lint.per-file-ignores] in pyproject.toml); do not auto-remove them.
from pathlib import Path
import hashlib
import frappe
from frappe import _
from frappe.utils import cint, getdate, today
from ia_maturity.compat import desk_base
from ia_maturity.grc.assessment_types import assessment_types_admin, save_assessment_type
from ia_maturity.grc.themes import themes, save_theme, set_default_theme, delete_theme
from ia_maturity.grc.screen_layouts import (screen_layouts, save_screen_layout, set_default_screen_layout,
    delete_screen_layout, find_report, saved_assessments)
from ia_maturity.grc.report_access import report_access_settings, save_report_access, report_view, report_list
from ia_maturity.grc.site_content import site_content_state, site_content_configure, site_content_save, site_content_submit, site_content_decide, site_content_revision, site_content_discard, site_content_cancel
from ia_maturity.grc.operations import operations_onboard_auditor, operations_overview, operations_detail, operations_configure, operations_decide
from ia_maturity.grc.preferences import save_notification_preferences
from ia_maturity.grc.profile import (profile, save_profile, change_password,
    workspace_preferences, save_workspace_preferences)
from ia_maturity.grc.organization_profile import (organization_profile, profile_catalog, save_organization_profile)
from ia_maturity.grc.mfa import begin_authenticator, confirm_authenticator
from ia_maturity.grc.mfa_policy import security_mfa_settings, save_mfa_settings, set_optional_mfa
from ia_maturity.grc.email_health import email_diagnostics
from ia_maturity.grc.verification_limits import verification_limit_status, clear_verification_limits, verification_limit_policy, set_verification_limit_policy
from ia_maturity.grc.report_delivery import email_report
from ia_maturity.grc.account_security import security_accounts, set_mfa_policy, security_role_policies, set_role_mfa_policy
from ia_maturity.grc.identity import display_name
from ia_maturity.grc.maturity_visibility import maturity_display_settings, save_maturity_display
from ia_maturity.grc.color_policy import color_ranges, save_color_ranges
from ia_maturity.grc.onboarding import (create_onboarding_invitation, onboarding_invitations, onboarding_detail, onboarding_invitation_action, onboarding_link, customer_onboarding, resume_onboarding, complete_onboarding)
from ia_maturity.grc.ownership import (ownership_settings, save_ownership_settings, customer_ownership, set_customer_ownership)
from ia_maturity.grc.assessment_types import set_template_type
from ia_maturity.grc.scope import scope_configurations, save_scope_configuration, publish_scope_configuration, confirm_assessment_scope, correct_assessment_scope
from ia_maturity.grc import security as sec
from ia_maturity.grc import assessments as service
from ia_maturity.grc import departments as dept
from ia_maturity.grc.read_cache import read_request
from ia_maturity.grc.departments import (department_staff, save_department_staff, audit_type_requests, request_audit_type, decide_audit_type_request)
from ia_maturity.grc.organizations import (organizations, organization_detail, save_organization,
    save_unit, invite_member, accept_invitation, update_membership, revoke_invitation, signup_organization)
from ia_maturity.grc.administration import (staff, save_staff, assign_customer, assign_assessment,
    templates, save_template, publish_template, settings, save_settings, consultations, update_consultation)


@frappe.whitelist(allow_guest=True)
@read_request
def bootstrap():
    if not sec.enabled():
        return {"enabled": False, "kind": "ERP", "home": desk_base()}
    user = frappe.session.user
    from ia_maturity.grc.themes import tokens as theme_tokens
    if user == "Guest":
        return {"enabled": True, "kind": "Guest", "home": "/login", "theme": theme_tokens()}
    kind = sec.account_type()
    if kind == "ERP":
        return {"enabled": True, "kind": "ERP", "home": sec.home()}
    orgs = organizations()
    allowed_entities = sec.entities()
    user_settings = frappe.db.get_value("User", user,
        ["grc_email_notifications", "grc_optional_reminders", "grc_optional_status_updates",
         "grc_hide_page_tour", "grc_hide_help", "language"], as_dict=True)
    assignments = frappe.get_all("Auditor Customer Assignment",
        filters={"auditor": user, "active": 1, "entity": ["in", allowed_entities or ["__none__"]]}, fields=["name", "entity", "responsibility", "modified"]) if kind == "Auditor" else []
    memberships = frappe.get_all("GRC Organization Membership",
        filters={"user": user, "active": 1}, fields=["name", "entity", "membership_role", "modified"]) if kind == "Customer" else []
    from ia_maturity.grc.onboarding import can_invite, owner_alert_count
    from ia_maturity.grc.scope import can_configure
    pending_invites = frappe.db.count("GRC Onboarding Invitation", {"email": user, "status": ["not in", ["Completed", "Revoked", "Pending Invitation Approval"]]}) if kind == "Customer" else 0
    onboarding_alerts = owner_alert_count() if kind == "Auditor" else 0
    department_access = dept.bootstrap_access()
    managed_entities = [e for e in allowed_entities if sec.can_manage_entity(e)]
    can_operations = (sec.is_admin() or any(sec.is_organization_manager(e) for e in allowed_entities)
        or kind == "Auditor" and any(dept.manager(d) for d in dept.types()))
    from ia_maturity.grc.assessment_types import public_types
    from ia_maturity.grc.report_access import can_view_reports
    # Presentation data stays outside access_version: a theme change must not look like an access change.
    presentation = {"theme": theme_tokens(), "assessment_types": public_types(), "can_view_reports": can_view_reports()}
    return {**presentation, **department_access, "can_invite_customers": can_invite(), "can_configure_scope": can_configure(), "onboarding_alerts": onboarding_alerts, "pending_auditor_invitations": pending_invites, "enabled": True, "user": user, "full_name": display_name(user),
        "kind": kind, "is_admin": sec.is_admin(), "can_operations":can_operations, "managed_entities":managed_entities, "pending_onboarding":__import__("ia_maturity.grc.operations",fromlist=["pending_onboarding"]).pending_onboarding(), "can_site_content": __import__("ia_maturity.grc.site_content", fromlist=["can_access"]).can_access(), "staff_roles": sorted(sec.roles() & sec.AUDITOR_ROLES), "home": sec.home(), "organizations": orgs,
        "memberships": memberships, "assignments": assignments, "signup_organization": signup_organization(),
        "access_version": hashlib.sha256(frappe.as_json([orgs, assignments, memberships, department_access, frappe.db.get_single_value("GRC Settings", "results_visibility"), frappe.db.get_single_value("GRC Settings", "profile_editable_fields")]).encode()).hexdigest(),
        "workspace_preferences": workspace_preferences(user_settings),
        "email_notifications": user_settings.grc_email_notifications,
        "optional_reminders": user_settings.grc_optional_reminders,
        "optional_status_updates": user_settings.grc_optional_status_updates,
        "language": user_settings.language or "en"}


def assignment_filters(entity=None):
    sec.require_login()
    allowed = sec.entities()
    if entity:
        sec.require_entity(entity)
        allowed = [entity]
    filters = {"entity": ["in", allowed or ["__no_organization__"]]}
    if sec.account_type() == "Customer":
        # Contributors see only their own assigned questionnaires; admins/viewers see their organization.
        broad = [e for e in allowed if sec.effective_membership(e) in {"Organization Admin", "Viewer", "Holding Viewer"}]
        if not broad:
            filters["respondent"] = frappe.session.user
    return filters


@frappe.whitelist()
def dashboard(entity=None, search=None, state=None, page=1, scorecards=0, group=None):
    from ia_maturity.grc.dashboard import dashboard as read_dashboard
    return read_dashboard(entity, search, state, page, scorecards, group)


@frappe.whitelist(methods=["POST"])
def start_assessment(entity, template=None, respondent=None, due_date=None, assessment_type=None):
    return service.payload(service.new_assessment(entity, template, respondent, due_date, assessment_type))


@frappe.whitelist()
def assessment(name):
    return service.payload(frappe.get_doc(service.DOCTYPE, name))


@frappe.whitelist(methods=["POST"])
def save_assessment(name, answers, modified=None, language=None):
    return service.save(name, answers, modified, language)


@frappe.whitelist(methods=["POST"])
def submit_assessment(name):
    return service.submit(name)


@frappe.whitelist(methods=["POST"])
def transition(name, action, comment=None):
    return service.transition(name, action, comment)


@frappe.whitelist(methods=["POST"])
def upload_evidence(name, doctype="IA Maturity Assessment"):
    if doctype not in {"IA Maturity Assessment", "IA Maturity Action"}:
        sec.deny()
    doc = frappe.get_doc(doctype, name)
    if doctype == service.DOCTYPE:
        sec.require_assessment(doc, write=True)
        service.get_assignment(doc)
        from ia_maturity.grc.scope import require_ready, answers
        require_ready(doc)
        from ia_maturity.grc.response_policy import flags_for_answer
        if not any(flags_for_answer(row)["allow_attachment"] for row in answers(doc)):
            frappe.throw(_("Question attachments are disabled."), frappe.PermissionError)
    else:
        require_action(doc, write=True)
    upload = frappe.request.files.get("file")
    if not upload:
        frappe.throw(_("Select a file."))
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".docx", ".xlsx", ".pptx"}:
        frappe.throw(_("Use a PDF, image, text, CSV, or Office document."))
    content = upload.stream.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        frappe.throw(_("Files must be 10 MB or smaller."))
    from frappe.utils.file_manager import save_file
    with sec.service_write():
        file = save_file(Path(upload.filename).name, content, doctype, name, is_private=1)
    assessment_name = name if doctype == service.DOCTYPE else doc.assessment
    assignment = frappe.db.get_value(service.DOCTYPE, assessment_name, "grc_assignment")
    sec.log("Evidence uploaded", doc.entity, assignment, assessment_name,
        details={"file": file.name, "filename": file.file_name}, internal=False)
    return {"file_url": file.file_url, "file_name": file.file_name}


@frappe.whitelist(methods=["POST"])
def delete_evidence(name, file_url, doctype="IA Maturity Assessment"):
    if doctype not in {service.DOCTYPE, "IA Maturity Action"}:
        sec.deny()
    doc = frappe.get_doc(doctype, name)
    if doctype == service.DOCTYPE:
        sec.require_assessment(doc, write=True)
        service.lock_assignment(doc.grc_assignment)
        doc.reload()
        sec.require_assessment(doc, write=True)
        service.get_assignment(doc)
        from ia_maturity.grc.scope import require_ready, answers
        require_ready(doc)
        from ia_maturity.grc.response_policy import flags_for_answer
        if not any(flags_for_answer(row)["allow_attachment"] for row in answers(doc)):
            frappe.throw(_("Question attachments are disabled."), frappe.PermissionError)
        if any(r.evidence == file_url and r not in answers(doc) for r in doc.answers):
            frappe.throw(_("Historical evidence must be retained. You can attach a replacement."))
    else:
        require_action(doc, write=True)
        if doc.status in {"Completed", "Cancelled"}:
            frappe.throw(_("Completed or superseded evidence must be retained."))
    sec.check_file_url(file_url)
    files = frappe.get_all("File", filters={"file_url": file_url, "is_private": 1,
        "attached_to_doctype": doctype, "attached_to_name": name}, fields=["name", "file_name"])
    if not files:
        sec.deny()
    referenced = frappe.db.exists("IA Maturity Assessment Answer", {
        "parent": ["!=", name], "evidence": file_url})
    if referenced or frappe.db.exists("IA Maturity Action", {"name": ["!=", name], "evidence": file_url}):
        frappe.throw(_("Historical evidence must be retained. You can attach a replacement."))
    if doctype == service.DOCTYPE:
        changes = {r.question_code: {"evidence": ""} for r in doc.answers if r.evidence == file_url}
        if changes:
            service.save(name, changes, modified=str(doc.modified))
    elif doc.evidence == file_url:
        with sec.service_write():
            doc.evidence = ""
            doc.save(ignore_permissions=True)
    with sec.service_write():
        for file in files:
            frappe.delete_doc("File", file.name, ignore_permissions=True)
    return {"deleted": True}


@frappe.whitelist()
def download_report(name, inline=0):
    from ia_maturity.grc.reports import content
    frappe.local.response.filecontent = content(name)
    kind = frappe.db.get_value("IA Maturity Assessment", name, "grc_assessment_type") or "Internal Audit"
    from ia_maturity.grc.assessment_types import report_prefix
    prefix = report_prefix(kind)
    frappe.local.response.filename = f"{prefix}-{name}.pdf"
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "application/pdf"
    frappe.local.response.display_content_as = "inline" if str(inline) == "1" else "attachment"


def require_action(doc, write=False):
    sec.require_entity(doc.entity)
    if not sec.can_read_action(doc):
        sec.deny()
    if sec.account_type() == "Customer":
        if write and not (sec.membership(doc.entity) == "Organization Admin" or
            (sec.membership(doc.entity) == "Contributor" and doc.assigned_to == frappe.session.user)):
            sec.deny()
    elif write and not (sec.is_admin() or sec.responsibilities(doc.entity)):
        sec.deny()


@frappe.whitelist()
def actions(entity=None, search=None, page=1):
    scope = assignment_filters(entity)["entity"]
    rows = frappe.get_all("IA Maturity Action", filters={"entity": scope, "status": ["!=", "Cancelled"]},
        fields=["name", "entity", "assessment", "finding_title", "priority", "status",
            "assigned_to", "due_date", "recommended_action", "completion_notes", "evidence", "completed_on"],
        order_by="due_date asc")
    visible = []
    for row in rows:
        if sec.can_read_action(row):
            if not search or search.lower() in (row.finding_title or "").lower():
                member = sec.membership(row.entity)
                row.can_edit = sec.is_admin() or sec.account_type() == "Auditor" or member == "Organization Admin" or (member == "Contributor" and row.assigned_to == frappe.session.user)
                row.can_assign = sec.is_admin() or sec.account_type() == "Auditor" or member == "Organization Admin"
                row.can_verify = sec.is_admin() or "Reviewer" in sec.responsibilities(row.entity)
                visible.append(row)
    page = max(1, cint(page))
    return {"items": visible[(page-1)*15:page*15], "total": len(visible), "page": page}


@frappe.whitelist(methods=["POST"])
def update_action(name, status, assigned_to=None, due_date=None, completion_notes="", evidence=None):
    doc = frappe.get_doc("IA Maturity Action", name)
    require_action(doc, write=True)
    if status not in {"Open", "In Progress", "Pending Verification", "Completed"}:
        sec.deny()
    if doc.status == "Cancelled":
        frappe.throw(_("This action belongs to a superseded submission."))
    if status == "Completed" and not (sec.is_admin() or "Reviewer" in sec.responsibilities(doc.entity)):
        frappe.throw(_("A GRC reviewer must verify closure."))
    if assigned_to and assigned_to != doc.assigned_to:
        if sec.membership(doc.entity, assigned_to) not in {"Organization Admin", "Contributor"}:
            sec.deny()
        if not (sec.is_admin() or sec.account_type() == "Auditor" or sec.membership(doc.entity) == "Organization Admin"):
            sec.deny()
        doc.assigned_to = assigned_to
    if due_date and getdate(due_date) != getdate(doc.due_date):
        if not (sec.is_admin() or sec.account_type() == "Auditor" or sec.membership(doc.entity) == "Organization Admin"):
            sec.deny()
        doc.due_date = getdate(due_date)
    if evidence:
        file = frappe.get_doc("File", sec.check_file_url(evidence))
        if file.attached_to_doctype != "IA Maturity Action" or file.attached_to_name != doc.name:
            sec.deny()
        doc.evidence = evidence
    doc.completion_notes = str(completion_notes or "")[:5000]
    if status in {"Pending Verification", "Completed"} and not (doc.completion_notes or doc.evidence):
        frappe.throw(_("Provide completion notes or evidence before requesting closure."))
    doc.status = status
    if status == "Completed":
        doc.completed_on = today()
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Improvement action updated", doc.entity,
        assignment=frappe.db.get_value(service.DOCTYPE, doc.assessment, "grc_assignment"), assessment=doc.assessment,
        details={"action": doc.name, "status": status}, internal=False)
    return {"name": doc.name}


@frappe.whitelist()
def followups(entity=None):
    sec.require_login()
    if not (sec.is_admin() or sec.account_type() == "Auditor"):
        sec.deny()
    scope = assignment_filters(entity)["entity"]
    rows = frappe.get_all("GRC Follow Up", filters={"entity": scope},
        fields=["name", "entity", "note", "assigned_to", "due_date", "status", "creation", "grc_department"], order_by="modified desc", limit_page_length=100)
    visible = [r for r in rows if dept.can_read(r)]
    for row in visible:
        row["can_edit"] = sec.can_manage_entity(row.entity)
    return visible


@frappe.whitelist(methods=["POST"])
def save_followup(entity, note, due_date=None, assigned_to=None, name=None, status="Open"):
    sec.require_entity(entity, manage=True)
    if not (sec.is_admin() or sec.account_type() == "Auditor") or status not in {"Open", "Completed"}:
        sec.deny()
    assigned_to = assigned_to or frappe.session.user
    if not (sec.is_admin(assigned_to) or sec.responsibilities(entity, assigned_to)):
        sec.deny()
    doc = frappe.get_doc("GRC Follow Up", name) if name else frappe.new_doc("GRC Follow Up")
    if name and (doc.entity != entity or not dept.can_read(doc)):
        sec.deny()
    doc.update(dict(entity=entity, note=note[:5000], due_date=getdate(due_date) if due_date else None,
        assigned_to=assigned_to, status=status))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Follow-up recorded", entity, details={"followup": doc.name})
    return {"name": doc.name}


@frappe.whitelist()
def activity(entity=None, assignment=None):
    from ia_maturity.grc.dashboard import activity as read_activity
    return read_activity(entity, assignment)


@frappe.whitelist()
def issues(entity):
    sec.require_entity(entity)
    if not (sec.is_admin() or sec.account_type() == "Auditor" or sec.membership(entity) == "Organization Admin"):
        sec.deny()
    rows = frappe.get_all("IA Audit Issue", filters={"entity": entity},
        fields=["name", "entity", "grc_department", "title", "status", "rating", "raised_on", "due_date", "closed_on", "issue_owner", "description"],
        order_by="modified desc", limit_page_length=100)
    return [r for r in rows if dept.can_read(r)]


@frappe.whitelist(methods=["POST"])
def save_issue(entity, data, name=None):
    sec.require_entity(entity, manage=True)
    if not (sec.is_admin() or sec.account_type() == "Auditor" or sec.membership(entity) == "Organization Admin"):
        sec.deny()
    data = frappe.parse_json(data) or {}
    doc = frappe.get_doc("IA Audit Issue", name) if name else frappe.new_doc("IA Audit Issue")
    if name and (doc.entity != entity or not dept.can_read(doc)):
        sec.deny()
    doc.entity = entity
    for key in ("title", "status", "rating", "raised_on", "due_date", "closed_on", "description", "management_action"):
        if key in data:
            doc.set(key, data[key])
    if data.get("issue_owner"):
        if not sec.membership(entity, data["issue_owner"]):
            sec.deny()
        doc.issue_owner = data["issue_owner"]
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Audit issue updated", entity, details={"issue": doc.name}, internal=False)
    return {"name": doc.name}
