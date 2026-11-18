"""GRC authorization. Client routing is never an authorization boundary."""
from contextlib import contextmanager
from urllib.parse import unquote
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc.schema import CUSTOMER_ROLES, AUDITOR_ROLES, TENANT_DOCTYPES
from ia_maturity.compat import desk_url, is_desk_path, permission_hook_passthrough
from ia_maturity.grc.read_cache import read_cached, invalidate

READ = {"read", "select", "report", "print", "export", None}
API_METHODS = {
    "department_staff", "save_department_staff", "audit_type_requests", "request_audit_type", "decide_audit_type_request",
    "organization_profile", "profile_catalog", "save_organization_profile",
    "create_onboarding_invitation", "onboarding_invitations", "onboarding_detail", "onboarding_invitation_action", "onboarding_link", "customer_onboarding", "resume_onboarding", "complete_onboarding",
    "ownership_settings", "save_ownership_settings", "customer_ownership", "set_customer_ownership",
    "set_template_type", "scope_configurations", "save_scope_configuration", "publish_scope_configuration", "confirm_assessment_scope", "correct_assessment_scope",
    "maturity_display_settings", "save_maturity_display",
    "color_ranges", "save_color_ranges",
    "security_mfa_settings", "save_mfa_settings", "set_optional_mfa", "operations_onboard_auditor", "operations_overview", "operations_detail", "operations_configure", "operations_decide", "site_content_cancel", "site_content_discard", "site_content_state", "site_content_configure", "site_content_save", "site_content_submit", "site_content_decide", "site_content_revision", "begin_authenticator", "confirm_authenticator", "email_diagnostics", "verification_limit_status", "clear_verification_limits", "verification_limit_policy", "set_verification_limit_policy", "security_accounts", "set_mfa_policy", "security_role_policies", "set_role_mfa_policy",
    "bootstrap", "dashboard", "profile", "save_profile", "save_workspace_preferences", "change_password", "save_notification_preferences", "organizations", "organization_detail", "save_organization",
    "save_unit", "invite_member", "accept_invitation", "update_membership", "staff",
    "save_staff", "assign_customer", "assign_assessment", "templates", "save_template",
    "publish_template", "settings", "save_settings", "start_assessment", "assessment",
    "save_assessment", "submit_assessment", "transition", "upload_evidence", "download_report", "email_report",
    "actions", "update_action", "followups", "save_followup", "activity", "consultations",
    "update_consultation", "issues", "save_issue", "revoke_invitation", "delete_evidence",
    # v3.2: assessment types, themes, screen layouts and report access.
    "assessment_types_admin", "save_assessment_type", "themes", "save_theme", "set_default_theme", "delete_theme", "screen_layouts", "save_screen_layout", "set_default_screen_layout", "delete_screen_layout", "find_report", "saved_assessments", "report_access_settings", "save_report_access", "report_view", "report_list",
}
PUBLIC_METHODS = {
    "ia_maturity.grc.api.onboarding_link",
    "ia_maturity.grc.api.bootstrap", "ia_maturity.grc.public.info", "ia_maturity.grc.public.site_content",
    "ia_maturity.grc.public.consultation", "ia_maturity.grc.auth.request_code",
    "ia_maturity.grc.auth.verify_code", "ia_maturity.grc.auth.verify_link", "ia_maturity.grc.auth.reset_password",
}
CORE_AUTH_METHODS = {
    "login", "logout", "web_logout", "frappe.handler.logout", "frappe.handler.web_logout", "frappe.auth.get_logged_user",
    "frappe.core.doctype.user.user.reset_password",
    "frappe.core.doctype.user.user.update_password",
}


def enabled():
    return bool(cint(frappe.conf.get("grc_enabled")))


@read_cached
def roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def is_admin(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or "GRC App Admin" in roles(user)


def account_type(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "Guest"
    # Frappe gives the built-in platform operator every effective role.
    # Those synthetic roles are not GRC membership. Keep core authentication,
    # MFA policy and Desk access; only separately classified staff are portal-only.
    if user == "Administrator":
        return "ERP"
    r = roles(user)
    if r & AUDITOR_ROLES:
        return "Auditor"
    if "GRC Customer" in r:
        return "Customer"
    # Only a real GRC customer role can lock someone out of Desk.
    # IA Assessment Respondent and a stale grc_account_type are not GRC roles.
    if r & (CUSTOMER_ROLES - {"IA Assessment Respondent"}):
        return "Restricted"
    return "ERP"


def require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)
    if account_type() == "Restricted":
        frappe.throw(_("Your GRC role is inactive. Contact your administrator."), frappe.PermissionError)


def require_admin():
    require_login()
    if not is_admin():
        deny()


def deny():
    frappe.throw(_("You do not have access to this record or action."), frappe.PermissionError)


@read_cached
def membership(entity, user=None):
    return frappe.db.get_value("GRC Organization Membership",
        {"entity": entity, "user": user or frappe.session.user, "active": 1}, "membership_role")


@read_cached
def responsibilities(entity, user=None):
    user = user or frappe.session.user
    from ia_maturity.grc import departments as dept
    if not dept.can_access_entity(entity, user):
        return set()
    if any(dept.manager(d, user) for d in dept.entity_types(entity)) and not is_admin(user):
        return {"Manager", "Consultant", "Reviewer"}
    from ia_maturity.grc.ownership import staff_allowed
    if not is_admin(user) and not staff_allowed(entity, user):
        return set()
    return set(frappe.get_all("Auditor Customer Assignment", filters={
        "entity": entity, "auditor": user or frappe.session.user, "active": 1}, pluck="responsibility"))


@read_cached
def inherited_entities(user=None):
    """Descendant reads derive solely from active, direct organization-admin memberships."""
    user = user or frappe.session.user
    if account_type(user) != "Customer":
        return set()
    roots = set(frappe.get_all("GRC Organization Membership", filters={
        "user": user, "active": 1, "membership_role": "Organization Admin"}, pluck="entity"))
    edges = frappe.get_all("IA Maturity Entity", fields=["name", "parent_organization"])
    seen, frontier = set(roots), set(roots)
    while frontier:
        children = {r.name for r in edges if r.parent_organization in frontier} - seen
        seen.update(children)
        frontier = children
    return seen - roots


def effective_membership(entity, user=None):
    direct = membership(entity, user)
    if direct not in {"Organization Admin", "Viewer"} and entity in inherited_entities(user):
        return "Holding Viewer"
    return direct


def is_organization_manager(entity, user=None):
    return account_type(user) == "Auditor" and "Manager" in responsibilities(entity, user)


def can_manage_entity(entity, user=None):
    from ia_maturity.grc.departments import can_profile
    if account_type(user) == "Auditor" and not can_profile(entity, user):
        return False
    return is_admin(user) or is_organization_manager(entity, user) or membership(entity, user) == "Organization Admin" or (
        account_type(user) == "Auditor" and "Consultant" in responsibilities(entity, user))


def can_edit_assessment(doc, user=None):
    user = user or frappe.session.user
    if doc.docstatus != 0 or not can_read_assessment(doc, user):
        return False
    if is_admin(user) or is_organization_manager(doc.entity, user):
        return True
    if account_type(user) == "Auditor":
        a = frappe.db.get_value("GRC Assessment Assignment", doc.grc_assignment,
            ["assessment", "consultant"], as_dict=True)
        return bool(a and a.assessment == doc.name and a.consultant == user
            and "Consultant" in responsibilities(doc.entity, user))
    return membership(doc.entity, user) == "Organization Admin" or (
        membership(doc.entity, user) == "Contributor" and doc.respondent == user)

def can_access(entity, user=None):
    user = user or frappe.session.user
    if not user or user == "Guest" or not entity:
        return False
    if is_admin(user):
        return True
    if account_type(user) == "Auditor":
        return bool(responsibilities(entity, user))
    if account_type(user) == "Customer":
        return bool(effective_membership(entity, user))
    return False


def require_entity(entity, manage=False):
    require_login()
    if not can_access(entity):
        deny()
    if manage and not can_manage_entity(entity):
        deny()


@read_cached
def entities(user=None):
    user = user or frappe.session.user
    if is_admin(user):
        return frappe.get_all("IA Maturity Entity", pluck="name")
    if account_type(user) == "Auditor":
        from ia_maturity.grc import departments as dept
        from ia_maturity.grc.ownership import staff_allowed
        candidates = set(frappe.get_all("Auditor Customer Assignment",
            filters={"auditor": user, "active": 1}, pluck="entity"))
        managed = [d for d in dept.staff_types(user) if dept.manager(d, user)]
        if managed:
            candidates.update(frappe.get_all("GRC Department Grant", filters={"department": ["in", managed], "active": 1}, pluck="entity"))
        return [entity for entity in candidates if dept.can_access_entity(entity, user) and (
            staff_allowed(entity, user) or any(dept.manager(d, user) for d in dept.entity_types(entity)))]
    if account_type(user) == "Customer":
        return sorted(set(frappe.get_all("GRC Organization Membership",
            filters={"user": user, "active": 1}, pluck="entity")) | inherited_entities(user))
    return []


def can_read_assessment(doc, user=None):
    user = user or frappe.session.user
    if not can_access(doc.entity, user):
        return False
    from ia_maturity.grc.departments import can_read
    if not can_read(doc, user):
        return False
    if is_admin(user) or account_type(user) == "Auditor":
        return True
    member = effective_membership(doc.entity, user)
    if member in {"Organization Admin", "Viewer", "Holding Viewer"}:
        return True
    return doc.respondent == user


def can_read_action(doc, user=None):
    user = user or frappe.session.user
    if not can_access(doc.entity, user):
        return False
    from ia_maturity.grc.assessments import visible_results
    assessment = frappe.get_doc("IA Maturity Assessment", doc.assessment)
    assigned = membership(doc.entity, user) == "Contributor" and doc.assigned_to == user
    return (can_read_assessment(assessment, user) or assigned) and visible_results(assessment, user)


def require_assessment(doc, write=False):
    require_login()
    if not can_read_assessment(doc):
        deny()
    if write and not can_edit_assessment(doc):
        deny()


def home(user=None):
    user = user or frappe.session.user
    kind = account_type(user)
    if kind == "Auditor":
        return "/grc/auditor"
    if kind == "Customer":
        return "/grc/customer"
    if kind == "Restricted":
        return "/login?access=inactive"
    if kind == "Guest":
        return "/login"
    return desk_url("home")


def ensure_erp_desk_user(user=None):
    """A Frappe user with no GRC role must be a System User so Desk can open."""
    user = user or frappe.session.user
    if not user or user in {"Guest", "Administrator"} or account_type(user) != "ERP":
        return
    if frappe.db.get_value("User", user, "user_type") == "System User":
        return
    frappe.db.set_value("User", user, "user_type", "System User", update_modified=False)
    frappe.clear_cache(user=user)
    # The redirect below leaves this request before Frappe commits.
    from ia_maturity.compat import in_test
    if not in_test():
        frappe.db.commit()


@contextmanager
def service_write():
    invalidate()
    old = frappe.flags.get("grc_service_write")
    frappe.flags.grc_service_write = True
    try:
        yield
    finally:
        frappe.flags.grc_service_write = old
        invalidate()


def log(action, entity=None, assignment=None, assessment=None, details=None, internal=True):
    from ia_maturity.grc import departments as dept
    department = frappe.db.get_value("IA Maturity Assessment", assessment, "grc_assessment_type") if assessment else None
    if not department and entity:
        types = dept.entity_types(entity)
        if account_type() == "Auditor":
            types &= dept.staff_types()
        department = next(iter(types)) if len(types) == 1 else None
    with service_write():
        frappe.get_doc(dict(doctype="GRC Activity", entity=entity, assignment=assignment,
            assessment=assessment, grc_department=department, actor=frappe.session.user, action=action,
            details=frappe.as_json(details or {}), internal=int(internal))).insert(ignore_permissions=True)


def guard_request():
    """auth_hooks runs AFTER cookie/API-key authentication in supported Frappe v15."""
    if not enabled() or not getattr(frappe.local, "request", None):
        return
    user = frappe.session.user
    path = unquote(frappe.request.path).rstrip("/") or "/"
    method = frappe.form_dict.get("cmd")
    if path.startswith("/api/method/"):
        method = path[len("/api/method/"):]
    elif path.startswith("/api/v1/method/"):
        method = path[len("/api/v1/method/"):]
    grc = account_type(user) in {"Customer", "Auditor", "Restricted"}
    # Always let Frappe destroy a session, including an inactive/old MFA session.
    if method in {"logout", "web_logout", "frappe.handler.logout", "frappe.handler.web_logout"}:
        return
    if user == "Guest":
        # Keep normal Frappe auth, but close legacy GRC sign-up/API bypasses.
        if method and method.startswith("ia_maturity.") and method not in PUBLIC_METHODS:
            deny()
        if method in {"frappe.core.doctype.user.user.sign_up", "frappe.www.login.send_login_link", "frappe.www.login.login_via_key", "frappe.www.login.login_via_token"}:
            deny()
        return
    if not grc:
        if account_type(user) == "ERP":
            ensure_erp_desk_user(user)
            # Default site entry is the GRC website. Desk users skip it.
            if not method and path in {"/", "/index", "/login", "/grc-site"}:
                _redirect(desk_url("home"))
        return
    if account_type() == "Restricted":
        if method in CORE_AUTH_METHODS or path in {"/login", "/update-password"}:
            return
        require_login()
    from ia_maturity.grc.mfa import require_verified_session
    if method:
        allowed = CORE_AUTH_METHODS | PUBLIC_METHODS | {
            "ia_maturity.grc.api." + name for name in API_METHODS
        }
        if account_type() == "Auditor" and method == "frappe.desk.desk_page.getpage" and frappe.form_dict.get("name") == "grc-staff":
            require_verified_session()
            return
        if method not in allowed:
            deny()
        require_verified_session()
        return
    if path.startswith("/api/") or path.startswith("/backups"):
        deny()
    if path.startswith("/private/files/"):
        require_verified_session()
        check_file_url(path)
        return
    allowed_pages = {"/", "/login", "/signup", "/onboarding", "/update-password", "/ia-assessment", "/grc", "/grc-site"}
    if account_type() == "Auditor" and is_desk_path(path, "grc-staff"):
        require_verified_session()
        # Keep old bookmarks usable without rendering native ERP Desk chrome.
        _redirect(home())
    if path not in allowed_pages and not path.startswith(("/grc/", "/grc-site/")):
        deny()
    require_verified_session()


def after_request(response):
    if enabled():
        from ia_maturity.grc.mfa import remember_login_challenge
        remember_login_challenge(response)
        from ia_maturity.grc.response_cache import apply_headers
        apply_headers(response)
    if getattr(frappe.local, "request", None) and ('/ia_maturity.grc.api.site_content_' in frappe.request.path or '/ia_maturity.grc.api.operations_' in frappe.request.path):
        response.headers['Cache-Control'] = 'no-store'
    if getattr(frappe.local, "request", None) and frappe.request.path.endswith((
        "/ia_maturity.grc.api.begin_authenticator", "/ia_maturity.grc.api.confirm_authenticator",
        "/ia_maturity.grc.api.set_optional_mfa", "/ia_maturity.grc.api.security_mfa_settings",
        "/ia_maturity.grc.api.save_mfa_settings")):
        response.headers["Cache-Control"] = "no-store"
    if not enabled() or frappe.session.user == "Guest":
        return
    kind = account_type()
    if kind == "ERP":
        _pin_login_home(response, desk_url("home"))
        return
    if kind not in {"Customer", "Auditor"}:
        return
    from ia_maturity.grc.identity import display_name
    safe_name = display_name(frappe.session.user)
    manager = getattr(frappe.local, "cookie_manager", None)
    if manager and "full_name" in manager.cookies:
        manager.set_cookie("full_name", safe_name)
    # Clear server-cached ERP return paths. Login responses are finalized after on_login.
    frappe.cache.hdel("redirect_after_login", frappe.session.user)
    if getattr(response, "mimetype", "") == "application/json":
        payload = response.get_json(silent=True)
        if isinstance(payload, dict) and isinstance(payload.get("message"), str) and payload["message"] in {"Logged In", "No App"}:
            payload["full_name"] = safe_name
            payload["home_page"] = home()
            payload["redirect_to"] = home()
            response.set_data(frappe.as_json(payload))


def _redirect(target):
    from werkzeug.exceptions import HTTPException
    from werkzeug.utils import redirect
    response = redirect(target, code=302)
    response.headers["Cache-Control"] = "no-store"
    raise HTTPException(response=response)


def _pin_login_home(response, target):
    if getattr(response, "mimetype", "") != "application/json":
        return
    payload = response.get_json(silent=True)
    if isinstance(payload, dict) and payload.get("message") in {"Logged In", "No App"}:
        payload["home_page"] = target
        payload["redirect_to"] = target
        response.set_data(frappe.as_json(payload))


def query_condition(user=None, doctype=None):
    if not enabled():
        return ""
    user = user or frappe.session.user
    if is_admin(user):
        return ""
    values = entities(user)
    if not values:
        return "1=0"
    if account_type(user) == "Customer" and doctype not in {
            "IA Maturity Entity", "IA Maturity Assessment", "GRC Assessment Assignment", "GRC Activity", "GRC Report Release", "IA Maturity Action"}:
        values = [v for v in values if membership(v, user)]
        if not values:
            return "1=0"
    col = "name" if doctype == "IA Maturity Entity" else "entity"
    clause = f"`tab{doctype}`.`{col}` in ({','.join(frappe.db.escape(v) for v in values)})"
    if account_type(user) == "Auditor":
        from ia_maturity.grc import departments as dept
        kinds = ",".join(frappe.db.escape(d) for d in dept.staff_types(user)) or "NULL"
        if doctype == "IA Maturity Assessment":
            clause += f" and `tab{doctype}`.grc_assessment_type in ({kinds})"
            clause += f" and exists (select 1 from `tabGRC Department Grant` g where g.entity=`tab{doctype}`.entity and g.department=`tab{doctype}`.grc_assessment_type and g.active=1 and g.profile_access=1)"
        elif doctype in {"GRC Assessment Assignment", "GRC Report Release", "GRC Activity", "IA Maturity Action"}:
            clause += f" and (assessment in (select a.name from `tabIA Maturity Assessment` a join `tabGRC Department Grant` g on g.entity=a.entity and g.department=a.grc_assessment_type and g.active=1 and g.profile_access=1 where a.grc_assessment_type in ({kinds}))"
            if doctype == "GRC Activity":
                clause += f" or (coalesce(assessment,'')='' and grc_department in ({kinds}))"
            clause += ")"
        elif doctype in {"GRC Follow Up", "GRC Reminder Delivery", "IA Audit Issue"}:
            clause += f" and `tab{doctype}`.grc_department in ({kinds})"
    if doctype in {"GRC Activity", "GRC Follow Up", "GRC Reminder Delivery", "Auditor Customer Assignment"} and account_type(user) == "Customer":
        if doctype != "GRC Activity":
            return "1=0"
        clause += " and `tabGRC Activity`.`internal`=0"
    if doctype in {"IA Maturity Assessment", "GRC Assessment Assignment", "GRC Report Release", "GRC Activity"} and account_type(user) == "Customer":
        admin_orgs = frappe.get_all("GRC Organization Membership", filters={
            "user": user, "active": 1, "membership_role": ["in", ["Organization Admin", "Viewer"]]}, pluck="entity")
        admin_sql = ",".join(frappe.db.escape(v) for v in set(admin_orgs) | inherited_entities(user)) or "NULL"
        own = f"respondent={frappe.db.escape(user)}" if doctype in {"IA Maturity Assessment", "GRC Assessment Assignment"} else (
            f"assessment in (select name from `tabIA Maturity Assessment` where respondent={frappe.db.escape(user)})")
        if doctype == "GRC Activity":
            own = "(" + own + " or assessment is null or assessment='')"
        clause += f" and (entity in ({admin_sql}) or {own})"
    if doctype == "IA Maturity Action" and account_type(user) == "Customer":
        broad = {e for e in values if effective_membership(e, user) in {"Organization Admin", "Viewer", "Holding Viewer"}}
        contributor = {e for e in values if membership(e, user) == "Contributor"}
        broad_sql = ",".join(frappe.db.escape(e) for e in broad) or "NULL"
        contributor_sql = ",".join(frappe.db.escape(e) for e in contributor) or "NULL"
        actor = frappe.db.escape(user)
        clause += f""" and (assessment in (select name from `tabIA Maturity Assessment`
            where entity in ({broad_sql}) or respondent={actor})
            or (entity in ({contributor_sql}) and assigned_to={actor}))"""
        released = "assessment in (select assessment from `tabGRC Report Release`)"
        preliminary = frappe.db.get_single_value("GRC Settings", "results_visibility") == "Preliminary scorecard"
        clause += f" and ({released}" + (" or assessment in (select name from `tabIA Maturity Assessment` where docstatus=1))" if preliminary else ")")
    return clause


def has_permission(doc, ptype=None, user=None):
    if not enabled():
        return True
    user = user or frappe.session.user
    if doc.doctype == "GRC Activity" and ptype not in READ:
        return False
    if is_admin(user):
        return True
    entity = doc.name if doc.doctype == "IA Maturity Entity" else doc.get("entity")
    if not can_access(entity, user):
        return False
    from ia_maturity.grc.departments import can_read
    if doc.doctype != "IA Maturity Entity" and not can_read(doc, user):
        return False
    if account_type(user) == "Customer" and effective_membership(entity, user) == "Holding Viewer" and doc.doctype not in {
            "IA Maturity Entity", "IA Maturity Assessment", "GRC Assessment Assignment", "GRC Activity", "GRC Report Release", "IA Maturity Action"}:
        return False
    if doc.doctype == "GRC Report Release":
        return ptype in READ and can_read_assessment(frappe.get_doc("IA Maturity Assessment", doc.assessment), user)
    if doc.doctype == "IA Maturity Action":
        return ptype in READ and can_read_action(doc, user)
    if doc.doctype == "IA Maturity Assessment":
        return can_read_assessment(doc, user) and (ptype in READ or (
            account_type(user) == "Customer" and doc.docstatus == 0
            and membership(entity, user) in {"Organization Admin", "Contributor"}
            and (membership(entity, user) == "Organization Admin" or doc.respondent == user)))
    if account_type(user) == "Customer":
        if doc.doctype in {"Auditor Customer Assignment", "GRC Follow Up", "GRC Reminder Delivery"}:
            return False
        if doc.doctype == "GRC Activity":
            if doc.internal:
                return False
            if doc.assessment and not can_read_assessment(frappe.get_doc("IA Maturity Assessment", doc.assessment), user):
                return False
        if doc.doctype == "GRC Assessment Assignment" and effective_membership(entity, user) == "Contributor" and doc.respondent != user:
            return False
    return ptype in READ


def check_file_url(url):
    if not url or not url.startswith("/private/files/"):
        deny()
    rows = frappe.get_all("File", filters={"file_url": url, "is_private": 1},
        fields=["name", "attached_to_doctype", "attached_to_name"])
    for row in rows:
        if row.attached_to_doctype in {"IA Maturity Assessment", "IA Maturity Action", "GRC Report Release"} and row.attached_to_name:
            doc = frappe.get_doc(row.attached_to_doctype, row.attached_to_name)
            if doc.doctype == "IA Maturity Assessment" and can_read_assessment(doc):
                return row.name
            if doc.doctype == "IA Maturity Action" and can_read_action(doc):
                return row.name
            if doc.doctype == "GRC Report Release" and can_access(doc.entity):
                assessment = frappe.get_doc("IA Maturity Assessment", doc.assessment)
                if can_read_assessment(assessment):
                    return row.name
    deny()


def file_permission(doc, ptype=None, user=None):
    if not enabled():
        return permission_hook_passthrough()
    grc_file = doc.attached_to_doctype in {"IA Maturity Assessment", "IA Maturity Action", "GRC Report Release"}
    if account_type(user) not in {"Customer", "Auditor"} and not grc_file:
        return permission_hook_passthrough()
    if ptype not in READ:
        return bool(frappe.flags.get("grc_service_write"))
    original = frappe.session.user
    try:
        if user and original != user:
            frappe.set_user(user)
        check_file_url(doc.file_url)
        return True
    except frappe.PermissionError:
        return False
    finally:
        if user and original != user:
            frappe.set_user(original)


def validate_user(doc, method=None):
    if not enabled():
        return
    if doc.is_new() and frappe.session.user == "Guest":
        if not frappe.flags.get("grc_verified_signup_email") or frappe.flags.grc_verified_signup_email != doc.email:
            frappe.throw(_("Verify your email through the GRC signup page before creating an account."), frappe.PermissionError)
    r = {row.role for row in doc.roles}
    before = doc.get_doc_before_save()
    protected = (doc.is_new() and bool(r & (AUDITOR_ROLES | CUSTOMER_ROLES) or doc.get("grc_account_type"))) or before and (
        before.get("grc_account_type") != doc.get("grc_account_type")
        or before.get("grc_mfa_policy") != doc.get("grc_mfa_policy")
        or before.get("grc_mfa_opt_in") != doc.get("grc_mfa_opt_in")
        or before.get("grc_email_verified") != doc.get("grc_email_verified")
        or ({x.role for x in before.roles} & (AUDITOR_ROLES | CUSTOMER_ROLES)) != (r & (AUDITOR_ROLES | CUSTOMER_ROLES))
        or ({x.role for x in before.roles} & (AUDITOR_ROLES | CUSTOMER_ROLES) and {x.role for x in before.roles} != r))
    if protected and not (is_admin() or frappe.flags.get("grc_service_write")):
        deny()
    if r & AUDITOR_ROLES:
        doc.grc_account_type = "Auditor"
    elif r & (CUSTOMER_ROLES - {"IA Assessment Respondent"}):
        doc.grc_account_type = "Customer"
    else:
        doc.grc_account_type = ""
    if doc.grc_account_type in {"Customer", "Auditor"}:
        if (r & AUDITOR_ROLES) and (r & CUSTOMER_ROLES):
            frappe.throw(_("Use separate customer and auditor accounts."))
        # Classification remains restrictive even if an administrator accidentally adds an ERP role.
        doc.user_type = "Website User" if doc.grc_account_type == "Customer" else "System User"
        from ia_maturity.grc.account_security import sync_user
        sync_user(doc)
    else:
        from ia_maturity.grc.mfa_policy import sync_platform_role
        sync_platform_role(doc)


def validate_document(doc, method=None):
    if not enabled() or frappe.flags.get("in_install") or frappe.flags.get("in_migrate"):
        return
    if doc.doctype == "GRC Settings":
        from ia_maturity.grc.verification_limits import POLICY_FIELDS
        for field in POLICY_FIELDS.values():
            # A missing Check field is loaded by Frappe as 0. Treat an absent
            # stored policy as enabled and write that default on a normal save.
            # Lock the row (or its gap) so concurrent policy changes cannot be
            # overwritten by an older settings document.
            rows = frappe.db.sql("select value from `tabSingles` where doctype=%s and field=%s for update",
                                 ("GRC Settings", field))
            if not rows:
                doc.set(field, 1)
                continue
            if bool(cint(doc.get(field))) != (str(rows[0][0]) != "0"):
                frappe.throw(_("Change verification limits through the audited administration controls."), frappe.PermissionError)
    if doc.doctype in {"GRC Activity", "GRC Report Release", "GRC Reminder Delivery"}:
        if not frappe.flags.get("grc_service_write"):
            deny()
        if doc.doctype == "GRC Activity" and not doc.is_new():
            deny()
    elif not (is_admin() or frappe.flags.get("grc_service_write")):
        deny()
    if doc.meta.has_field("grc_department"):
        from ia_maturity.grc import departments as dept
        before = doc.get_doc_before_save()
        if before and before.get("grc_department") and before.grc_department != doc.get("grc_department"):
            frappe.throw(_("The record department cannot change."))
        if not doc.get("grc_department"):
            department = dept.kind(doc)
            if not department and doc.get("entity"):
                candidates = dept.entity_types(doc.entity)
                if account_type() == "Auditor":
                    candidates &= dept.staff_types()
                department = next(iter(candidates)) if len(candidates) == 1 else None
            doc.grc_department = department
    if doc.doctype in {"IA Maturity Entity", "Auditor Customer Assignment"}:
        from ia_maturity.grc.ownership import guard
        guard(doc)
    if doc.doctype == "IA Maturity Entity":
        before = doc.get_doc_before_save()
        parent = doc.get("parent_organization")
        if (not before and parent) or (before and before.get("parent_organization") != parent):
            if not is_admin():
                deny()
        seen = {doc.name, doc.entity_name}
        while parent:
            if parent in seen:
                frappe.throw(_("Parent organizations cannot form a cycle."))
            seen.add(parent)
            if not frappe.db.exists("IA Maturity Entity", parent):
                deny()
            parent = frappe.db.get_value("IA Maturity Entity", parent, "parent_organization", for_update=True)
    if doc.doctype == "Auditor Customer Assignment":
        if account_type(doc.auditor) != "Auditor":
            frappe.throw(_("Assign a GRC auditor account."))
        existing = frappe.db.exists(doc.doctype, {"entity": doc.entity, "auditor": doc.auditor,
            "responsibility": doc.responsibility, "name": ["!=", doc.name or ""]})
        if existing:
            frappe.throw(_("This auditor responsibility already exists; update its active status."))
    if doc.doctype == "GRC Organization Membership":
        if account_type(doc.user) != "Customer":
            frappe.throw(_("Only GRC customer accounts can join an organization."))
    if doc.doctype == "GRC Settings":
        if doc.get("profile_editable_fields"):
            from ia_maturity.grc.profile import validate_policy
            validate_policy(doc.profile_editable_fields)
        if not 1 <= cint(doc.reminder_days) <= 90 or not 1 <= cint(doc.default_due_days) <= 365:
            frappe.throw(_("Enter a reminder interval of 1–90 days and a deadline of 1–365 days."))


def changed(doc, method=None):
    if not enabled() or doc.doctype == "GRC Activity":
        return
    if doc.doctype in {"Auditor Customer Assignment", "GRC Organization Membership"}:
        who = doc.get("auditor") or doc.get("user")
        frappe.clear_cache(user=who)
        frappe.publish_realtime("grc_access_changed", {}, user=who, after_commit=True)
        if not can_access(doc.entity, who):
            # Pending mail must not outlive the recipient's organization access.
            for delivery in frappe.get_all("GRC Reminder Delivery", filters={
                    "entity": doc.entity, "recipient": who, "status": "Queued"},
                    fields=["name", "email_queue"]):
                if delivery.email_queue:
                    status = frappe.db.get_value("Email Queue", delivery.email_queue, "status")
                    if status in {"Not Sent", "Error", "Partially Sent"}:
                        frappe.db.set_value("Email Queue", delivery.email_queue, "status", "Expired")
                frappe.db.set_value("GRC Reminder Delivery", delivery.name,
                    {"status": "Failed", "error": "Organization access revoked before delivery."})
        if doc.doctype == "GRC Organization Membership" and not doc.active:
            for assignment in frappe.get_all("GRC Assessment Assignment",
                    filters={"entity": doc.entity, "respondent": who,
                             "workflow_state": ["!=", "Report Released"]}, pluck="name"):
                frappe.db.set_value("GRC Assessment Assignment", assignment, "needs_reassignment", 1)
        if doc.doctype == "Auditor Customer Assignment" and not doc.active:
            remaining = responsibilities(doc.entity, doc.auditor)
            field = "reviewer" if doc.responsibility == "Reviewer" else "consultant"
            if doc.responsibility not in remaining:
                for assignment in frappe.get_all("GRC Assessment Assignment",
                        filters={"entity": doc.entity, field: doc.auditor,
                                 "workflow_state": ["!=", "Report Released"]}, pluck="name"):
                    previous = frappe.db.get_value("GRC Assessment Assignment", assignment, ["assessment", field], as_dict=True)
                    frappe.db.set_value("GRC Assessment Assignment", assignment,
                        {field: None, "needs_reassignment": 1})
                    log("Assessment ownership revoked", doc.entity, assignment, previous.assessment,
                        {"field": field, "before": previous.get(field), "after": None,
                         "reason": "Customer responsibility revoked"}, internal=True)
    if doc.doctype in {"Auditor Customer Assignment", "GRC Organization Membership", "GRC Settings"}:
        keys = ("auditor", "user", "responsibility", "membership_role", "active", "results_visibility", "profile_editable_fields")
        before = doc.get_doc_before_save()
        log(doc.doctype + " updated", entity=doc.get("entity"), details={
            "record": doc.name, "before": {k: before.get(k) for k in keys if before and before.get(k) is not None},
            "after": {k: doc.get(k) for k in keys if doc.get(k) is not None}})


def forbid_share(doc, method=None):
    if enabled() and doc.share_doctype in TENANT_DOCTYPES:
        frappe.throw(_("GRC records use organization memberships and auditor assignments, not document sharing."))

def document_boundary(doc, ptype=None, user=None):
    """Deny ERP documents even if a portal account accidentally has ERP roles."""
    if not enabled() or account_type(user) not in {"Customer", "Auditor"}:
        return permission_hook_passthrough()
    if doc.doctype in TENANT_DOCTYPES or doc.doctype.startswith(("GRC ", "IA Maturity")) or doc.doctype == "File":
        return permission_hook_passthrough()
    if doc.doctype == "User" and doc.name == (user or frappe.session.user) and ptype in READ:
        return permission_hook_passthrough()
    return False


def evidence_deleted(doc, method=None):
    """Capture deletion through every framework path, not only the portal button."""
    if not enabled() or doc.attached_to_doctype not in {"IA Maturity Assessment", "IA Maturity Action"}:
        return
    if not doc.attached_to_name or not frappe.db.exists(doc.attached_to_doctype, doc.attached_to_name):
        return
    target = frappe.get_doc(doc.attached_to_doctype, doc.attached_to_name)
    assessment = target.name if doc.attached_to_doctype == "IA Maturity Assessment" else target.assessment
    assignment = frappe.db.get_value("IA Maturity Assessment", assessment, "grc_assignment")
    log("Evidence deleted", target.entity, assignment, assessment,
        {"file": doc.name, "filename": doc.file_name}, internal=False)
