"""Idempotent GRC installation. All customizations belong to ia_maturity."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property
from ia_maturity.grc.schema import PORTAL_ROLES, TENANT_DOCTYPES
from ia_maturity.grc.account_security import MFA_ROLE


def setup():
    if not frappe.conf.get("grc_enabled"):
        return
    from ia_maturity.grc.organization_profile import backfill_assessment_types
    backfill_assessment_types()
    from ia_maturity.grc.departments import setup as setup_departments
    setup_departments()
    from ia_maturity.grc import screen_layouts, themes
    themes.setup()
    screen_layouts.setup()
    from ia_maturity.grc import report_access
    report_access.setup()
    for role in (*PORTAL_ROLES, MFA_ROLE):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(ignore_permissions=True)
        frappe.db.set_value("Role", role, {"desk_access": int(role in {"GRC Auditor", "GRC Consultant", "GRC Reviewer", "GRC Manager", "GRC App Admin"}),
            "two_factor_auth": int(role == MFA_ROLE)})
    for role in ("IA Assessment Respondent", "IA Maturity Reviewer", "IA Maturity Manager"):
        if frappe.db.exists("Role", role):
            frappe.db.set_value("Role", role, {"desk_access": int(role != "IA Assessment Respondent"), "two_factor_auth": 0})
    create_custom_fields({"User": [{
        "fieldname": "grc_account_type", "label": "GRC account type", "fieldtype": "Select",
        "options": "\nCustomer\nAuditor", "insert_after": "user_type", "read_only": 1, "no_copy": 1
    }, {
        "fieldname": "grc_email_notifications", "label": "GRC workflow emails", "fieldtype": "Check",
        "default": "1", "insert_after": "grc_account_type", "read_only": 1
    }, {
        "fieldname": "grc_optional_reminders", "label": "Optional GRC reminders", "fieldtype": "Check",
        "default": "1", "read_only": 1, "insert_after": "grc_email_notifications"
    }, {
        "fieldname": "grc_optional_status_updates", "label": "Optional GRC status updates", "fieldtype": "Check",
        "default": "1", "read_only": 1, "insert_after": "grc_optional_reminders"
    }, {
        "fieldname": "grc_mfa_policy", "label": "GRC MFA policy", "fieldtype": "Select",
        "options": "Default\nRequired\nDisabled", "default": "Default", "read_only": 1, "no_copy": 1,
        "insert_after": "grc_email_notifications"
    }, {
        "fieldname": "grc_email_verified", "label": "GRC email verified", "fieldtype": "Check",
        "default": "0", "read_only": 1, "no_copy": 1, "insert_after": "grc_mfa_policy"
    }]}, update=True)
    create_custom_fields({"User": [{
        "fieldname": "grc_mfa_opt_in", "label": "Optional GRC MFA enrolled",
        "fieldtype": "Check", "default": "0", "read_only": 1, "no_copy": 1,
        "hidden": 1, "insert_after": "grc_mfa_policy"
    }]}, update=True)
    create_custom_fields({"User": [{
        "fieldname": "grc_hide_page_tour", "label": "Hide GRC page tour",
        "fieldtype": "Check", "default": "0", "read_only": 1,
        "insert_after": "grc_optional_status_updates"
    }, {
        "fieldname": "grc_hide_help", "label": "Hide GRC help button",
        "fieldtype": "Check", "default": "0", "read_only": 1,
        "insert_after": "grc_hide_page_tour"
    }]}, update=True)
    # Preserve native OTP secrets and migrate role-based enforcement to per-account policy.
    from ia_maturity.grc.security import service_write, account_type
    from ia_maturity.grc.account_security import sync_user
    for user in frappe.get_all("User", pluck="name"):
        if account_type(user) not in {"Customer", "Auditor"}:
            continue
        doc = frappe.get_doc("User", user)
        before_roles = {row.role for row in doc.roles}
        doc.grc_account_type = account_type(user)
        sync_user(doc)
        old_type = doc.user_type
        doc.user_type = "System User" if account_type(user) == "Auditor" else "Website User"
        verified = bool(frappe.db.exists("IA Maturity Registration", {"email": user, "status": "Verified"}))
        if old_type != doc.user_type or before_roles != {row.role for row in doc.roles} or (verified and not doc.grc_email_verified):
            if verified:
                doc.grc_email_verified = 1
            with service_write():
                doc.save(ignore_permissions=True)
    # Legacy assessment roles remain reusable; portal API applies the narrower row-level policy.
    for doctype in (*TENANT_DOCTYPES, "IA Maturity Template"):
        for role in PORTAL_ROLES:
            add_permission(doctype, role, 0)
            update_permission_property(doctype, role, 0, "read", 1)
            update_permission_property(doctype, role, 0, "print", 1)
            if role == "GRC App Admin":
                for perm in ("write", "create", "delete", "submit", "cancel", "amend", "print", "report"):
                    update_permission_property(doctype, role, 0, perm, 1)
    frappe.db.sql("UPDATE `tabIA Maturity Template` SET assessment_type=%s WHERE assessment_type IS NULL OR assessment_type=%s", ("Internal Audit", ""))
    from ia_maturity.grc.site_content import initialize as initialize_site_content
    initialize_site_content()
    settings = frappe.get_single("GRC Settings")
    changed = False
    if not frappe.db.get_single_value("GRC Settings", "results_visibility"):
        settings.results_visibility = "Preliminary scorecard"
        settings.reminders_enabled = 1
        settings.reminder_days = 7
        settings.default_due_days = 14
        changed = True
    # Report delivery defaults preserve pre-v2.2 behavior (download/email after release).
    stored = {r[0] for r in frappe.db.sql(
        "select field from `tabSingles` where doctype=%s", "GRC Settings")}
    for field, default in (("onboarding_auto_lock", 1), ("onboarding_attention_hours", 48),
                           ("verification_email_limit_enabled", 1), ("verification_ip_limit_enabled", 1)):
        if field not in stored:
            settings.set(field, default)
            changed = True
    if "allow_report_download" not in stored:
        settings.allow_report_download = 1
        changed = True
    if "allow_report_email" not in stored:
        settings.allow_report_email = 1
        changed = True
    if "report_access_timing" not in stored:
        settings.report_access_timing = "After Audit"
        changed = True
    if changed:
        from ia_maturity.grc.security import service_write
        with service_write():
            settings.save(ignore_permissions=True)
    from ia_maturity.grc.mfa_policy import policy as central_mfa_policy
    if not central_mfa_policy():
        frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)
        frappe.db.set_single_value("System Settings", "two_factor_method", "OTP App")
    frappe.db.set_single_value("Website Settings", "home_page", "grc-site")
    # Disable the generic signup path; GRC registrations must verify first.
    frappe.db.set_single_value("Website Settings", "disable_signup", 1)
    for dt, columns in (
        ("Auditor Customer Assignment", ["entity", "auditor", "responsibility"]),
        ("GRC Organization Membership", ["entity", "user"]),
    ):
        frappe.db.add_unique(dt, columns)
    # The imported reference template is published provisionally for local acceptance testing.
    from ia_maturity.grc.assessments import publish
    from ia_maturity.install import SEED_TEMPLATE
    for name in frappe.get_all("IA Maturity Template", filters={"name": SEED_TEMPLATE, "is_active": 1, "grc_published": 0}, pluck="name"):
        publish(name)
    from ia_maturity.grc.workbook import install_grc_template
    install_grc_template()
    frappe.clear_cache()
