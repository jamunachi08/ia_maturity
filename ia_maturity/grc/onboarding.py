"""Recipient-bound onboarding, original-auditor attribution and private progress tracking."""
import secrets
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, escape_html, get_datetime, get_url, now_datetime
from ia_maturity.grc import security as sec
from ia_maturity.grc.auth import digest, limit

DOCTYPE = "GRC Onboarding Invitation"
TERMINAL = {"Completed", "Revoked"}
INVITATION_KIND = "Auditor Customer Invitation"
ACTIVATION_KIND = "Invited Customer Onboarding"


@contextmanager
def writing():
    old = frappe.flags.get("grc_onboarding_write")
    frappe.flags.grc_onboarding_write = True
    try:
        with sec.service_write():
            yield
    finally:
        frappe.flags.grc_onboarding_write = old


def guard(doc, method=None):
    if not sec.enabled() or frappe.flags.get("in_migrate") or frappe.flags.get("in_install"):
        return
    if not frappe.flags.get("grc_onboarding_write"):
        sec.deny()
    # The unique key closes the gap between releasing the cache lock and HTTP commit.
    doc.pending_email = doc.email if doc.status not in TERMINAL else None
    before = doc.get_doc_before_save()
    if before and any(before.get(k) != doc.get(k) for k in ("email", "invited_by", "auto_lock", "company", "assessment_type", "minimum_sections")):
        frappe.throw(_("The invitation recipient, origin and locking policy cannot change."))


def can_invite(user=None):
    from ia_maturity.grc.departments import staff_types
    return sec.is_admin(user) or (sec.account_type(user) == "Auditor" and bool(
        staff_types(user)))


def require_staff(doc=None):
    sec.require_login()
    if not can_invite() or (doc and not sec.is_admin() and doc.invited_by != frappe.session.user):
        sec.deny()
    if doc and doc.entity and not sec.can_access(doc.entity):
        sec.deny()
    if doc and doc.assessment_type:
        from ia_maturity.grc.departments import staff_types
        if doc.assessment_type not in staff_types():
            sec.deny()


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    from ia_maturity.grc.departments import staff_types
    return bool(ptype in sec.READ and (sec.is_admin(user) or can_invite(user) and doc.invited_by == user
        and doc.assessment_type in staff_types(user) and (not doc.entity or sec.can_access(doc.entity, user))))


def query_condition(user=None):
    user = user or frappe.session.user
    if sec.is_admin(user):
        return ""
    if not can_invite(user):
        return "1=0"
    allowed = ",".join(frappe.db.escape(e) for e in sec.entities(user)) or "''"
    from ia_maturity.grc.departments import staff_types
    types = ",".join(frappe.db.escape(d) for d in staff_types(user)) or "NULL"
    return "invited_by=" + frappe.db.escape(user) + f" and assessment_type in ({types}) and (coalesce(entity,'')='' or entity in ({allowed}))"


def owner_alert_count():
    from ia_maturity.grc.departments import staff_types
    filters = {"unread_owner_event": 1}
    if not sec.is_admin():
        filters["invited_by"] = frappe.session.user
        filters["assessment_type"] = ["in", list(staff_types()) or ["__none__"]]
    return sum(1 for row in frappe.get_all(DOCTYPE, filters=filters, fields=["entity"])
        if not row.entity or sec.can_access(row.entity))


def locked(name):
    # A locking read is also required when loading the record: an earlier
    # non-locking read may have established a repeatable-read snapshot.
    return frappe.get_doc(DOCTYPE, name, for_update=True)


def active(doc):
    if doc.status in TERMINAL or doc.status == "Pending Invitation Approval" or not doc.expires_on or get_datetime(doc.expires_on) < now_datetime():
        frappe.throw(_("This invitation is unavailable or expired. Ask the inviting auditor to resend it."))
    if not frappe.db.get_value("User", doc.invited_by, "enabled") or not can_invite(doc.invited_by):
        frappe.throw(_("The inviting auditor is inactive. A GRC administrator must resolve this invitation."))
    from ia_maturity.grc.departments import staff_types
    if doc.assessment_type and doc.assessment_type not in staff_types(doc.invited_by):
        frappe.throw(_("The inviting team access has been revoked. Ask a department manager to reissue the invitation."))


def event(doc, action, blocker=None, progress=True, notify=False):
    events = frappe.parse_json(doc.events or "[]")
    events.append({"action": action, "at": str(now_datetime()), "actor": frappe.session.user})
    doc.events = frappe.as_json(events)
    if progress:
        doc.last_activity_on = now_datetime()
    if blocker is not None:
        doc.blocker = blocker
    if notify:
        doc.unread_owner_event = 1
    with writing():
        doc.save(ignore_permissions=True)
    if notify:
        frappe.publish_realtime("grc_onboarding_changed", {"name": doc.name}, user=doc.invited_by, after_commit=True)


def delivery(doc):
    if not doc.email_queue:
        return doc.delivery_status or "Not Sent"
    status = frappe.db.get_value("Email Queue", doc.email_queue, "status")
    if status == "Sent":
        return "Sent by mail system"
    if status in {"Error", "Expired"}:
        return "Failed"
    return "Queued"


def summary(doc, detail=False):
    expired = doc.status not in TERMINAL | {"Awaiting Approval", "Pending Invitation Approval"} and bool(doc.expires_on and get_datetime(doc.expires_on) < now_datetime())
    mail = delivery(doc)
    status = "Expired" if expired else doc.status
    inactive = not frappe.db.get_value("User", doc.invited_by, "enabled") or not can_invite(doc.invited_by)
    blocker = ("Inviting auditor is inactive" if inactive and doc.status not in TERMINAL else
        "Invitation expired" if expired else "Invitation email failed" if mail == "Failed" and doc.status not in TERMINAL else doc.blocker or "")
    approval = status in {"Pending Invitation Approval", "Awaiting Approval"}
    threshold = cint(frappe.db.get_single_value("GRC Settings", "onboarding_attention_hours")) or 48
    stalled = status not in TERMINAL and not approval and (
        now_datetime() - get_datetime(doc.last_activity_on or doc.creation)).total_seconds() >= threshold * 3600
    next_action = {"Invited": "Customer verifies email", "Started": "Customer verifies email",
        "Email Verified": "Customer submits organization details", "Awaiting Approval": "Administrator reviews onboarding",
        "Pending Invitation Approval": "Administrator approves invitation", "Completed": "Open customer",
        "Revoked": "Invitation revoked", "Expired": "Auditor resends invitation"}.get(status, "")
    if inactive and doc.status not in TERMINAL:
        next_action = "Administrator resolves inactive inviter"
    elif mail == "Failed" and status not in TERMINAL:
        next_action = "Check email delivery and resend"
    result = {k: doc.get(k) for k in ("name", "email", "invited_by", "language", "creation", "last_sent_on", "expires_on",
        "last_activity_on", "started_on", "verified_on", "profile_submitted_on", "completed_on", "entity", "approval_request", "unread_owner_event", "company", "assessment_type", "assessment")}
    result["minimum_sections"] = frappe.parse_json(doc.minimum_sections or "[]")
    result["team_label"] = team_label(doc)
    result.update(status=status, delivery_status=mail, blocker=blocker, needs_attention=bool(stalled or blocker and not approval), next_action=next_action)
    if not blocker:
        result["blocker"] = ("Approval pending" if approval else "Email verification incomplete" if status in {"Invited", "Started"}
            else "Organization details not submitted" if status == "Email Verified" else "")
    result["permitted_actions"] = (["revoke"] if doc.status not in TERMINAL else []) + (
        ["remind", "resend"] if doc.status not in TERMINAL and not approval and not inactive else []) + (
        ["read"] if doc.unread_owner_event else [])
    if detail:
        result["events"] = frappe.parse_json(doc.events or "[]")
    return result


def issue_link(doc, reminder=False):
    from ia_maturity.grc.departments import staff_types
    if doc.assessment_type and doc.assessment_type not in staff_types(doc.invited_by):
        frappe.throw(_("The inviting team access has been revoked. A department manager must reissue this invitation."))
    if doc.status in TERMINAL or doc.status in {"Awaiting Approval", "Pending Invitation Approval"}:
        frappe.throw(_("This invitation cannot be resent in its current state."))
    if not frappe.db.get_value("User", doc.invited_by, "enabled") or not can_invite(doc.invited_by):
        frappe.throw(_("The inviting auditor is inactive."))
    limit("onboarding-send", doc.name, 1, seconds=60)
    limit("onboarding-recipient", doc.email, 10)
    # Invalidate unsent old links as well as their server-side token.
    if doc.email_queue and frappe.db.get_value("Email Queue", doc.email_queue, "status") in {"Not Sent", "Error", "Partially Sent"}:
        frappe.db.set_value("Email Queue", doc.email_queue, "status", "Expired")
    token = secrets.token_urlsafe(32)
    doc.token_hash = digest(token)
    doc.expires_on = add_to_date(now_datetime(), days=7)
    doc.last_sent_on = now_datetime()
    url = get_url("/onboarding?token=" + token, allow_header_override=False)
    ar = doc.language == "ar"
    title = ("تذكير بإكمال التهيئة" if reminder else "دعوة لتهيئة العميل") if ar else ("Complete your onboarding" if reminder else "Customer onboarding invitation")
    auditor = escape_html(team_label(doc))
    message = (f'<div dir="{"rtl" if ar else "ltr"}"><h2>{title}</h2><p>{auditor}</p>'
        f'<p><a href="{escape_html(url)}">{"التحقق والمتابعة" if ar else "Verify email and continue"}</a></p>'
        f'<p>{"صالحة لمدة 7 أيام وللبريد المدعو فقط." if ar else "Valid for 7 days and restricted to the invited email address."}</p></div>')
    try:
        queued = frappe.sendmail(recipients=[doc.email], subject="AlphaX | " + title,
            message=message, reference_doctype=DOCTYPE, reference_name=doc.name, delayed=True, now=False)
        queue = frappe.db.get_value("Email Queue", {"reference_doctype": DOCTYPE, "reference_name": doc.name,
            "creation": [">=", doc.last_sent_on]}, "name", order_by="creation desc") if queued else None
        doc.email_queue = queue
        doc.delivery_status = "Queued" if queued and queue else "Failed"
    except (frappe.OutgoingEmailError, frappe.InvalidEmailAddressError):
        doc.email_queue = None
        doc.delivery_status = "Failed"
    failed = doc.delivery_status == "Failed"
    event(doc, "Reminder queued" if reminder and not failed else "Invitation email failed" if failed else "Invitation queued",
        blocker="Invitation email failed" if failed else "", progress=False, notify=failed)


def email_queue_changed(queue, method=None):
    """Record mail-worker failures without interpreting delivery as customer progress."""
    if not sec.enabled() or queue.reference_doctype != DOCTYPE or not queue.reference_name:
        return
    if queue.status not in {"Sent", "Error"} or not frappe.db.exists(DOCTYPE, queue.reference_name):
        return
    doc = locked(queue.reference_name)
    if doc.email_queue != queue.name or doc.status in TERMINAL:
        return
    status = "Sent by mail system" if queue.status == "Sent" else "Failed"
    if doc.delivery_status == status:
        return
    doc.delivery_status = status
    event(doc, "Invitation email failed" if status == "Failed" else status, progress=False,
        blocker="Invitation email failed" if status == "Failed" else "" if doc.blocker == "Invitation email failed" else doc.blocker,
        notify=status == "Failed")


@frappe.whitelist(methods=["POST"])
def create_onboarding_invitation(email, language="en", company=None, assessment_type=None, minimum_sections=None):
    require_staff()
    from ia_maturity.grc import departments as dept
    from ia_maturity.grc.organizations import validate_signup_organization
    company = validate_signup_organization(company)["entity_name"]
    assessment_type = dept.validate_type(assessment_type)
    if assessment_type not in dept.staff_types():
        sec.deny()
    minimum_sections = frappe.parse_json(minimum_sections or "[]")
    if not isinstance(minimum_sections, list) or any(s not in {"Awareness", "Risk", "Compliance", "Governance"} for s in minimum_sections):
        frappe.throw(_("Choose valid GRC sections."))
    # Invited minimum sections are the built-in GRC questionnaire's sections; other types have none.
    if assessment_type != "GRC" and minimum_sections:
        frappe.throw(_("This assessment type does not have a section choice."))
    if assessment_type == "GRC":
        minimum_sections = list(dict.fromkeys(["Awareness"] + minimum_sections))
    from ia_maturity.grc.email_policy import check_email
    from ia_maturity.grc import operations
    email = check_email(email, new_account=not frappe.db.exists("User", email))
    if frappe.db.exists("User", email) and sec.account_type(email) != "Customer":
        frappe.throw(_("Use a customer email address."))
    pending = dept.invitation_precheck(email, assessment_type, company)
    if pending:
        return pending
    limit("onboarding-create", frappe.session.user, 20)
    with frappe.cache.lock("grc:onboarding:" + frappe.local.site + ":" + digest(email), timeout=15):
        existing = frappe.db.exists(DOCTYPE, {"email": email, "status": ["not in", list(TERMINAL)]})
        if existing:
            frappe.throw(_("An onboarding request already exists for this email. Ask a GRC administrator to resolve it."))
        with writing():
            doc = frappe.get_doc({"doctype": DOCTYPE, "email": email, "invited_by": frappe.session.user,
                "company": company, "assessment_type": assessment_type, "minimum_sections": frappe.as_json(minimum_sections),
                "language": "ar" if language == "ar" else "en", "status": "Invited",
                "auto_lock": cint(frappe.db.get_single_value("GRC Settings", "onboarding_auto_lock")),
                "last_activity_on": now_datetime(), "events": "[]"}).insert(ignore_permissions=True)
        queued = operations.maybe_queue(INVITATION_KIND, {"invitation": doc.name})
        if queued:
            doc.status, doc.approval_request = "Pending Invitation Approval", queued["name"]
            event(doc, "Invitation approval requested")
        else:
            issue_link(doc)
    return summary(doc)


@frappe.whitelist()
def onboarding_invitations(search=None, status=None):
    require_staff()
    filters = {} if sec.is_admin() else {"invited_by": frappe.session.user}
    if not sec.is_admin():
        from ia_maturity.grc.departments import staff_types
        filters["assessment_type"] = ["in", list(staff_types()) or ["__none__"]]
    rows = [summary(frappe._dict(row)) for row in frappe.get_all(DOCTYPE, filters=filters, fields=["*"], order_by="creation desc")
        if not row.entity or sec.can_access(row.entity)]
    if search:
        term = str(search).casefold()
        rows = [r for r in rows if term in (r["email"] + " " + r["name"] + " " + (r["entity"] or "")).casefold()]
    if status == "Needs attention":
        rows = [r for r in rows if r["needs_attention"]]
    elif status == "Active":
        rows = [r for r in rows if r["status"] not in TERMINAL | {"Expired"}]
    elif status == "Awaiting customer":
        rows = [r for r in rows if r["status"] in {"Invited", "Started", "Email Verified"}]
    elif status:
        rows = [r for r in rows if r["status"] == status]
    return rows


@frappe.whitelist()
def onboarding_detail(name):
    doc = frappe.get_doc(DOCTYPE, name)
    require_staff(doc)
    return summary(doc, detail=True)


@frappe.whitelist(methods=["POST"])
def onboarding_invitation_action(name, action, reason=None):
    doc = locked(name)
    require_staff(doc)
    if action in {"resend", "remind"}:
        issue_link(doc, action == "remind")
    elif action == "revoke":
        if doc.status in TERMINAL:
            frappe.throw(_("This invitation is already closed."))
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            frappe.throw(_("Enter a reason to revoke the invitation."))
        doc.status, doc.token_hash = "Revoked", ""
        event(doc, "Invitation revoked", blocker="", progress=False)
        sec.log("Onboarding invitation revoked", details={"invitation": name, "reason": reason})
    elif action == "read":
        doc.unread_owner_event = 0
        with writing():
            doc.save(ignore_permissions=True)
    else:
        sec.deny()
    return summary(doc, detail=True)


def from_token(token):
    if not sec.enabled() or not isinstance(token, str) or not 20 <= len(token) <= 128:
        sec.deny()
    name = frappe.db.get_value(DOCTYPE, {"token_hash": digest(token)}, "name")
    if not name:
        frappe.throw(_("This invitation link is invalid or has been replaced."))
    doc = locked(name)
    if not secrets.compare_digest(doc.token_hash or "", digest(token)):
        frappe.throw(_("This invitation link is invalid or has been replaced."))
    active(doc)
    return doc


@frappe.whitelist(allow_guest=True)
def onboarding_link(token):
    """Read only: visiting a link never verifies, starts or consumes an invitation."""
    limit("onboarding-link", getattr(frappe.local, "request_ip", None) or "local", 100)
    doc = from_token(token)
    from ia_maturity.grc.identity import display_name
    return {"email": doc.email, "language": doc.language, "auditor": display_name(doc.invited_by), "expires_on": doc.expires_on,
        "company": doc.company, "assessment_type": doc.assessment_type, "minimum_sections": frappe.parse_json(doc.minimum_sections or "[]"), "team_label": team_label(doc)}


def team_label(doc):
    if doc.assessment_type == "Internal Audit":
        return "بدعوة من فريق التدقيق الداخلي" if doc.language == "ar" else "Invited by the Internal Audit team"
    if doc.assessment_type == "GRC":
        return "بدعوة من فريق الحوكمة والمخاطر والالتزام" if doc.language == "ar" else "Invited by the GRC team"
    from ia_maturity.grc.assessment_types import label
    name = label(doc.assessment_type, doc.language)
    return ("بدعوة من فريق " + name) if doc.language == "ar" else ("Invited by the " + name + " team")


def registration_invitation(email, token=None, name=None):
    if token:
        doc = from_token(token)
    elif name:
        sec.require_login()
        if sec.account_type() != "Customer" or email != frappe.session.user:
            sec.deny()
        doc = locked(name)
        active(doc)
    else:
        # Resolve privately by recipient; a guessed email cannot consume an
        # invitation or create a membership before verification.
        name = frappe.db.get_value(DOCTYPE, {"email": email, "status": ["in", ["Invited", "Started", "Email Verified"]],
            "expires_on": [">", now_datetime()]}, "name", order_by="creation desc")
        if not name:
            return None
        doc = locked(name)
        from ia_maturity.grc.departments import staff_types
        if doc.assessment_type not in staff_types(doc.invited_by):
            return None
    if doc.email != email:
        sec.deny()
    return doc


def registration_started(doc, registration):
    if not doc:
        return
    frappe.db.set_value("IA Maturity Registration", registration.name, "grc_onboarding_invitation", doc.name)
    if not doc.started_on:
        doc.started_on = now_datetime()
    if doc.status == "Invited":
        doc.status = "Started"
    event(doc, "Customer requested verification", blocker="")


def verified(reg, user):
    if not reg.get("grc_onboarding_invitation"):
        return
    doc = locked(reg.grc_onboarding_invitation)
    active(doc)
    if doc.email != user:
        sec.deny()
    doc.customer = user
    doc.verified_on = doc.verified_on or now_datetime()
    if doc.status != "Awaiting Approval":
        doc.status = "Email Verified"
    event(doc, "Customer email verified", blocker="")


@frappe.whitelist()
def customer_onboarding():
    sec.require_login()
    if sec.account_type() != "Customer":
        sec.deny()
    rows = frappe.get_all(DOCTYPE, filters={"email": frappe.session.user, "status": ["not in", ["Revoked", "Pending Invitation Approval"]]}, fields=["*"], order_by="creation desc")
    return [{k: v for k, v in summary(frappe._dict(row)).items() if k in {
        "name", "email", "status", "expires_on", "entity", "blocker", "next_action", "company", "assessment_type", "minimum_sections", "team_label", "assessment"}} for row in rows]


@frappe.whitelist(methods=["POST"])
def resume_onboarding(name):
    sec.require_login()
    doc = locked(name)
    if sec.account_type() != "Customer" or doc.email != frappe.session.user:
        sec.deny()
    active(doc)
    if not cint(frappe.db.get_value("User", frappe.session.user, "grc_email_verified")):
        return {"verification_required": True}
    doc.customer = frappe.session.user
    doc.started_on = doc.started_on or now_datetime()
    doc.verified_on = doc.verified_on or now_datetime()
    if doc.status != "Awaiting Approval":
        doc.status = "Email Verified"
    event(doc, "Customer resumed onboarding", blocker="")
    return {"name": name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def complete_onboarding(name, organization_name=None, sector=None):
    sec.require_login()
    doc = locked(name)
    if sec.account_type() != "Customer" or doc.email != frappe.session.user:
        sec.deny()
    if doc.status == "Completed":
        return {"entity": doc.entity, "status": doc.status, "assessment": doc.assessment}
    active(doc)
    if doc.customer != frappe.session.user or not doc.verified_on:
        frappe.throw(_("Verify your email and resume this invitation first."))
    if doc.status == "Awaiting Approval":
        return {"status": doc.status}
    from ia_maturity.grc.organizations import validate_signup_organization
    from ia_maturity.grc import operations
    try:
        data = validate_signup_organization(doc.company or organization_name, sector)
    except frappe.ValidationError:
        event(doc, "Organization details need correction", blocker="Required organization details are missing or invalid", notify=True)
        # Return an actionable validation result so progress diagnostics commit without draft profile values.
        return {"status": doc.status, "validation_error": _("Enter an organization name and select a valid sector.")}
    if frappe.db.exists("IA Maturity Entity", data["entity_name"]) and not sec.membership(data["entity_name"]):
        event(doc, "Organization name needs correction", blocker="Organization name cannot be used", notify=True)
        return {"status": doc.status, "validation_error": _("This organization name cannot be used. Contact your GRC administrator.")}
    doc.profile_submitted_on = now_datetime()
    queued = operations.maybe_queue(ACTIVATION_KIND, {"invitation": name, "data": data})
    if queued:
        doc.status, doc.approval_request = "Awaiting Approval", queued["name"]
        event(doc, "Organization details submitted; awaiting approval", blocker="")
        return {"status": doc.status}
    return activate(doc, data)


def activate(doc, data):
    """Caller holds the invitation row lock, including approval execution."""
    from ia_maturity.grc.organizations import validate_signup_organization
    from ia_maturity.grc.ownership import writing as owner_write
    if doc.status == "Completed":
        return {"entity": doc.entity, "status": doc.status, "assessment": doc.assessment}
    # Approval waiting is allowed past link expiry; verified acceptance already happened.
    if doc.status == "Revoked" or not doc.customer or not doc.verified_on:
        sec.deny()
    if not frappe.db.get_value("User", doc.invited_by, "enabled") or not can_invite(doc.invited_by):
        frappe.throw(_("The inviting auditor is inactive. Resolve the invitation before approval."))
    from ia_maturity.grc.departments import staff_types
    if doc.assessment_type and doc.assessment_type not in staff_types(doc.invited_by):
        sec.deny()
    if sec.account_type(doc.customer) != "Customer" or not frappe.db.get_value("User", doc.customer, "enabled"):
        sec.deny()
    data = validate_signup_organization(doc.company or data["entity_name"], data.get("sector"))
    from ia_maturity.grc import departments as dept
    with frappe.cache.lock("grc:signup-organization:" + digest(data["entity_name"].casefold()), timeout=15), owner_write():
        if frappe.db.exists("IA Maturity Entity", data["entity_name"]):
            entity = frappe.get_doc("IA Maturity Entity", data["entity_name"], for_update=True)
            if not sec.membership(entity.name, doc.customer):
                sec.deny()
            if doc.assessment_type not in dept.entity_types(entity.name):
                frappe.throw(_("A department manager must approve a second audit type."))
        else:
            entity = frappe.get_doc({"doctype": "IA Maturity Entity", **data, "contact_email": doc.email,
                "owner": doc.customer, "grc_auditor_owner": doc.invited_by,
                "grc_ownership_locked": doc.auto_lock, "grc_onboarding_invitation": doc.name}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype": "GRC Organization Membership", "entity": entity.name,
                "user": doc.customer, "membership_role": "Organization Admin", "active": 1}).insert(ignore_permissions=True)
            dept.grant(entity.name, doc.assessment_type, doc.name)
        if not frappe.db.exists("Auditor Customer Assignment", {"entity": entity.name, "auditor": doc.invited_by, "responsibility": "Consultant"}):
            frappe.get_doc({"doctype": "Auditor Customer Assignment", "entity": entity.name,
                "auditor": doc.invited_by, "responsibility": "Consultant", "active": 1}).insert(ignore_permissions=True)
        from ia_maturity.grc.assessments import new_assessment
        assessment = new_assessment(entity.name, respondent=doc.customer, assessment_type=doc.assessment_type, invitation=doc)
        doc.assessment = assessment.name
        doc.entity, doc.status, doc.token_hash = entity.name, "Completed", ""
        doc.completed_on = now_datetime()
        event(doc, "Onboarding completed", blocker="", notify=True)
        sec.log("Invited customer activated", entity.name, details={"invitation": doc.name, "invited_by": doc.invited_by,
            "customer": doc.customer, "locked": doc.auto_lock}, internal=True)
    return {"entity": entity.name, "status": doc.status, "assessment": doc.assessment}


def apply_approval(request):
    payload = frappe.parse_json(request.payload)
    doc = locked(payload["invitation"])
    if request.kind == INVITATION_KIND:
        if doc.status != "Pending Invitation Approval":
            frappe.throw(_("The invitation is no longer awaiting approval."))
        doc.status = "Invited"
        issue_link(doc)
        return {"invitation": doc.name}
    return activate(doc, payload["data"])


def approval_rejected(request):
    if request.kind not in {INVITATION_KIND, ACTIVATION_KIND}:
        return
    doc = locked(frappe.parse_json(request.payload)["invitation"])
    if doc.status in TERMINAL:
        return
    if request.kind == INVITATION_KIND:
        doc.status, doc.token_hash = "Revoked", ""
    else:
        doc.status = "Email Verified"
    event(doc, "Approval rejected or cancelled", blocker="Administrator rejected or cancelled the request", notify=True)
