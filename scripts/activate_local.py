"""Enable GRC only on the task's new site."""
import os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
import frappe
frappe.init(site="grc.local");frappe.connect();frappe.set_user("Administrator")
assert frappe.conf.db_name=="grc_local" and frappe.conf.db_socket==str(ROOT/"sites/.grc-db/mysql.sock")
from frappe.installer import update_site_config
for k,v in {"grc_enabled":1,"allow_tests":1,"mute_emails":1,"host_name":"http://localhost:8005","developer_mode":1}.items():
 update_site_config(k,v)
 frappe.conf[k]=v
from ia_maturity.grc.setup import setup
setup()
frappe.db.set_single_value("System Settings","otp_issuer_name","AlphaX GRC")
frappe.db.set_single_value("System Settings","bypass_2fa_for_restricted_ip_users",0)
frappe.db.commit();frappe.destroy()
print("GRC activated on grc.local only.")
