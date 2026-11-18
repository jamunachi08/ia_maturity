"""Idempotent local demo fixtures. Credentials are written privately, never printed."""
import os,json,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
import frappe
frappe.init(site="grc.local");frappe.connect();frappe.set_user("Administrator")
assert frappe.conf.grc_enabled and frappe.conf.db_name=="grc_local"
from ia_maturity.grc import security as sec,assessments as svc
from ia_maturity.grc.administration import assign_customer,assign_assessment
from frappe.utils.password import update_password
from ia_maturity.install import SEED_TEMPLATE
path=ROOT/"sites/grc.local/private/grc-local-credentials.json"
credentials=json.loads(path.read_text())
users=[
 ("customer@alpha.example.test","Noura Hassan","GRC Customer"),
 ("customer@beta.example.test","Khalid Mansour","GRC Customer"),
 ("contributor@alpha.example.test","Sara Ali","GRC Customer"),
 ("auditor@grc.example.test","Omar Saleh","GRC Auditor"),
 ("reviewer@grc.example.test","Lina Ahmed","GRC Reviewer"),
 ("unassigned@grc.example.test","Unassigned Auditor","GRC Auditor"),
 ("admin@grc.example.test","GRC Administrator","GRC App Admin"),
 ("erp@grc.example.test","ERP Administrator","System Manager")]
for email,name,role in users:
 if not frappe.db.exists("User",email):
  with sec.service_write():
   frappe.get_doc(dict(doctype="User",email=email,first_name=name,send_welcome_email=0,
      roles=[{"role":role}],enabled=1)).insert(ignore_permissions=True)
 if email not in credentials:
  password=secrets.token_urlsafe(20);update_password(email,password)
  credentials[email]=password
with sec.service_write():
 for org,owner,sector in [("Al Noor Industries","customer@alpha.example.test","Manufacturing"),("Safa Financial Services","customer@beta.example.test","Banking & Financial Services")]:
  if not frappe.db.exists("IA Maturity Entity",org):
   frappe.get_doc(dict(doctype="IA Maturity Entity",entity_name=org,sector=sector,contact_email=owner,is_active=1)).insert(ignore_permissions=True)
  if not frappe.db.exists("GRC Organization Membership",{"entity":org,"user":owner}):
   frappe.get_doc(dict(doctype="GRC Organization Membership",entity=org,user=owner,membership_role="Organization Admin",active=1)).insert(ignore_permissions=True)
 if not frappe.db.exists("GRC Organization Membership",{"entity":"Al Noor Industries","user":"contributor@alpha.example.test"}):
  frappe.get_doc(dict(doctype="GRC Organization Membership",entity="Al Noor Industries",user="contributor@alpha.example.test",membership_role="Contributor",active=1)).insert(ignore_permissions=True)
assign_customer("Al Noor Industries","auditor@grc.example.test","Consultant")
assign_customer("Al Noor Industries","reviewer@grc.example.test","Reviewer")
for org,owner in [("Al Noor Industries","customer@alpha.example.test"),("Safa Financial Services","customer@beta.example.test")]:
 if not frappe.db.exists("GRC Assessment Assignment",{"entity":org}):
  frappe.set_user(owner)
  doc=svc.new_assessment(org,SEED_TEMPLATE)
  svc.save(doc.name,{a.question_code:{"selected_option":"C" if i%4 else "B","comment":"Current practice documented for local acceptance testing."} for i,a in enumerate(doc.answers) if i<9})
  frappe.set_user("Administrator")
  if org=="Al Noor Industries":
   assign_assessment(doc.grc_assignment,consultant="auditor@grc.example.test",reviewer="reviewer@grc.example.test")
frappe.db.commit()
path.write_text(json.dumps(credentials,indent=2));path.chmod(0o600)
frappe.destroy()
print("Local demo organizations and role-separated accounts are ready. Credentials saved privately.")
