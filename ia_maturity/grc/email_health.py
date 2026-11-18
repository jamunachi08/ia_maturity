"""Read-only email diagnostics without bodies, addresses, credentials or raw tracebacks."""
import frappe
from frappe.utils import cint
from ia_maturity.grc import security as sec


def error_category(error):
    text = (error or "").lower()
    if any(x in text for x in ("authenticationerror", "authentication failed", "535", "invalid credentials")):
        return "SMTP authentication rejected"
    if any(x in text for x in ("certificate", "sslerror", "starttls", "tls")):
        return "SMTP TLS or certificate error"
    if any(x in text for x in ("timed out", "timeout", "connectionrefused", "network is unreachable", "name or service not known")):
        return "SMTP connectivity or DNS error"
    if any(x in text for x in ("quota", "rate limit", "too many", "daily limit")):
        return "Provider quota or rate limit"
    if any(x in text for x in ("recipient", "550", "551", "553", "relay")):
        return "Recipient or relay rejected"
    return "Review the Email Queue error in Desk" if text else None


@frappe.whitelist()
def email_diagnostics():
    sec.require_admin()
    from frappe.utils.scheduler import is_scheduler_inactive
    from frappe.utils.background_jobs import get_workers
    accounts = frappe.get_all("Email Account", filters={"enable_outgoing": 1},
        fields=["default_outgoing", "awaiting_password"])
    queues = frappe.db.sql("select status,count(*) as total from `tabEmail Queue` group by status", as_dict=True)
    recent = frappe.get_all("Email Queue", filters={"status": "Error"},
        fields=["name", "modified", "error"], order_by="modified desc", limit_page_length=5)
    verification = frappe.db.sql("""select status,count(*) as total,min(creation) as oldest,
        max(creation) as newest from `tabEmail Queue`
        where reference_doctype='IA Maturity Registration' group by status""", as_dict=True)
    try:
        workers = bool(get_workers())
    except Exception:
        workers = None
    return {"emails_muted": bool(cint(frappe.conf.get("mute_emails"))),
        "queue_suspended": bool(cint(frappe.db.get_default("suspend_email_queue"))),
        "scheduler_inactive": bool(is_scheduler_inactive(verbose=False)),
        "workers_present": workers, "outgoing_accounts": len(accounts),
        "default_outgoing_configured": any(cint(a.default_outgoing) for a in accounts),
        "account_awaiting_password": any(cint(a.awaiting_password) for a in accounts),
        "queue_counts": {row.status: row.total for row in queues},
        "verification_queue": [{"status": r.status, "total": r.total,
            "oldest": str(r.oldest), "newest": str(r.newest)} for r in verification],
        "provider_processing": "Not verified; inspect provider delivery records using the queue Message-ID.",
        "sender_authentication": "Not verified; confirm SPF, DKIM and DMARC for the actual sender domain.",
        "spam_filtering": "Not verified; inspect recipient headers and spam-folder placement.",
        "recent_failures": [{"name": row.name, "modified": str(row.modified),
            "category": error_category(row.error)} for row in recent],
        "note": "Sent means handed to the mail server, not proof of inbox delivery."}
