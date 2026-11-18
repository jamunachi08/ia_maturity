"""Read a real native MFA challenge for reserved local performance staff only.

JSON stdout is consumed privately by Playwright. Never print it into shared tool
logs. This helper neither creates challenges nor changes authentication policy.
"""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]


def main():
    if len(sys.argv) != 3:
        raise RuntimeError("A reserved staff identity and native challenge are required.")
    email, challenge = sys.argv[1:]
    if not (email == "admin@grc.example.test" or re.fullmatch(
            r"grc-journey-[a-z0-9]{6,24}-[a-z0-9-]+@example\.test", email)):
        raise RuntimeError("Only reserved local staff identities are supported.")
    # Supported Frappe v15 issues an eight-character native tmp_id.
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", challenge):
        raise RuntimeError("Invalid native challenge identifier.")
    os.chdir(ROOT / "sites")
    import frappe
    import pyotp
    from ia_maturity.grc import security as sec
    frappe.init(site="grc.local")
    try:
        frappe.connect()
        if not (frappe.local.site == "grc.local" and frappe.conf.db_name == "grc_local"
                and frappe.conf.get("mute_emails") and frappe.conf.get("allow_tests")
                and frappe.conf.db_socket == str(ROOT / "sites/.grc-db/mysql.sock")):
            raise RuntimeError("Only the muted disposable local acceptance site is allowed.")
        if sec.account_type(email) != "Auditor" or not frappe.db.get_value("User", email, "enabled"):
            raise RuntimeError("An active reserved staff account is required.")
        cached_user = frappe.cache.get(challenge + "_usr")
        secret = frappe.cache.get(challenge + "_otp_secret")
        counter = frappe.cache.get(challenge + "_token")
        if isinstance(cached_user, bytes):
            cached_user = cached_user.decode()
        if isinstance(secret, bytes):
            secret = secret.decode()
        if cached_user != email or not secret:
            raise RuntimeError("Native challenge is absent, expired or belongs to another account.")
        method = frappe.db.get_single_value("System Settings", "two_factor_method")
        # Match frappe.twofactor.confirm_otp_token: native Email uses HOTP at
        # the stored challenge counter; authenticator challenges use TOTP.
        if method == "Email":
            if counter is None:
                raise RuntimeError("Native email challenge counter is missing.")
            code = pyotp.HOTP(secret).at(int(counter))
        elif method == "OTP App":
            code = pyotp.TOTP(secret).now()
        else:
            raise RuntimeError("Only native Email and OTP App methods are supported.")
        print(json.dumps({"code": code}))
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
