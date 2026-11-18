"""Organization profiles, invitations, and memberships."""
import secrets
import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_url, now_datetime, escape_html
from ia_maturity.grc import security as sec
from ia_maturity.grc.auth import digest
from ia_maturity.grc.email_policy import check_email

MEMBER_ROLES = {"Organization Admin", "Contributor", "Viewer"}


@frappe.whitelist()
def organizations():
    sec.require_login()
    allowed = sec.entities()
    if not allowed:
        return []
    return frappe.get_all("IA Maturity Entity", filters={"name": ["in", allowed]},
        fields=["name", "entity_name", "sector", "contact_email", "is_active", "parent_organization"], order_by="entity_name")


@frappe.whitelist()
def organization_detail(name):
    sec.require_entity(name)
    doc = frappe.get_doc("IA Maturity Entity", name)
    data = {k: doc.get(k) for k in ("name", "entity_name", "sector", "listed_company",
        "contact_email", "regulators", "notes", "is_active", "parent_organization",
        "grc_optional_reminders", "grc_optional_status_updates")}
    data["auditor_owner"] = doc.grc_auditor_owner
    data["ownership_locked"] = bool(doc.grc_ownership_locked)
    data["can_manage"] = sec.can_manage_entity(name)
    data["can_assign_staff"] = sec.is_admin() or sec.is_organization_manager(name)
    data["read_only"] = sec.effective_membership(name) == "Holding Viewer"
    if data["read_only"]:
        data["notes"] = ""
    data["membership_role"] = sec.effective_membership(name)
    data["units"] = [] if data["read_only"] else frappe.get_all("GRC Organization Unit", filters={"entity": name},
        fields=["name", "unit_name", "unit_type", "responsibilities"], order_by="unit_type, unit_name")
    data["members"] = []
    data["auditors"] = []
    data["invitations"] = []
    if data["can_manage"] or sec.account_type() == "Auditor":
        data["members"] = frappe.get_all("GRC Organization Membership", filters={"entity": name},
            fields=["name", "user", "membership_role", "active"])
    if sec.is_admin() or sec.account_type() == "Auditor":
        data["auditors"] = frappe.get_all("Auditor Customer Assignment", filters={"entity": name},
            fields=["name", "auditor", "responsibility", "active"])
    if data["can_manage"]:
        data["invitations"] = frappe.get_all("GRC Invitation", filters={"entity": name},
            fields=["name", "email", "membership_role", "status", "expires_on"])
    from ia_maturity.grc import departments as dept
    data["can_view_company_profile"] = dept.can_profile(name)
    if not data["can_view_company_profile"]:
        data["regulators"] = ""
        data["notes"] = ""
    if sec.account_type() == "Auditor" and not sec.is_admin():
        data["auditors"] = [a for a in data["auditors"] if dept.staff_types(a.auditor) & dept.staff_types()]
        if data["auditor_owner"] and not (dept.staff_types(data["auditor_owner"]) & dept.staff_types()):
            data["auditor_owner"] = None
    return data


@frappe.whitelist(methods=["POST"])
def save_organization(data, name=None):
    sec.require_login()
    data = frappe.parse_json(data) or {}
    if name:
        sec.require_entity(name, manage=True)
        doc = frappe.get_doc("IA Maturity Entity", name)
    else:
        if sec.account_type() == "Customer" and frappe.db.exists("GRC Onboarding Invitation", {"email": frappe.session.user, "status": ["not in", ["Completed", "Revoked", "Pending Invitation Approval"]]}):
            frappe.throw(_("Complete your auditor invitation from Customer onboarding."))
        if sec.account_type() not in {"Customer", "Auditor"} and not sec.is_admin():
            sec.deny()
        if sec.account_type() == "Auditor" and not (sec.is_admin() or sec.roles() & {"GRC Auditor", "GRC Consultant", "GRC Manager", "IA Maturity Manager"}):
            sec.deny()
        title = (data.get("entity_name") or "").strip()[:140]
        if not title or frappe.db.exists("IA Maturity Entity", title):
            frappe.throw(_("This organization name cannot be used. If you are joining an organization, request an invitation."))
        doc = frappe.new_doc("IA Maturity Entity")
        doc.entity_name = title
    for key in ("sector", "contact_email", "regulators", "notes"):
        if key in data:
            doc.set(key, str(data[key] or "")[:5000 if key == "notes" else 500])
    if "listed_company" in data:
        doc.listed_company = cint(data["listed_company"])
    if "parent_organization" in data:
        if not sec.is_admin():
            sec.deny()
        doc.parent_organization = data["parent_organization"] or None
    for key in ("grc_optional_reminders", "grc_optional_status_updates"):
        if key in data:
            doc.set(key, int(bool(cint(data[key]))))
    is_new = doc.is_new()
    if is_new and sec.account_type() == "Auditor" and not sec.is_admin():
        from ia_maturity.grc.departments import staff_types
        if len(staff_types()) != 1:
            frappe.throw(_("Create the customer through a department invitation."))
    if is_new:
        from ia_maturity.grc.operations import maybe_queue
        queued=maybe_queue('Customer Onboarding',{'data':{k:doc.get(k) for k in ('entity_name','sector','contact_email','regulators','notes','listed_company','parent_organization')} })
        if queued:return queued
    with frappe.cache.lock("grc:organization-hierarchy:" + frappe.local.site, timeout=15), sec.service_write():
        doc.save(ignore_permissions=True)
        if is_new and sec.account_type() == "Customer":
            frappe.get_doc(dict(doctype="GRC Organization Membership", entity=doc.name,
                user=frappe.session.user, membership_role="Organization Admin", active=1)).insert(ignore_permissions=True)
        elif is_new and sec.account_type() == "Auditor":
            frappe.get_doc(dict(doctype="Auditor Customer Assignment", entity=doc.name,
                auditor=frappe.session.user, responsibility="Manager" if sec.roles() & {"GRC Manager", "IA Maturity Manager"} else "Consultant", active=1)).insert(ignore_permissions=True)
    if is_new and sec.account_type() == "Auditor" and not sec.is_admin():
        from ia_maturity.grc.departments import grant, staff_types
        grant(doc.name, next(iter(staff_types())), "Staff-created customer")
    from ia_maturity.grc.preferences import cancel_optional
    cancel_optional(entity=doc.name)
    sec.log("Organization created" if is_new else "Organization updated", doc.name, internal=False)
    return organization_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def save_unit(entity, unit_name, unit_type, responsibilities="", name=None):
    sec.require_entity(entity, manage=True)
    if unit_type not in {"Department", "Branch"} or not unit_name.strip():
        frappe.throw(_("Enter a department or branch name."))
    doc = frappe.get_doc("GRC Organization Unit", name) if name else frappe.new_doc("GRC Organization Unit")
    if name and doc.entity != entity:
        sec.deny()
    doc.update(dict(entity=entity, unit_name=unit_name.strip()[:140], unit_type=unit_type,
        responsibilities=str(responsibilities)[:3000]))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Organization unit updated", entity, details={"unit": doc.name}, internal=False)
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def invite_member(entity, email, membership_role="Contributor"):
    sec.require_entity(entity, manage=True)
    if membership_role not in MEMBER_ROLES:
        frappe.throw(_("Invalid membership role."))
    email = check_email(email)
    if frappe.db.exists("User", email) and sec.account_type(email) != "Customer":
        frappe.throw(_("Use a separate customer account for organization membership."))
    from ia_maturity.grc.operations import maybe_queue
    queued=maybe_queue('Customer Invitation',{'entity':entity,'email':email,'membership_role':membership_role},entity)
    if queued:return queued
    token = secrets.token_urlsafe(32)
    with sec.service_write():
        invitation = frappe.get_doc(dict(doctype="GRC Invitation", entity=entity, email=email,
            membership_role=membership_role, token_hash=digest(token),
            invited_by=frappe.session.user, expires_on=add_to_date(now_datetime(), days=7))).insert(ignore_permissions=True)
    url = get_url("/login?invitation=" + token, allow_header_override=False)
    frappe.sendmail(recipients=[email], subject="AlphaX GRC | Organization invitation",
        message=f'<p>You have been invited to an organization in AlphaX GRC.</p>'
                f'<p><a href="{escape_html(url)}">Verify your email and accept / تحقق من بريدك واقبل الدعوة</a></p>'
                '<p>This invitation expires in 7 days and is restricted to your email address.</p>')
    sec.log("Member invited", entity, details={"email": email, "role": membership_role})
    return {"name": invitation.name, "status": invitation.status}


@frappe.whitelist(methods=["POST"])
def accept_invitation(token):
    sec.require_login()
    if sec.account_type() != "Customer" or not token or len(token) > 128:
        sec.deny()
    name = frappe.db.get_value("GRC Invitation", {"token_hash": digest(token)}, "name")
    if not name:
        sec.deny()
    frappe.db.sql("select name from `tabGRC Invitation` where name=%s for update", name)
    invite = frappe.get_doc("GRC Invitation", name)
    if invite.status != "Pending" or invite.expires_on < now_datetime() or invite.email != frappe.session.user:
        frappe.throw(_("This invitation is invalid, expired, or belongs to another email address."))
    member_name = frappe.db.get_value("GRC Organization Membership",
        {"entity": invite.entity, "user": frappe.session.user}, "name")
    with sec.service_write():
        member = frappe.get_doc("GRC Organization Membership", member_name) if member_name else frappe.new_doc("GRC Organization Membership")
        member.update(dict(entity=invite.entity, user=frappe.session.user,
            membership_role=invite.membership_role, active=1))
        member.save(ignore_permissions=True)
        invite.status = "Accepted"
        invite.save(ignore_permissions=True)
    if invite.membership_role == "Organization Admin":
        for row in frappe.get_all("GRC Assessment Assignment", filters={
                "entity": invite.entity, "customer_pending": 1, "workflow_state": ["in", ["Draft", "In Progress"]]},
                fields=["name", "assessment"]):
            frappe.db.sql("select name from `tabGRC Assessment Assignment` where name=%s for update", row.name)
            assignment = frappe.get_doc("GRC Assessment Assignment", row.name)
            if not assignment.customer_pending:
                continue
            before = assignment.respondent
            with sec.service_write():
                assignment.respondent, assignment.customer_pending = frappe.session.user, 0
                assignment.save(ignore_permissions=True)
                frappe.db.set_value("IA Maturity Assessment", row.assessment, {
                    "respondent": frappe.session.user, "respondent_name": "", "respondent_email": ""})
            sec.log("Customer ownership accepted", invite.entity, row.name, row.assessment,
                {"before": before, "after": frappe.session.user, "reason": "Customer administrator accepted invitation"}, internal=True)
    sec.log("Invitation accepted", invite.entity, internal=False)
    return {"entity": invite.entity}


@frappe.whitelist(methods=["POST"])
def revoke_invitation(name):
    doc = frappe.get_doc("GRC Invitation", name)
    sec.require_entity(doc.entity, manage=True)
    with sec.service_write():
        doc.status = "Revoked"
        doc.save(ignore_permissions=True)
    return {"status": doc.status}


@frappe.whitelist(methods=["POST"])
def update_membership(name, membership_role, active=1):
    doc = frappe.get_doc("GRC Organization Membership", name)
    sec.require_entity(doc.entity, manage=True)
    if membership_role not in MEMBER_ROLES:
        sec.deny()
    if doc.membership_role == "Organization Admin" and (membership_role != "Organization Admin" or not cint(active)):
        count = frappe.db.count("GRC Organization Membership",
            {"entity": doc.entity, "membership_role": "Organization Admin", "active": 1, "name": ["!=", doc.name]})
        if not count:
            frappe.throw(_("Keep at least one active organization administrator."))
    from ia_maturity.grc.operations import maybe_queue
    queued=maybe_queue('Customer Membership',{'name':name,'membership_role':membership_role,'active':cint(active),'_before':{'membership_role':doc.membership_role,'active':doc.active}},doc.entity)
    if queued:return queued
    with sec.service_write():
        doc.membership_role, doc.active = membership_role, cint(active)
        doc.save(ignore_permissions=True)
    return {"name": doc.name}


def validate_signup_organization(title, sector=None):
    """Validate public signup input without looking up or disclosing existing tenants."""
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140 or any(ord(c) < 32 for c in title):
        frappe.throw(_("Enter an organization name of up to 140 characters."))
    options = frappe.get_meta("IA Maturity Entity").get_field("sector").options.splitlines()
    if sector not in (None, "") and (not isinstance(sector, str) or sector not in options):
        frappe.throw(_("Choose a valid organization sector."))
    return {"entity_name": title.strip(), "sector": sector or ""}


def create_verified_signup_organization(reg, user):
    """Only called after proof validation and new User creation, in the same transaction."""
    if reg.get("grc_onboarding_invitation") or frappe.db.exists("GRC Onboarding Invitation", {
        "email": user, "status": ["not in", ["Completed", "Revoked"]]}):
        return
    if not reg.get("grc_organization_signup"):
        return  # Pre-upgrade verification links keep the existing onboarding flow.
    data = validate_signup_organization(reg.entity_name, reg.grc_organization_sector)
    if frappe.db.exists("GRC Organization Membership", {"user": user}) or frappe.db.exists(
        "GRC Invitation", {"email": user, "status": "Pending", "expires_on": [">", now_datetime()]}):
        return  # Invitations need explicit acceptance; never create an unrelated tenant.
    from ia_maturity.grc.operations import maybe_queue
    queued=maybe_queue('Customer Onboarding',{'data':{**data,'contact_email':user}},actor=user)
    if queued:return
    with frappe.cache.lock("grc:signup-organization:" + digest(data["entity_name"].casefold()), timeout=15):
        if frappe.db.exists("IA Maturity Entity", data["entity_name"]):
            return  # A matching name is never proof of membership.
        frappe.db.savepoint("grc_signup_organization")
        try:
            with sec.service_write():
                doc = frappe.get_doc(dict(doctype="IA Maturity Entity", **data,
                    contact_email=user, owner=user)).insert(ignore_permissions=True)
                frappe.get_doc(dict(doctype="GRC Organization Membership", entity=doc.name,
                    user=user, owner=user, membership_role="Organization Admin", active=1)).insert(ignore_permissions=True)
                frappe.get_doc(dict(doctype="GRC Activity", entity=doc.name, actor=user,
                    action="Organization created", internal=0,
                    details=frappe.as_json({"source": "Verified signup"}))).insert(ignore_permissions=True)
        except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
            # A concurrent creator may have reserved this name outside this flow.
            frappe.db.rollback(save_point="grc_signup_organization")


def signup_organization():
    """Only the authenticated customer's own verified signup details may be returned."""
    if sec.account_type() != "Customer" or sec.entities():
        return None
    row = frappe.db.get_value("IA Maturity Registration", {
        "email": frappe.session.user, "user": frappe.session.user,
        "status": "Verified", "grc_organization_signup": 1},
        ["entity_name", "grc_organization_sector"], as_dict=True, order_by="creation desc")
    return {"entity_name": row.entity_name, "sector": row.grc_organization_sector} if row else None
