"""Black-box HTTP acceptance checks, including cookies, API tokens, and MFA."""
import os,json,re
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[3]
credentials=json.loads((ROOT/"sites/grc.local/private/grc-local-credentials.json").read_text())
BASE="http://127.0.0.1:8005"
def call(client,method,payload=None):
 return client.post(BASE+"/api/method/"+method,json=payload or {})
def login(email):
 s=requests.Session()
 r=call(s,"login",{"usr":email,"pwd":credentials[email]})
 assert r.status_code==200,(email,r.status_code,r.text[:250])
 return s,r.json()
def get(s,path,status=200):
 r=s.get(BASE+path);assert r.status_code==status,(path,r.status_code,r.text[:250]);return r
customer,result=login("customer@alpha.example.test")
assert result["home_page"]=="/grc/customer",result
context=get(customer,"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]
assert context["kind"]=="Customer"
for path in ("/app","/app/sales-invoice","/api/resource/Customer","/api/method/frappe.client.get_list?doctype=Customer","/api/v2/document/Customer"):
 get(customer,path,403)
get(customer,"/grc/customer/assessments")
get(customer,"/grc/auditor/admin/settings") # React denies this nested client route; APIs enforce authorization.
get(customer,"/api/method/ia_maturity.grc.api.settings",403)
orgs=get(customer,"/api/method/ia_maturity.grc.api.organizations").json()["message"]
assert [o["name"] for o in orgs]==["Al Noor Industries"],orgs
get(customer,"/api/method/ia_maturity.grc.api.organization_detail?name=Safa%20Financial%20Services",403)
erp,erp_result=login("erp@grc.example.test")
assert erp_result.get("home_page") not in {"/grc/customer","/grc/auditor"},erp_result
assert get(erp,"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="ERP"
auditor,result=login("auditor@grc.example.test")
assert result.get("verification") and result.get("tmp_id"),result
assert auditor.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
os.chdir(ROOT/"sites")
import frappe,pyotp
frappe.init(site="grc.local");frappe.connect();frappe.set_user("Administrator")
from frappe.twofactor import get_otpsecret_for_
otp=pyotp.TOTP(get_otpsecret_for_("auditor@grc.example.test")).now()
r=call(auditor,"login",{"usr":"auditor@grc.example.test","pwd":credentials["auditor@grc.example.test"],"tmp_id":result["tmp_id"],"otp":otp})
assert r.status_code==200,(r.status_code,r.text[:300])
assert r.json()["home_page"]=="/grc/auditor",r.json()
get(auditor,"/api/method/ia_maturity.grc.api.organizations")
get(auditor,"/app",403)
# An API token cannot bypass mandatory MFA, even for otherwise authorized GRC APIs.
from frappe.core.doctype.user.user import generate_keys
keys=generate_keys("auditor@grc.example.test")
api_key=frappe.db.get_value("User","auditor@grc.example.test","api_key")
frappe.db.commit()
token=requests.Session();token.headers["Authorization"]=f"token {api_key}:{keys['api_secret']}"
get(token,"/api/method/ia_maturity.grc.api.organizations",401)
get(token,"/api/resource/Customer",403)
# Revoke and test the existing browser cookie and API token, then restore the demo assignment.
from ia_maturity.grc.administration import assign_customer
assign_customer("Al Noor Industries","auditor@grc.example.test","Consultant",0);frappe.db.commit()
for client in (auditor,):
 assert get(client,"/api/method/ia_maturity.grc.api.organizations").json()["message"]==[]
 get(client,"/api/method/ia_maturity.grc.api.organization_detail?name=Al%20Noor%20Industries",403)
assign_customer("Al Noor Industries","auditor@grc.example.test","Consultant",1)
from ia_maturity.grc.administration import assign_assessment
for name in frappe.get_all("GRC Assessment Assignment", filters={"entity":"Al Noor Industries"}, pluck="name"):
 assign_assessment(name,consultant="auditor@grc.example.test",reviewer="reviewer@grc.example.test")
# Remove temporary token after validation.
frappe.db.set_value("User","auditor@grc.example.test",{"api_key":None,"api_secret":None})
frappe.db.commit()
# Password recovery must create no authenticated staff session and still require MFA.
from urllib.parse import urlparse,parse_qs
target="unassigned@grc.example.test"
recovery_link=frappe.get_doc("User",target)._reset_password(send_email=False)
key=parse_qs(urlparse(recovery_link).query)["key"][0]
frappe.db.commit()
recovery=requests.Session()
response=call(recovery,"frappe.core.doctype.user.user.update_password",
 {"key":key,"new_password":credentials[target],"logout_all_sessions":1})
assert response.status_code==200,(response.status_code,"Staff recovery failed")
assert response.json()["message"]=="/login"
assert get(recovery,"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
_,challenge=login(target)
assert challenge.get("verification") and challenge.get("tmp_id")
frappe.destroy()
print("PASS: shared login, MFA, customer scope, ERP denial, ERP routing, token denial, active-session revocation, recovery cannot bypass MFA.")
