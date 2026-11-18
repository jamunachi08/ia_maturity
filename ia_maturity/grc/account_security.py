"""Admin-managed GRC MFA policy backed by Frappe's native role checks."""
import json
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc import security as sec

MFA_ROLE = "GRC Account MFA"
LEGACY_MFA_ROLE = "GRC Customer MFA"
POLICIES = {"Default", "Required", "Disabled"}
from ia_maturity.grc.schema import PORTAL_ROLES, AUDITOR_ROLES
POLICY_ROLES = set(PORTAL_ROLES) | AUDITOR_ROLES


def role_policies():
    raw = frappe.db.get_single_value("GRC Settings", "mfa_role_policies") or "{}"
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        frappe.throw(_("Invalid GRC role MFA policies. Contact the platform administrator."))
    if not isinstance(value, dict) or any(k not in POLICY_ROLES or v not in POLICIES for k, v in value.items()):
        frappe.throw(_("Invalid GRC role MFA policies. Contact the platform administrator."))
    return value


def role_default(roles, policies=None):
    policies = role_policies() if policies is None else policies
    selected = {policies.get(role, "Default") for role in roles if role in POLICY_ROLES}
    # A required role wins over a disabled role for accounts with multiple roles.
    return "Required" if "Required" in selected else "Disabled" if "Disabled" in selected else "Default"


def effective_policy(doc, policies=None):
    policy = doc.get("grc_mfa_policy") or "Default"
    if policy not in POLICIES:
        frappe.throw(_("Choose a valid MFA policy."))
    return policy if policy != "Default" else role_default({row.role for row in doc.roles}, policies)


def desired(doc, policies=None):
    if doc.get("grc_account_type") == "Customer":
        return False
    override = effective_policy(doc, policies)
    if override != "Default":
        return override == "Required"
    from ia_maturity.grc.mfa_policy import policy as central_policy
    central = central_policy() or "Disabled"
    # Enrollment and the old derived MFA role do not imply an admin requirement.
    return central == "Enforced" or central == "Enabled" and bool(cint(doc.get("grc_mfa_opt_in")))


def sync_user(doc):
    if doc.name in {"Administrator", "Guest"} or doc.get("grc_account_type") not in {"Customer", "Auditor"}:
        return
    from ia_maturity.grc.mfa_policy import sync_platform_role
    sync_platform_role(doc)
    needs = desired(doc)
    # Other roles and site-wide MFA are never weakened by a GRC policy change.
    other_roles = ({row.role for row in doc.roles} | {"All"}) - {MFA_ROLE, LEGACY_MFA_ROLE}
    if (doc.get("grc_mfa_policy") == "Disabled" and
            (not doc.get_doc_before_save() or doc.get_doc_before_save().get("grc_mfa_policy") != "Disabled") and other_roles
            and frappe.db.exists("Role", {"name": ["in", list(other_roles)], "two_factor_auth": 1})):
        frappe.throw(_("Another role or site policy requires MFA. Ask the platform administrator to review it."))
    doc.set("roles", [row for row in doc.roles if row.role != LEGACY_MFA_ROLE and (row.role != MFA_ROLE or needs)])
    if needs and MFA_ROLE not in {row.role for row in doc.roles}:
        doc.append("roles", {"role": MFA_ROLE})


@frappe.whitelist()
def security_accounts(search=None, page=1):
    sec.require_admin()
    from ia_maturity.grc.identity import display_name
    from ia_maturity.grc.mfa import required
    from frappe.twofactor import get_default
    page=max(1,cint(page))
    filters={"grc_account_type":["in",["Customer","Auditor"]],"name":["not in",["Administrator","Guest"]]}
    options={}
    if search:
        term="%" + str(search)[:140] + "%"
        options["or_filters"]={"name":["like",term],"full_name":["like",term]}
    rows=frappe.get_all("User",filters=filters,fields=["name","grc_account_type","grc_mfa_policy","enabled","grc_email_verified"],
        order_by="name",limit_start=(page-1)*20,limit_page_length=21,**options)
    more=len(rows)>20
    from ia_maturity.grc.mfa_policy import method
    result=[]
    for row in rows[:20]:
        result.append({"name":row.name,"full_name":display_name(row.name),"kind":row.grc_account_type,
            "policy":"Email OTP" if row.grc_account_type == "Customer" else row.grc_mfa_policy or "Default",
            "effective_policy":"Email OTP" if row.grc_account_type == "Customer" else "Required" if required(row.name) else "Disabled",
            "roles":sorted(sec.roles(row.name) & POLICY_ROLES),
            "method":"Email OTP" if row.grc_account_type == "Customer" else method(),"enabled":bool(row.enabled),
            "required":required(row.name),"enrolled":False if row.grc_account_type == "Customer" else bool(cint(get_default(row.name+"_otplogin"))),
            "email_verified":bool(row.grc_email_verified),"app_admin":"GRC App Admin" in sec.roles(row.name)})
    return {"rows":result,"has_more":more,"page":page}


@frappe.whitelist(methods=["POST"])
def set_mfa_policy(user, policy, current_password):
    sec.require_admin()
    if sec.account_type(user) == "Customer":
        frappe.throw(_("Customers use email verification codes. Password MFA policy applies only to staff."))
    from frappe.utils.password import check_password
    from frappe.sessions import clear_sessions
    from ia_maturity.grc.mfa import configured
    from ia_maturity.grc.auth import limit
    if policy not in POLICIES or sec.account_type(user) not in {"Customer","Auditor"} or user in {"Guest","Administrator"}:
        sec.deny()
    limit("mfa-policy-admin",frappe.session.user,10,seconds=900)
    if not current_password:
        frappe.throw(_("Enter your current password."))
    check_password(frappe.session.user,current_password,delete_tracker_cache=False)
    from ia_maturity.grc.mfa_policy import lock_settings
    lock_settings()
    frappe.db.sql("select name from tabUser where name=%s for update",user)
    doc=frappe.get_doc("User",user)
    before=doc.get("grc_mfa_policy") or "Default"
    doc.grc_mfa_policy=policy
    if desired(doc) and not configured():
        frappe.throw(_("Enable OTP App authentication in System Settings before requiring MFA."))
    if desired(doc):
        from ia_maturity.grc.mfa_policy import method, email_ready
        if method() == "Email" and not email_ready():
            frappe.throw(_("Configure an active default outgoing email account before enabling email MFA."))
    if before!=policy:
        with sec.service_write():
            doc.save(ignore_permissions=True)
        frappe.clear_cache(user=user)
        clear_sessions(user=user,keep_current=False,force=True)
        sec.log("MFA policy changed",details={"user":user,"before":before,"after":policy})
    reauthenticate = before != policy and user == frappe.session.user
    if reauthenticate:
        from ia_maturity.grc.mfa_policy import logout_current_request
        logout_current_request()
    return {"user":user,"policy":policy,"sessions_revoked":before!=policy,"reauthenticate":reauthenticate}


@frappe.whitelist()
def security_role_policies():
    sec.require_admin()
    configured = role_policies()
    return [{"role": role, "policy": configured.get(role, "Default")} for role in sorted(AUDITOR_ROLES)]


@frappe.whitelist(methods=["POST"])
def set_role_mfa_policy(role, policy, current_password):
    """Update a role default and synchronize inheriting GRC accounts atomically."""
    sec.require_admin()
    if role in sec.CUSTOMER_ROLES:
        frappe.throw(_("Customers use email verification codes. Password MFA policy applies only to staff."))
    from frappe.utils.password import check_password
    from frappe.sessions import clear_sessions
    from ia_maturity.grc.auth import limit
    from ia_maturity.grc.mfa import configured
    if role not in AUDITOR_ROLES or policy not in POLICIES:
        sec.deny()
    limit("mfa-policy-admin", frappe.session.user, 10, seconds=900)
    if not current_password:
        frappe.throw(_("Enter your current password."))
    check_password(frappe.session.user, current_password, delete_tracker_cache=False)
    # Serialize role and individual policy updates before locking any User rows.
    from ia_maturity.grc.mfa_policy import lock_settings
    lock_settings()
    if policy == "Required" and not configured():
        frappe.throw(_("Enable OTP App authentication in System Settings before requiring MFA."))
    if policy == "Required":
        from ia_maturity.grc.mfa_policy import method, email_ready
        if method() == "Email" and not email_ready():
            frappe.throw(_("Configure an active default outgoing email account before enabling email MFA."))
    policies = role_policies()
    before = policies.get(role, "Default")
    if before == policy:
        return {"role": role, "policy": policy, "affected": 0}
    names = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
    docs = []
    for name in sorted(set(names) - {"Guest", "Administrator"}):
        frappe.db.sql("select name from `tabUser` where name=%s for update", name)
        doc = frappe.get_doc("User", name)
        if doc.get("grc_account_type") not in {"Customer", "Auditor"} or (doc.get("grc_mfa_policy") or "Default") != "Default":
            continue
        docs.append((doc, desired(doc)))
    if policy == "Default":
        policies.pop(role, None)
    else:
        policies[role] = policy
    # Returning to inheritance can also turn MFA on (for example Enforced).
    if any(desired(doc, policies) for doc, _ in docs):
        if not configured():
            frappe.throw(_("Enable OTP App authentication in System Settings before requiring MFA."))
        from ia_maturity.grc.mfa_policy import method, email_ready
        if method() == "Email" and not email_ready():
            frappe.throw(_("Configure an active default outgoing email account before enabling email MFA."))
    frappe.db.set_single_value("GRC Settings", "mfa_role_policies", json.dumps(policies, sort_keys=True))
    affected = []
    for doc, old_required in docs:
        new_required = desired(doc)
        old_roles = {row.role for row in doc.roles}
        sync_user(doc)
        if old_roles != {row.role for row in doc.roles}:
            with sec.service_write():
                doc.save(ignore_permissions=True)
        if old_required != new_required:
            affected.append(doc.name)
    for name in affected:
        frappe.clear_cache(user=name)
        clear_sessions(user=name, keep_current=False, force=True)
    sec.log("MFA role policy changed", details={"role": role, "before": before, "after": policy, "affected": len(affected)})
    reauthenticate = frappe.session.user in affected
    if reauthenticate:
        from ia_maturity.grc.mfa_policy import logout_current_request
        logout_current_request()
    return {"role": role, "policy": policy, "affected": len(affected),"reauthenticate":reauthenticate}
