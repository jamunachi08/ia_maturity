"""Return a TOTP only for a reserved local acceptance account (stdout is consumed by tests)."""
import sys,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
email=sys.argv[1]
assert email in {"auditor@grc.example.test","reviewer@grc.example.test","admin@grc.example.test","unassigned@grc.example.test"}
import frappe,pyotp
frappe.init(site="grc.local");frappe.connect()
assert frappe.conf.db_name=="grc_local" and frappe.conf.mute_emails
from frappe.twofactor import get_otpsecret_for_
# Leave time for the browser to submit; never widen the production OTP window.
remaining=30-time.time()%30
if remaining<5:
 time.sleep(remaining+0.05)
print(pyotp.TOTP(get_otpsecret_for_(email)).now())
frappe.destroy()
