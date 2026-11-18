"""Disposable authenticator browser fixture. Never available outside the muted local test site."""
import json, os, re, secrets, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
import frappe
frappe.init(site="grc.local");frappe.connect()
try:
    assert frappe.conf.db_name=="grc_local" and frappe.conf.get("mute_emails") and frappe.conf.get("allow_tests")
    action,email=sys.argv[1:3]
    assert re.fullmatch(r"grc-authenticator-[a-z0-9]+@example\.test",email)
    from ia_maturity.grc import security as sec
    from frappe.utils.password import update_password, decrypt
    from frappe.twofactor import get_otpsecret_for_
    import pyotp
    frappe.set_user("Administrator")
    if action in {"create","create-auditor","create-admin"}:
        assert not frappe.db.exists("User",email)
        password=secrets.token_urlsafe(24)
        with sec.service_write():
            frappe.get_doc(dict(doctype="User",email=email,first_name="Authenticator",last_name="Customer",
                roles=[{"role":"GRC App Admin" if action=="create-admin" else "GRC Auditor" if action=="create-auditor" else "GRC Customer"}],send_welcome_email=0)).insert(ignore_permissions=True)
        update_password(email,password);frappe.db.commit()
        print(json.dumps({"email":email,"password":password}))
    elif action=="pending-code":
        from ia_maturity.grc.mfa import pending_key
        frappe.set_user(email);frappe.session.sid=sys.argv[3]
        pending=frappe.cache.get_value(pending_key())
        assert pending,"No pending enrollment for the fixture session."
        print(pyotp.TOTP(decrypt(pending["secret"])).now())
    elif action=="login-code":
        print(pyotp.TOTP(get_otpsecret_for_(email)).now())
    elif action=="cleanup":
        from frappe.sessions import clear_sessions
        clear_sessions(user=email,force=True)
        frappe.delete_doc("User",email,ignore_permissions=True,force=True)
        for suffix in ("_otpsecret","_otplogin"):
            frappe.defaults.clear_default(email+suffix)
        frappe.db.commit()
    else:
        raise ValueError("Unsupported fixture operation.")
finally:
    frappe.destroy()
