"""Exercise password changes against real sessions using disposable local accounts."""
import os, secrets, requests, pyotp
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
import frappe
frappe.init(site="grc.local");frappe.connect();frappe.set_user("Administrator")
assert frappe.conf.db_name=="grc_local" and frappe.conf.mute_emails
from ia_maturity.grc import security as sec
from frappe.utils.password import update_password
from frappe.twofactor import get_otpsecret_for_
BASE="http://127.0.0.1:8005"
def call(client,method,data):
 return client.post(BASE+"/api/method/"+method,json=data)
created=[]
try:
 for role in ("GRC Customer","GRC Auditor"):
  email="grc-profile-"+secrets.token_hex(5)+"@example.test"
  old=secrets.token_urlsafe(24);new=secrets.token_urlsafe(24)
  with sec.service_write():
   frappe.get_doc(dict(doctype="User",email=email,first_name="Profile acceptance",roles=[{"role":role}],send_welcome_email=0)).insert(ignore_permissions=True)
  created.append(email);update_password(email,old);frappe.db.commit()
  client=requests.Session()
  r=call(client,"login",{"usr":email,"pwd":old});assert r.status_code==200
  if role=="GRC Auditor":
   data=r.json();assert data.get("verification")
   code=pyotp.TOTP(get_otpsecret_for_(email)).now();frappe.db.commit()
   wrong=("0" if code[0]!="0" else "1")+code[1:]
   failed=call(client,"login",{"usr":email,"pwd":old,"tmp_id":data["tmp_id"],"otp":wrong})
   assert failed.status_code==401,"Invalid MFA code accepted"
   assert client.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
   code=pyotp.TOTP(get_otpsecret_for_(email)).now()
   r=call(client,"login",{"usr":email,"pwd":old,"tmp_id":data["tmp_id"],"otp":code});assert r.status_code==200
   replay=requests.Session()
   failed=call(replay,"login",{"usr":email,"pwd":old,"tmp_id":data["tmp_id"],"otp":code})
   assert failed.status_code!=200,"Consumed MFA challenge accepted"
   assert replay.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
  context=client.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"];assert context["kind"] in {"Customer","Auditor"}
  bad=call(client,"ia_maturity.grc.api.change_password",{"current_password":"incorrect","new_password":new,"confirm_password":new})
  assert bad.status_code==401,("wrong password accepted",bad.status_code)
  result=call(client,"ia_maturity.grc.api.change_password",{"current_password":old,"new_password":new,"confirm_password":new})
  assert result.status_code==200,("password change failed",role,result.status_code,result.text[:200])
  assert result.json()["message"]["redirect"]=="/login"
  assert client.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
  again=requests.Session()
  assert call(again,"login",{"usr":email,"pwd":old}).status_code==401
  response=call(again,"login",{"usr":email,"pwd":new});assert response.status_code==200
  if role=="GRC Auditor":
   challenge=response.json()
   assert challenge.get("verification"),"Staff MFA bypass after password change"
   code=pyotp.TOTP(get_otpsecret_for_(email)).now()
   assert call(again,"login",{"usr":email,"pwd":new,"tmp_id":challenge["tmp_id"],"otp":code}).status_code==200
   sid=again.cookies.get("sid")
   saved=frappe.cache.hget("session",sid)
   assert saved["data"]["grc_validated_mfa_user"]==email
   # Emulate a pre-upgrade session: only the server-side proof is removed.
   saved["data"].pop("grc_validated_mfa_user")
   frappe.cache.hset("session",sid,saved)
   frappe.db.sql("update `tabSessions` set sessiondata=%s where sid=%s",(str(saved["data"]),sid))
   frappe.db.commit()
   assert again.get(BASE+"/api/method/ia_maturity.grc.api.bootstrap").json()["message"]["kind"]=="Guest"
 print("PASS: customer/staff password changes verify the current password, sign out sessions, reject old passwords and retain staff MFA.")
finally:
 frappe.db.rollback();frappe.set_user("Administrator")
 for email in created:
  assert email.startswith("grc-profile-") and email.endswith("@example.test")
  frappe.delete_doc("User",email,force=1,ignore_permissions=True)
 frappe.db.commit();frappe.destroy()
