"""Read a queued email code on the isolated local test site; never a web API."""
import os
import re
import sys
from email import message_from_string
from pathlib import Path

root = Path(__file__).resolve().parents[3]
os.chdir(root / "sites")
import frappe
frappe.init(site="grc.local")
try:
    frappe.connect()
    if not (frappe.conf.db_name == "grc_local" and frappe.conf.get("mute_emails") and frappe.conf.get("allow_tests")):
        raise RuntimeError("Only available on the muted local acceptance site.")
    email = sys.argv[1]
    if not re.fullmatch(r"grc-journey-[a-z0-9-]+@example\.test", email):
        raise ValueError("Only reserved journey test addresses are supported.")
    if len(sys.argv)>2 and sys.argv[2]=="status":
        exists=frappe.db.exists("User",email)
        print("verified" if exists and frappe.db.get_value("User",email,"grc_email_verified") else "pending" if not exists else "unverified")
        sys.exit(0)
    reg = frappe.db.get_value("IA Maturity Registration", {"email": email, "status": "Pending"}, "name", order_by="creation desc")
    message = frappe.db.get_value("Email Queue", {"reference_doctype": "IA Maturity Registration", "reference_name": reg}, "message", order_by="creation desc")
    if not message:
        raise RuntimeError("No verification email was queued.")
    mail = message_from_string(message)
    for part in mail.walk():
        if part.get_content_type() == "text/html":
            body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8")
            if len(sys.argv)>2 and sys.argv[2]=="link":
                import html
                match=re.search(r'href="([^"]+[?]verify=[^"]+)"',body)
                if not match:raise RuntimeError("Verification link missing.")
                print(html.unescape(match.group(1)))
                break
            match = re.search(r">\s*([0-9]{6})\s*</p>", body)
            if match:
                print(match.group(1))
                break
    else:
        raise RuntimeError("Verification code missing from queued email.")
finally:
    frappe.destroy()
