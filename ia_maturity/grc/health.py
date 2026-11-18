"""Read-only operational readiness; no credentials or customer data in output."""
import frappe

def check():
    settings=frappe.get_single("GRC Settings")
    from frappe.utils.scheduler import is_scheduler_disabled
    from ia_maturity.grc.public import info
    legal=info()
    checks={
        "grc_enabled":bool(frappe.conf.get("grc_enabled")),
        "https":str(frappe.conf.get("host_name") or "").startswith("https://"),
        "outgoing_email_configured":bool(frappe.db.exists("Email Account",{"enable_outgoing":1,"default_outgoing":1})),
        "emails_unmuted":not bool(frappe.conf.get("mute_emails")),
        "scheduler_enabled":not is_scheduler_disabled(),
        "scoring_owner_approved":bool(settings.scoring_owner_approved),
        "bilingual_content_approved":bool(settings.content_approved),
        "production_hostname_set":bool(settings.production_hostname),
        "approved_legal_content":all(legal.get(k) for k in ("privacy_en","privacy_ar","terms_en","terms_ar")),
        "staff_mfa_enabled":bool(frappe.db.get_single_value("System Settings","enable_two_factor_auth")),
    }
    return {"site":frappe.local.site,"production_ready":all(checks.values()),"checks":checks}
