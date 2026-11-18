"""Integration coverage for GRC tenant, account, workflow, and report boundaries."""
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import frappe
from ia_maturity.compat import desk_url
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import api, security as sec, assessments as svc
from ia_maturity.grc.administration import assign_customer, assign_assessment, save_settings
from ia_maturity.install import SEED_TEMPLATE
from ia_maturity.grc import departments
from frappe.utils.file_manager import save_file

PREFIX="grc-test-"
CUSTOMER="grc-test-owner@example.test"
OTHER="grc-test-other@example.test"
CONTRIBUTOR="grc-test-contributor@example.test"
AUDITOR="grc-test-auditor@example.test"
REVIEWER="grc-test-reviewer@example.test"
OUTSIDER="grc-test-outsider@example.test"
ERP="grc-test-erp@example.test"
APP_ADMIN="grc-test-app-admin@example.test"
ORG="_Test GRC Alpha"
ORG2="_Test GRC Beta"
# Redis counters outlive database rollbacks. Isolate only this module's reserved fixture addresses.
RATE_EMAILS=set(re.findall(r"grc-test-[a-z0-9-]+@[a-z0-9.-]+",Path(__file__).read_text()))
RATE_EMAILS.update({"grc-test-signup-existing@example.test","grc-test-signup-invited@example.test"})

class TestGRC(FrappeTestCase):
 @classmethod
 def setUpClass(cls):
  super().setUpClass()
  frappe.set_user("Administrator")
  assert sec.enabled(), "Enable grc_enabled on the isolated test site."
  for email,role in [(CUSTOMER,"GRC Customer"),(OTHER,"GRC Customer"),(CONTRIBUTOR,"GRC Customer"),
      (AUDITOR,"GRC Auditor"),(REVIEWER,"GRC Reviewer"),(OUTSIDER,"GRC Auditor"),(ERP,"System Manager"),(APP_ADMIN,"GRC App Admin")]:
   if not frappe.db.exists("User",email):
    with sec.service_write():
     frappe.get_doc(dict(doctype="User",email=email,first_name=email.split("@")[0],
      send_welcome_email=0,roles=[{"role":role}])).insert(ignore_permissions=True)
  with sec.service_write():
   for name in (ORG,ORG2):
    if not frappe.db.exists("IA Maturity Entity",name):
     frappe.get_doc(dict(doctype="IA Maturity Entity",entity_name=name)).insert(ignore_permissions=True)
   for entity,user,role in [(ORG,CUSTOMER,"Organization Admin"),(ORG,CONTRIBUTOR,"Contributor"),(ORG2,OTHER,"Organization Admin")]:
    if not frappe.db.exists("GRC Organization Membership",{"entity":entity,"user":user}):
     frappe.get_doc(dict(doctype="GRC Organization Membership",entity=entity,user=user,membership_role=role,active=1)).insert(ignore_permissions=True)
  # This retained suite exercises the IA tenant boundary. Department access is
  # explicit; an auditor role or customer assignment must never imply it.
  for user,role in [(AUDITOR,"Consultant"),(REVIEWER,"Reviewer"),(OUTSIDER,"Reviewer")]:
   departments.save_department_staff(user,"Internal Audit",role)
  for entity in (ORG,ORG2):
   departments.grant(entity,"Internal Audit","Retained IA regression fixture")
  assign_customer(ORG,AUDITOR,"Consultant")
  assign_customer(ORG,REVIEWER,"Reviewer")
  assign_customer(ORG2,OUTSIDER,"Reviewer")
  frappe.db.commit()

 def setUp(self):
  frappe.set_user("Administrator")
  # Legacy evidence workflows explicitly opt in; production defaults stay off.
  frappe.db.set_single_value("GRC Settings", "question_extras_enabled", 1)
  # Fresh installs keep questionnaire comments/attachments off (only upgraded sites were
  # backfilled to on), so this suite opts its seed template in per test; tearDown rolls it back.
  frappe.db.set_value("IA Maturity Template", SEED_TEMPLATE, {"default_allow_comment": 1, "default_allow_attachment": 1}, update_modified=False)
  frappe.db.set_single_value("GRC Settings", {"mfa_policy":"", "mfa_method":"", "mfa_revision":"", "mfa_role_policies":"",
   "report_access_timing":"After Audit", "allow_report_download":1, "allow_report_email":1})
  frappe.db.set_single_value("System Settings", {"enable_two_factor_auth":1,"two_factor_method":"OTP App"})
  for user in (AUDITOR,REVIEWER,OUTSIDER,APP_ADMIN,CUSTOMER,OTHER,CONTRIBUTOR):
   with sec.service_write():
    doc=frappe.get_doc("User",user);doc.grc_mfa_policy="Default";doc.save(ignore_permissions=True)
  frappe.flags.in_test=True
  self.sent_email=frappe._dict(status="Sent",reload=lambda:None,send=lambda:None)
  from ia_maturity.grc.auth import digest
  for email in RATE_EMAILS:
   for kind in ("request-email","request-cooldown","password-change","mfa-enrollment","mfa-confirm","report-email","mfa-policy-admin"):
    frappe.cache.delete(f"grc:{frappe.local.site}:{kind}:{digest(email)}")
  for kind in ("request-ip","verify-ip","consultation-ip"):
   frappe.cache.delete(f"grc:{frappe.local.site}:{kind}:{digest('local')}")

 def tearDown(self):
  frappe.set_user("Administrator")
  frappe.db.rollback()
  frappe.clear_cache()

 def make(self,entity=ORG,owner=CUSTOMER,submit=False):
  frappe.set_user(owner)
  doc=svc.new_assessment(entity,SEED_TEMPLATE)
  answers={a.question_code:{"selected_option":"C","comment":"Documented current practice"} for a in doc.answers}
  svc.save(doc.name,answers)
  if submit: svc.submit(doc.name)
  doc.reload()
  return doc

 def assigned(self,doc):
  frappe.set_user("Administrator")
  assign_assessment(doc.grc_assignment,consultant=AUDITOR,reviewer=REVIEWER)

 def assert_denied_request(self,user,path,cmd=None):
  frappe.set_user(user)
  with patch.object(frappe.local,"request",SimpleNamespace(path=path),create=True),patch.object(frappe.local,"form_dict",frappe._dict(cmd=cmd)):
   with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):sec.guard_request()

 def test_customer_assignment_and_query_scope(self):
  for user in (AUDITOR,REVIEWER):
   frappe.set_user(user)
   self.assertIn(ORG,sec.entities())
   self.assertNotIn(ORG2,sec.entities())
   self.assertEqual([d.name for d in frappe.get_list("IA Maturity Entity",filters={"name":["in",[ORG,ORG2]]})],[ORG])
   with self.assertRaises(frappe.PermissionError):api.organization_detail(ORG2)
  frappe.set_user(OUTSIDER)
  self.assertNotIn(ORG,sec.entities())

 def test_no_assignments_empty_queue(self):
  frappe.set_user("Administrator")
  assign_customer(ORG2,OUTSIDER,"Reviewer",0)
  frappe.set_user(OUTSIDER)
  self.assertEqual(api.dashboard()["assessments"],[])
  self.assertEqual(api.dashboard()["customer_count"],0)

 def test_customer_and_contributor_isolation(self):
  doc=self.make()
  frappe.set_user(OTHER)
  with self.assertRaises(frappe.PermissionError):api.assessment(doc.name)
  frappe.set_user(CONTRIBUTOR)
  with self.assertRaises(frappe.PermissionError):api.assessment(doc.name)
  self.assertNotIn(doc.name,[a["name"] for a in api.dashboard()["assessments"]])

 def test_erp_routes_generic_methods_and_tokens_policy(self):
  for user in (CUSTOMER,AUDITOR):
   for route in ("/app","/app/sales-invoice","/desk","/api/resource/Customer","/api/v2/document/Customer","/backups/data.sql.gz"):
    self.assert_denied_request(user,route)
   for method in ("frappe.client.get_list","frappe.client.get","frappe.desk.search.search_link","frappe.desk.query_report.run","ia_maturity.api.get_assessments"):
    self.assert_denied_request(user,"/api/method/"+method)
  frappe.set_user(ERP)
  with patch.object(frappe.local,"request",SimpleNamespace(path="/app"),create=True),patch.object(frappe.local,"form_dict",frappe._dict()):
   sec.guard_request()
  self.assertEqual(sec.account_type(ERP),"ERP")

 def test_permission_delegation_preserves_native_and_tenant_denials(self):
  from frappe.permissions import has_controller_permissions
  from ia_maturity.compat import permission_hook_passthrough
  doc=self.make()
  with sec.service_write():
   file=save_file("erp-hook-regression.txt",b"private GRC evidence",doc.doctype,doc.name,is_private=1)
  protected_user=frappe.get_doc("User","Administrator")
  # Exercise the actual v15 dispatcher and the v16 all-hooks-must-pass contract.
  def v16_permissions(document,ptype,user):
   hooks=frappe.get_hooks("has_permission")
   for method in reversed(hooks.get(document.doctype,[])+hooks.get("*",[])):
    if not frappe.call(method,doc=document,ptype=ptype,user=user):return False
   return True
  for version,check,neutral in [("15.118.0",has_controller_permissions,None),("16.0.0",v16_permissions,True)]:
   with self.subTest(version=version),patch.object(frappe,"__version__",version):
    self.assertIs(permission_hook_passthrough(),neutral)
    self.assertFalse(check(doc,"read",user=OTHER))
    self.assertFalse(check(file,"read",user=ERP))
    self.assertFalse(check(protected_user,"read",user=ERP))
    self.assertIs(sec.document_boundary(frappe._dict(doctype="Sales Invoice"),"read",ERP),neutral)
    self.assertIs(sec.file_permission(frappe._dict(attached_to_doctype="Customer"),"read",ERP),neutral)

 def test_logout_is_available_for_portal_and_inactive_sessions(self):
  for user in (CUSTOMER,AUDITOR,ERP):
   frappe.set_user(user)
   for method in ("logout","web_logout","frappe.handler.logout","frappe.handler.web_logout"):
    with self.subTest(user=user,method=method),patch("ia_maturity.grc.mfa.require_verified_session",side_effect=AssertionError("Logout must not require a verified session")),patch.object(frappe.local,"request",SimpleNamespace(path="/"),create=True),patch.object(frappe.local,"form_dict",frappe._dict(cmd=method)):
     sec.guard_request()
  with patch("ia_maturity.grc.security.account_type",return_value="Restricted"),patch("ia_maturity.grc.mfa.require_verified_session",side_effect=AssertionError("Inactive sessions must be able to log out")),patch.object(frappe.local,"request",SimpleNamespace(path="/"),create=True),patch.object(frappe.local,"form_dict",frappe._dict(cmd="web_logout")):
   sec.guard_request()

 def test_accidental_erp_role_does_not_override_portal(self):
  frappe.set_user("Administrator")
  with sec.service_write():frappe.get_doc("User",AUDITOR).add_roles("System Manager")
  self.assertEqual(sec.account_type(AUDITOR),"Auditor")
  self.assert_denied_request(AUDITOR,"/api/resource/Sales Invoice")
  self.assert_denied_request(AUDITOR,"/app")

 def test_revocation_blocks_records_and_private_files(self):
  doc=self.make()
  self.assigned(doc)
  with sec.service_write():file=save_file("test-evidence.txt",b"GRC confidential",doc.doctype,doc.name,is_private=1)
  frappe.set_user(AUDITOR);sec.check_file_url(file.file_url)
  frappe.set_user("Administrator");assign_customer(ORG,AUDITOR,"Consultant",0)
  frappe.set_user(AUDITOR)
  with self.assertRaises(frappe.PermissionError):api.assessment(doc.name)
  with self.assertRaises(frappe.PermissionError):sec.check_file_url(file.file_url)
  self.assertFalse(frappe.has_permission(doc.doctype,doc=doc,user=AUDITOR))
  a=frappe.get_doc("GRC Assessment Assignment",doc.grc_assignment)
  self.assertTrue(a.needs_reassignment);self.assertFalse(a.consultant)

 def test_assignment_alone_does_not_allow_review(self):
  doc=self.make(submit=True)
  frappe.set_user(AUDITOR)
  with self.assertRaises(frappe.PermissionError):svc.transition(doc.name,"start_review")
  self.assigned(doc)
  frappe.set_user(AUDITOR);svc.transition(doc.name,"start_review")
  with self.assertRaises(frappe.PermissionError):svc.transition(doc.name,"approve")
  frappe.set_user(REVIEWER);result=svc.transition(doc.name,"approve")
  self.assertEqual(result["state"],"Approved")

 def test_status_only_strips_scores_report_actions(self):
  doc=self.make(submit=True)
  self.assertIn("overall_score",api.assessment(doc.name))
  frappe.set_user("Administrator");save_settings({"results_visibility":"Status only"})
  frappe.set_user(CUSTOMER);result=api.assessment(doc.name)
  for key in ("overall_score","maturity_level","section_scores","gating_note","report","pdf_url"):
   self.assertNotIn(key,result)
  self.assertEqual(api.actions()["items"],[])
  self.assertEqual(api.dashboard()["overdue_actions"],[])
  from ia_maturity.report_data import get_report_context
  with self.assertRaises(frappe.PermissionError):get_report_context(doc)
  with self.assertRaises(frappe.PermissionError):api.download_report(doc.name)

 def test_published_policy_and_submitted_score_immutable(self):
  doc=self.make(submit=True)
  before=doc.grc_policy_snapshot;score=doc.overall_score
  frappe.set_user("Administrator")
  settings=frappe.get_single("IA Maturity Settings");settings.points_c=80;settings.save(ignore_permissions=True)
  doc.reload();doc.calculate()
  self.assertEqual(doc.overall_score,score);self.assertEqual(doc.grc_policy_snapshot,before)
  template=frappe.get_doc("IA Maturity Template",SEED_TEMPLATE);template.questions[0].question_text="Changed"
  with self.assertRaises(frappe.ValidationError):template.save(ignore_permissions=True)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):svc.save(doc.name,{})

 def test_full_correction_review_release_and_frozen_pdf(self):
  doc=self.make(submit=True);self.assigned(doc)
  frappe.set_user(REVIEWER);svc.transition(doc.name,"start_review")
  corrected=svc.transition(doc.name,"clarify","Please explain the evidence for question 1.")
  self.assertNotEqual(corrected["name"],doc.name)
  old=frappe.get_doc(doc.doctype,doc.name);self.assertEqual(old.docstatus,2)
  self.assertEqual(old.overall_score,75)
  frappe.set_user(CUSTOMER);svc.submit(corrected["name"])
  frappe.set_user(REVIEWER);svc.transition(corrected["name"],"start_review");svc.transition(corrected["name"],"approve")
  result=svc.transition(corrected["name"],"release")
  self.assertTrue(result["released"])
  release=frappe.get_doc("GRC Report Release",{"assessment":corrected["name"]})
  frozen=release.report_context;sha=release.pdf_sha256
  self.assertTrue(frappe.get_doc("File",release.pdf_file).get_content().startswith(b"%PDF"))
  frappe.set_user("Administrator");save_settings({"results_visibility":"Status only"})
  frappe.set_user(CUSTOMER);self.assertTrue(api.assessment(corrected["name"])["results_visible"])
  self.assertEqual(frappe.db.get_value("GRC Report Release",release.name,"pdf_sha256"),sha)
  self.assertEqual(frappe.db.get_value("GRC Report Release",release.name,"report_context"),frozen)
  self.assertEqual(api.assessment(corrected["name"])["report"],json.loads(frozen))

 def test_evidence_ownership(self):
  first=self.make();other=self.make(ORG2,OTHER)
  frappe.set_user("Administrator")
  with sec.service_write():file=save_file("other-evidence.txt",b"Other org",other.doctype,other.name,is_private=1)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):svc.save(first.name,{"Q1":{"evidence":file.file_url}})
  with self.assertRaises(frappe.PermissionError):svc.save(first.name,{"Q1":{"evidence":"/files/public.pdf"}})

 def test_customer_code_cannot_authenticate_staff_or_erp(self):
  from ia_maturity.grc.auth import request_code
  frappe.set_user("Guest")
  for email in (AUDITOR,ERP):
   with patch("frappe.sendmail") as mail:
    request_code(email)
    mail.assert_not_called()
    self.assertFalse(frappe.db.exists("IA Maturity Registration",{"email":email,"status":"Pending"}))

 def test_invitation_is_bound_to_verified_email(self):
  from ia_maturity.grc.auth import digest
  from ia_maturity.grc.organizations import accept_invitation
  from frappe.utils import add_days,now_datetime
  frappe.set_user("Administrator")
  with sec.service_write():
   invite=frappe.get_doc(dict(doctype="GRC Invitation",entity=ORG,email=OTHER,membership_role="Viewer",
      token_hash=digest("test-token"),expires_on=add_days(now_datetime(),1),invited_by=CUSTOMER)).insert(ignore_permissions=True)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.ValidationError):accept_invitation("test-token")
  frappe.set_user(OTHER);accept_invitation("test-token")
  self.assertEqual(sec.membership(ORG),"Viewer")
  self.assertEqual(frappe.db.get_value("GRC Invitation",invite.name,"status"),"Accepted")
  with self.assertRaises(frappe.ValidationError):accept_invitation("test-token")

 def test_only_admin_can_change_customer_assignments(self):
  frappe.set_user(AUDITOR)
  with self.assertRaises(frappe.PermissionError):assign_customer(ORG,OUTSIDER)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):assign_customer(ORG,OUTSIDER)

 def test_customer_verification_single_use_and_no_organization_before_verify(self):
  from ia_maturity.grc.auth import request_code,consume
  from ia_maturity.grc.organizations import save_organization
  import re
  email="grc-test-new-verified@example.test"
  frappe.set_user("Guest")
  with patch("frappe.sendmail",return_value=self.sent_email) as mail:
   request_code(email,purpose="Start",full_name="Verified Customer",consent=1,organization_name="_Test Verified New Organization",organization_sector="Manufacturing")
  self.assertFalse(frappe.db.exists("User",email))
  self.assertFalse(frappe.db.exists("IA Maturity Entity","_Test Verified New Organization"))
  message=mail.call_args.kwargs["message"]
  code=re.search(r"letter-spacing:6px[^>]*>([0-9]{6})",message).group(1)
  registration=frappe.db.get_value("IA Maturity Registration",{"email":email,"status":"Pending"},"name")
  consume(registration,code=code)
  self.assertEqual(sec.account_type(email),"Customer")
  self.assertEqual(sec.entities(),["_Test Verified New Organization"])
  self.assertEqual(sec.membership("_Test Verified New Organization"),"Organization Admin")
  self.assertEqual(frappe.db.get_value("IA Maturity Entity","_Test Verified New Organization",["sector","contact_email"]),("Manufacturing",email))
  with self.assertRaises(frappe.ValidationError):consume(registration,code=code)

 def test_staff_requires_mfa_even_for_direct_login_as(self):
  from ia_maturity.grc.auth import enforce_staff_mfa
  with sec.service_write():
   doc=frappe.get_doc("User",AUDITOR);doc.grc_mfa_policy="Required";doc.save(ignore_permissions=True)
  with patch.object(frappe.local,"form_dict",frappe._dict(),create=True):
   with self.assertRaises(frappe.AuthenticationError):
    enforce_staff_mfa(SimpleNamespace(user=AUDITOR))

 def test_normal_erp_role_administration_is_preserved(self):
  frappe.set_user(ERP)
  user=frappe.get_doc("User",ERP)
  user.append("roles",{"role":"Accounts User"})
  user.save()
  self.assertEqual(sec.account_type(ERP),"ERP")

 def test_arabic_release_pdf_and_read_only_snapshot(self):
  doc=self.make(submit=False)
  svc.save(doc.name,{},language="ar");svc.submit(doc.name)
  self.assigned(doc);frappe.set_user(REVIEWER)
  svc.transition(doc.name,"start_review");svc.transition(doc.name,"approve");svc.transition(doc.name,"release")
  release=frappe.get_doc("GRC Report Release",{"assessment":doc.name})
  context=json.loads(release.report_context)
  self.assertEqual(release.language,"ar")
  self.assertEqual(context["lang"],"ar")
  self.assertEqual(context["dir"],"rtl")
  self.assertTrue(any("\u0600" <= c <= "\u06ff" or "\ufb50" <= c <= "\ufeff" for c in json.dumps(context,ensure_ascii=False)))
  content=frappe.get_doc("File",release.pdf_file).get_content()
  self.assertTrue(content.startswith(b"%PDF"));self.assertGreater(len(content),10000)
  # Admin writes cannot mutate a release through ordinary document APIs.
  frappe.set_user("Administrator")
  release.report_context="{}"
  with self.assertRaises(frappe.PermissionError):release.save()

 def test_contributor_assigned_action_without_other_assessment_access(self):
  doc=self.make(submit=True)
  frappe.set_user("Administrator")
  with sec.service_write():
   action=frappe.get_doc(dict(doctype="IA Maturity Action",assessment=doc.name,entity=ORG,
    finding_title="Assigned improvement",question_code="Q1",status="Open",
    assigned_to=CONTRIBUTOR,due_date="2026-12-01")).insert(ignore_permissions=True)
  frappe.set_user(CONTRIBUTOR)
  self.assertFalse(sec.can_read_assessment(doc))
  self.assertIn(action.name,[r.name for r in api.actions()["items"]])
  api.update_action(action.name,"Pending Verification",assigned_to=CONTRIBUTOR,
   due_date="2026-12-01",completion_notes="Implemented and ready for verification.")
  with self.assertRaises(frappe.ValidationError):
   api.update_action(action.name,"Completed",completion_notes="Self approval is denied.")
  frappe.set_user(OTHER)
  with self.assertRaises(frappe.PermissionError):api.update_action(action.name,"In Progress")
  frappe.set_user("Administrator")
  save_settings({"results_visibility":"Status only"})
  frappe.set_user(CONTRIBUTOR)
  self.assertNotIn(action.name,[r.name for r in api.actions()["items"]])

 def test_profile_policy_is_server_enforced_and_self_only(self):
  frappe.set_user("Administrator")
  save_settings({"profile_editable_fields": ["first_name", "phone", "language"]})
  frappe.set_user(CUSTOMER)
  original_other = frappe.db.get_value("User", OTHER, "first_name")
  result = api.save_profile({"first_name": "Updated name", "phone": "+49 123 456", "language": "ar"})
  self.assertEqual(result["values"]["first_name"], "Updated name")
  self.assertEqual(frappe.db.get_value("User", OTHER, "first_name"), original_other)
  for payload in ({"email": OTHER}, {"roles": [{"role": "System Manager"}]},
                  {"grc_account_type": "Auditor"}, {"user": OTHER}, {"mobile_no": "123"}):
   with self.assertRaises(frappe.PermissionError):api.save_profile(payload)
  with self.assertRaises(frappe.ValidationError):api.save_profile({"language": "unsupported"})
  with self.assertRaises(frappe.PermissionError):save_settings({"profile_editable_fields": ["mobile_no"]})
  frappe.set_user("Administrator")
  save_settings({"profile_editable_fields": []})
  frappe.set_user(CUSTOMER)
  self.assertEqual(api.profile()["editable_fields"], [])
  with self.assertRaises(frappe.PermissionError):api.save_profile({"first_name": "Blocked"})
  frappe.set_user(ERP)
  with self.assertRaises(frappe.PermissionError):api.profile()

 def test_profile_admin_policy_rejects_security_fields(self):
  for fields in (["email"], ["roles"], ["grc_account_type"], {"phone": True}, "not json"):
   with self.assertRaises((frappe.ValidationError, ValueError)):
    save_settings({"profile_editable_fields": fields})

 def test_dashboard_card_filters_match_counts_and_tenant_scope(self):
  from frappe.utils import add_days, today
  draft=self.make()
  submitted=self.make(submit=True)
  frappe.db.set_value("GRC Assessment Assignment", draft.grc_assignment, "due_date", add_days(today(), -2))
  frappe.set_user(CUSTOMER)
  all_rows=api.dashboard()
  progress=api.dashboard(group="in_progress")
  review=api.dashboard(group="awaiting_review")
  overdue=api.dashboard(group="overdue")
  self.assertEqual(progress["total"], sum(all_rows["counts"].get(s,0) for s in ("Draft", "In Progress")))
  self.assertEqual(review["total"], sum(all_rows["counts"].get(s,0) for s in ("Submitted", "Resubmitted", "Under Review")))
  self.assertEqual(overdue["total"], all_rows["overdue"])
  self.assertIn(draft.name,[a["name"] for a in progress["assessments"]])
  self.assertIn(submitted.name,[a["name"] for a in review["assessments"]])
  self.assertEqual(api.dashboard(group="released")["total"], all_rows["counts"].get("Report Released",0))
  frappe.set_user(OUTSIDER)
  self.assertNotIn(draft.name,[a["name"] for a in api.dashboard(group="overdue")["assessments"]])
  with self.assertRaises(frappe.ValidationError):api.dashboard(group="invalid")

 def test_staff_password_change_validates_confirmation_and_calls_core(self):
  frappe.set_user(AUDITOR)
  with self.assertRaises(frappe.ValidationError):api.change_password("", "new-password-long", "new-password-long")
  with self.assertRaises(frappe.ValidationError):api.change_password("old", "new-password-long", "different")
  with self.assertRaises(frappe.ValidationError):api.change_password("old", "short", "short")
  manager=SimpleNamespace(logout=lambda: frappe.set_user("Guest"))
  with patch.object(frappe.local, "login_manager", manager, create=True), patch("ia_maturity.grc.auth.reset_password") as reset:
   self.assertEqual(api.change_password("old-password", "new-password-long", "new-password-long"), {"redirect": "/login"})
   reset.assert_called_once_with("new-password-long", logout_all_sessions=1, old_password="old-password")
  self.assertEqual(frappe.session.user, "Guest")

 def test_legacy_pdf_has_no_dependency_on_site_host_or_print_assets(self):
  from ia_maturity import printing
  doc=self.make(submit=True)
  frappe.set_user("Administrator")
  with patch.dict(frappe.conf, {"grc_enabled":0,"host_name":"http://unreachable.invalid"}):
   for language in ("en","ar"):
    for fmt in sorted(printing.FORMATS):
     content=printing.render_pdf(doc,fmt,language)
     self.assertTrue(content.startswith(b"%PDF-"))
     self.assertGreater(len(content),10000)

 def test_standard_pdf_route_preserves_release_gating_and_record_permissions(self):
  from ia_maturity import printing
  doc=self.make(submit=True)
  with self.assertRaises(frappe.PermissionError):
   printing.download_pdf(doc.doctype,doc.name,format="IA Maturity Report")
  frappe.set_user(OTHER)
  with self.assertRaises(frappe.PermissionError):
   printing.download_pdf(doc.doctype,doc.name,format="IA Maturity Report")
  self.assigned(doc)
  frappe.set_user(REVIEWER)
  svc.transition(doc.name,"start_review");svc.transition(doc.name,"approve");svc.transition(doc.name,"release")
  frappe.set_user(CUSTOMER)
  printing.download_pdf(doc.doctype,doc.name,format="IA Maturity Report",doc='{"overall_score":100}')
  release=frappe.get_doc("GRC Report Release",{"assessment":doc.name})
  self.assertEqual(frappe.local.response.filecontent,frappe.get_doc("File",release.pdf_file).get_content())

 def test_app_pdf_rejects_external_resources_and_keeps_other_prints_on_core(self):
  from ia_maturity import printing
  doc=self.make(submit=True)
  frappe.set_user("Administrator")
  with patch.dict(frappe.conf,{"grc_enabled":0}),patch("frappe.render_template",return_value='<img src="https://external.invalid/logo.png">'):
   with self.assertRaises(frappe.ValidationError):
    printing.report_html(doc,"IA Maturity Report")
  with patch("frappe.call",return_value="core") as call:
   self.assertEqual(printing.download_pdf("Sales Invoice","test-invoice",format="Standard"),"core")
   self.assertEqual(call.call_args.kwargs["doctype"],"Sales Invoice")
   self.assertEqual(call.call_args.kwargs["name"],"test-invoice")

 def test_enabled_site_install_keeps_grc_homepage_without_touching_disabled_sites(self):
  from ia_maturity.grc.setup import setup
  with patch.dict(frappe.conf,{"grc_enabled":0}),patch("frappe.db.set_single_value") as write:
   setup()
   write.assert_not_called()
  setup()
  self.assertEqual(frappe.db.get_single_value("Website Settings","home_page"),"grc-site")

 def test_platform_administrator_is_erp_despite_effective_grc_roles(self):
  from ia_maturity.grc.auth import enforce_staff_mfa
  from ia_maturity.grc.routing import website_home
  frappe.set_user("Administrator")
  self.assertIn("GRC Auditor",frappe.get_roles())
  self.assertTrue(sec.is_admin())
  self.assertEqual(sec.account_type(),"ERP")
  self.assertEqual(sec.home(),desk_url("home"))
  self.assertEqual(api.bootstrap()["kind"],"ERP")
  self.assertEqual(api.bootstrap()["home"],desk_url("home"))
  self.assertIsNone(website_home("Administrator"))
  with patch.object(frappe.local,"request",SimpleNamespace(path="/"),create=True),patch.object(frappe.local,"form_dict",frappe._dict()):
   from werkzeug.exceptions import HTTPException
   with self.assertRaises(HTTPException) as caught:
    sec.guard_request()
   response=caught.exception.get_response()
   self.assertEqual(response.status_code,302)
   self.assertEqual(response.headers["Location"],desk_url("home"))
  with patch.object(frappe.local,"form_dict",frappe._dict(),create=True):
   enforce_staff_mfa(SimpleNamespace(user="Administrator"))
   with patch.object(frappe.local,"request",SimpleNamespace(path="/app"),create=True):
    sec.guard_request()

 def test_grc_app_admin_still_requires_staff_mfa_and_cannot_access_erp(self):
  from ia_maturity.grc.auth import enforce_staff_mfa
  with sec.service_write():
   doc=frappe.get_doc("User",APP_ADMIN);doc.grc_mfa_policy="Required";doc.save(ignore_permissions=True)
  frappe.set_user(APP_ADMIN)
  self.assertEqual(sec.account_type(),"Auditor")
  self.assertTrue(api.bootstrap()["is_admin"])
  self.assertEqual(api.bootstrap()["kind"],"Auditor")
  self.assertEqual(sec.home(),"/grc/auditor")
  with patch.object(frappe.local,"form_dict",frappe._dict(),create=True):
   with self.assertRaises(frappe.AuthenticationError):
    enforce_staff_mfa(SimpleNamespace(user=APP_ADMIN))
  self.assert_denied_request(APP_ADMIN,"/app")

 def test_name_fields_reject_passwords_and_owner_uses_current_identity(self):
  from frappe.utils.password import update_password
  from ia_maturity.grc.identity import display_name
  doc=self.make()
  update_password(CUSTOMER,"ActualPasswordName")
  with self.assertRaises(frappe.ValidationError):api.save_profile({"first_name":"ActualPasswordName"})
  with self.assertRaises(frappe.ValidationError):api.save_profile({"first_name":"Invalid!Name42"})
  frappe.db.set_value("User",CUSTOMER,{"first_name":"Invalid!Name42","full_name":"Invalid!Name42"})
  result=api.profile()
  self.assertEqual(result["values"]["first_name"],"")
  self.assertIn("first_name",result["name_repair_fields"])
  self.assertEqual(result["full_name"],CUSTOMER)
  self.assertEqual(api.bootstrap()["full_name"],CUSTOMER)
  api.save_profile({"first_name":"Correct","middle_name":"","last_name":"Customer"})
  self.assertEqual(display_name(CUSTOMER),"Correct Customer")
  self.assertEqual(api.assessment(doc.name)["respondent_name"],"Correct Customer")
  frappe.set_user(APP_ADMIN)
  self.assertEqual(api.assessment(doc.name)["report"]["respondent"],"Correct Customer")
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.ValidationError):
   api.change_password("ActualPasswordName","Correct Customer","Correct Customer")

 def test_customer_otp_only_denies_enrollment_and_preserves_native_storage(self):
  from ia_maturity.grc import mfa
  from frappe.twofactor import set_default,get_default
  from frappe.utils.password import encrypt
  import pyotp
  frappe.set_user(CUSTOMER)
  secret=encrypt(pyotp.random_base32())
  set_default(CUSTOMER+"_otpsecret",secret)
  set_default(CUSTOMER+"_otplogin",1)
  for password in ("incorrect","LocalMfaPassword123!"):
   with self.assertRaises(frappe.PermissionError):mfa.begin_authenticator(password)
  with self.assertRaises(frappe.PermissionError):mfa.confirm_authenticator("forged","123456")
  self.assertFalse(mfa.required())
  self.assertTrue(mfa.status()["customer_otp_only"])
  self.assertFalse(mfa.status()["can_enroll"])
  self.assertEqual(get_default(CUSTOMER+"_otpsecret"),secret)
  self.assertTrue(get_default(CUSTOMER+"_otplogin"))
  self.assert_denied_request(CUSTOMER,"/app")

 def test_customer_otp_replaces_legacy_password_mfa_without_direct_login_bypass(self):
  from ia_maturity.grc import mfa
  from ia_maturity.grc.auth import request_code,consume,enforce_staff_mfa
  frappe.db.set_value("User",CUSTOMER,"grc_mfa_policy","Required")
  frappe.clear_cache(user=CUSTOMER)
  with patch.object(frappe.local,"form_dict",frappe._dict(),create=True):
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(SimpleNamespace(user=CUSTOMER))
  frappe.set_user("Guest")
  with patch("frappe.sendmail",return_value=self.sent_email) as mail,patch("ia_maturity.grc.auth.limit"):
   request_code(CUSTOMER,purpose="Resume")
  code=re.search(r"letter-spacing:6px[^>]*>([0-9]{6})",mail.call_args.kwargs["message"]).group(1)
  name=frappe.db.get_value("IA Maturity Registration",{"email":CUSTOMER,"status":"Pending"},"name")
  result=consume(name,code=code)
  self.assertNotIn("requires_mfa",result)
  self.assertEqual(result["user"],CUSTOMER)
  self.assertEqual(frappe.session.user,CUSTOMER)
  self.assertFalse(mfa.required())
  self.assertEqual(frappe.db.get_value("IA Maturity Registration",name,"status"),"Verified")
  with self.assertRaises(frappe.ValidationError):consume(name,code=code)

 def test_authenticator_and_email_diagnostics_are_scoped(self):
  from ia_maturity.grc import mfa
  from ia_maturity.grc.email_health import email_diagnostics,error_category
  for user in ("Guest",ERP,AUDITOR):
   frappe.set_user(user)
   with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):mfa.begin_authenticator("ignored")
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):email_diagnostics()
  frappe.set_user("Administrator")
  result=email_diagnostics()
  self.assertIn("queue_counts",result)
  self.assertNotIn("password",result)
  self.assertEqual(error_category("SMTPAuthenticationError 535 redacted"),"SMTP authentication rejected")
  self.assertEqual(error_category("TLS certificate failed"),"SMTP TLS or certificate error")

 def test_signup_defaults_to_all_valid_emails_and_admin_controls_domains(self):
  from ia_maturity.grc.email_policy import check_email
  frappe.set_user(APP_ADMIN)
  save_settings({"signup_email_policy":"All valid emails","signup_allowed_domains":""})
  frappe.db.set_single_value("IA Maturity Settings","block_free_email_domains",1)
  frappe.db.set_single_value("IA Maturity Settings","allowed_domains","company.example")
  frappe.clear_cache(doctype="IA Maturity Settings")
  self.assertEqual(check_email("someone@gmail.com",new_account=True),"someone@gmail.com")
  for invalid in ("Administrator","two@example.com,three@example.com","Name <user@example.com>","x@example.com\nBcc:y@example.com"):
   with self.assertRaises(frappe.ValidationError):check_email(invalid,True)
  save_settings({"signup_email_policy":"Allowed domains only","signup_allowed_domains":"@EXAMPLE.TEST,example.test"})
  self.assertEqual(check_email("new@example.test",True),"new@example.test")
  for blocked in ("new@gmail.com","new@sub.example.test"):
   with self.assertRaises(frappe.ValidationError):check_email(blocked,True)
  self.assertEqual(check_email("existing@gmail.com"),"existing@gmail.com")
  with self.assertRaises(frappe.ValidationError):save_settings({"signup_allowed_domains":""})
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):save_settings({"signup_email_policy":"All valid emails"})

 def test_signup_uses_frappe_outgoing_mail_and_rechecks_policy_before_creation(self):
  from ia_maturity.grc.auth import request_code,consume
  frappe.set_user(APP_ADMIN);save_settings({"signup_email_policy":"All valid emails"})
  email="grc-test-new-policy@gmail.com"
  frappe.set_user("Guest")
  from unittest.mock import Mock
  queued=frappe._dict(status="Sent",reload=lambda:None,send=Mock())
  with patch("frappe.sendmail",return_value=queued) as send,patch("ia_maturity.grc.auth.limit"):
   request_code(email,purpose="Start",full_name="Policy Customer",consent=1,organization_name="_Test Signup Policy",organization_sector="Manufacturing")
  args=send.call_args.kwargs
  # Queued without Frappe's post-commit hook, then delivered inside the request (not by the scheduler).
  self.assertNotIn("sender",args);self.assertTrue(args["delayed"]);self.assertFalse(args["now"])
  queued.send.assert_called_once_with()
  self.assertEqual(args["recipients"],[email]);self.assertNotIn("smtp",args)
  import re
  code=re.search(r">([0-9]{6})</p>",args["message"]).group(1)
  registration=frappe.db.get_value("IA Maturity Registration",{"email":email,"status":"Pending"},"name")
  frappe.set_user(APP_ADMIN);save_settings({"signup_email_policy":"Allowed domains only","signup_allowed_domains":"example.test"})
  frappe.set_user("Guest")
  with self.assertRaises(frappe.ValidationError):consume(registration,code=code)
  self.assertFalse(frappe.db.exists("User",email))

 def test_email_report_requires_current_access_and_attaches_customer_pdf(self):
  from ia_maturity.grc.report_delivery import email_report
  doc=self.make(submit=True);self.assigned(doc)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):email_report(doc.name)
  frappe.set_user(REVIEWER)
  svc.transition(doc.name,"start_review");svc.transition(doc.name,"approve");svc.transition(doc.name,"release")
  for user in (OTHER,OUTSIDER):
   frappe.set_user(user)
   with self.assertRaises(frappe.PermissionError):email_report(doc.name)
  for user in (CUSTOMER,REVIEWER,APP_ADMIN):
   frappe.set_user(user)
   with patch("frappe.sendmail") as send,patch("ia_maturity.grc.auth.limit"):
    result=email_report(doc.name)
   self.assertTrue(result["queued"])
   args=send.call_args.kwargs
   self.assertEqual(args["recipients"],[CUSTOMER])
   self.assertEqual(len(args["attachments"]),1);self.assertNotIn("sender",args)
   self.assertTrue(args["attachments"][0]["fname"].endswith(".pdf"))
   self.assertTrue(args["attachments"][0]["fcontent"].startswith(b"%PDF"))
   self.assertNotIn("75",args["message"]);self.assertNotIn("overall_score",args["message"])
   self.assertIn("/assessments/"+doc.name,args["message"])
  frappe.set_user(APP_ADMIN);assign_customer(ORG,REVIEWER,"Reviewer",0)
  frappe.set_user(REVIEWER)
  with self.assertRaises(frappe.PermissionError):email_report(doc.name)
  with self.assertRaises(frappe.PermissionError):api.download_report(doc.name)

 def test_public_signup_cannot_create_user_before_verified_email(self):
  from ia_maturity.grc.auth import sign_up
  frappe.set_user("Guest")
  frappe.db.set_single_value("Website Settings","disable_signup",0)
  email="grc-test-unverified-public@example.test"
  with self.assertRaises(frappe.PermissionError):sign_up(email,"Unverified Customer","/grc/customer")
  with sec.service_write():
   doc=frappe.get_doc(dict(doctype="User",email=email,first_name="Unverified",send_welcome_email=0,
       roles=[{"role":"GRC Customer"}]))
   doc.flags.grc_verified_signup_email=email
   with self.assertRaises(frappe.PermissionError):doc.insert(ignore_permissions=True)
  self.assertFalse(frappe.db.exists("User",email))
  with patch("ia_maturity.grc.security.enabled",return_value=False),patch("frappe.core.doctype.user.user.sign_up",return_value=(1,"core")) as core:
   self.assertEqual(sign_up(email,"Unverified Customer","/"),(1,"core"))
   core.assert_called_once()

 def test_signup_link_creates_verified_account_once(self):
  from ia_maturity.grc.auth import request_code,verify_link
  import re
  email="grc-test-link-signup@example.test"
  frappe.set_user("Guest")
  with patch("frappe.sendmail",return_value=self.sent_email) as send,patch("ia_maturity.grc.auth.limit"):
   request_code(email,purpose="Start",full_name="Link Customer",consent=1,organization_name="_Test Signup Link",organization_sector="Manufacturing")
  link=re.search(r'verify=([^"]+)',send.call_args.kwargs["message"]).group(1)
  self.assertFalse(frappe.db.exists("User",email))
  with patch("ia_maturity.grc.auth.limit"):
   result=verify_link(link)
   self.assertEqual(result["user"],email)
   self.assertEqual(frappe.db.get_value("User",email,"grc_email_verified"),1)
   with self.assertRaises(frappe.ValidationError):verify_link(link)
  self.assertIsNone(frappe.flags.get("grc_verified_signup_email"))

 def test_admin_controls_staff_mfa_while_customer_access_remains_otp_only(self):
  from ia_maturity.grc.account_security import set_mfa_policy,MFA_ROLE
  from ia_maturity.grc.mfa import required,begin_authenticator
  from ia_maturity.grc.auth import enforce_staff_mfa
  from frappe.twofactor import two_factor_is_enabled_for_
  from frappe.utils.password import update_password
  import secrets
  password=secrets.token_urlsafe(24)
  update_password(APP_ADMIN,password)
  frappe.set_user(APP_ADMIN)
  with patch("frappe.sessions.clear_sessions") as clear,patch("ia_maturity.grc.auth.limit"):
   with self.assertRaises(frappe.AuthenticationError):set_mfa_policy(AUDITOR,"Disabled","incorrect")
   set_mfa_policy(AUDITOR,"Disabled",password)
   clear.assert_called_with(user=AUDITOR,keep_current=False,force=True)
   self.assertFalse(required(AUDITOR));self.assertFalse(two_factor_is_enabled_for_(AUDITOR))
   self.assertNotIn(MFA_ROLE,sec.roles(AUDITOR))
   with patch.object(frappe.local,"form_dict",frappe._dict(),create=True):
    enforce_staff_mfa(SimpleNamespace(user=AUDITOR))
   self.assert_denied_request(AUDITOR,"/app")
   frappe.set_user(APP_ADMIN)
   for policy in ("Required","Disabled"):
    with self.assertRaises(frappe.ValidationError):set_mfa_policy(CUSTOMER,policy,password)
   self.assertFalse(required(CUSTOMER))
   frappe.set_user(CUSTOMER)
   self.assertFalse(api.profile()["authenticator"]["can_enroll"])
   with self.assertRaises(frappe.PermissionError):begin_authenticator("anything")
   with self.assertRaises(frappe.PermissionError):api.save_profile({"grc_mfa_policy":"Required"})
   frappe.set_user(APP_ADMIN)
   set_mfa_policy(AUDITOR,"Default",password)
   self.assertFalse(required(AUDITOR));self.assertFalse(two_factor_is_enabled_for_(AUDITOR))

 def test_mfa_policy_is_admin_only_and_does_not_weaken_other_roles(self):
  from ia_maturity.grc.account_security import set_mfa_policy,security_accounts
  from frappe.utils.password import update_password
  import secrets
  password=secrets.token_urlsafe(24)
  update_password(APP_ADMIN,password)
  for user in (CUSTOMER,AUDITOR,ERP,"Guest"):
   frappe.set_user(user)
   with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):set_mfa_policy(CUSTOMER,"Disabled",password)
   with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):security_accounts()
  frappe.set_user(APP_ADMIN)
  with patch("ia_maturity.grc.auth.limit"):
   with self.assertRaises(frappe.PermissionError):set_mfa_policy(ERP,"Disabled",password)
   set_mfa_policy(APP_ADMIN,"Disabled",password)
   from ia_maturity.grc.mfa import required
   self.assertFalse(required(APP_ADMIN))
   set_mfa_policy(APP_ADMIN,"Required",password)
   frappe.db.set_value("Role","All","two_factor_auth",1)
   with self.assertRaises(frappe.ValidationError):set_mfa_policy(AUDITOR,"Disabled",password)
  self.assertEqual(frappe.db.get_value("Role","All","two_factor_auth"),1)
  self.assertTrue(all(row["kind"] in {"Customer","Auditor"} for row in security_accounts()["rows"]))


 def test_role_mfa_policy_and_individual_overrides(self):
  from ia_maturity.grc.account_security import set_role_mfa_policy, set_mfa_policy, security_role_policies, MFA_ROLE
  from ia_maturity.grc.mfa import required, begin_authenticator
  from frappe.utils.password import update_password
  import secrets
  password=secrets.token_urlsafe(24)
  update_password(APP_ADMIN,password)
  frappe.set_user(APP_ADMIN)
  with patch("frappe.sessions.clear_sessions") as clear, patch("ia_maturity.grc.auth.limit"):
   with self.assertRaises(frappe.AuthenticationError):set_role_mfa_policy("GRC Auditor","Disabled","wrong")
   self.assertFalse(required(AUDITOR))
   set_role_mfa_policy("GRC Auditor","Required",password)
   self.assertTrue(required(AUDITOR))
   result=set_role_mfa_policy("GRC Auditor","Disabled",password)
   self.assertGreaterEqual(result["affected"],1)
   self.assertFalse(required(AUDITOR));self.assertNotIn(MFA_ROLE,sec.roles(AUDITOR))
   clear.assert_any_call(user=AUDITOR,keep_current=False,force=True)
   set_mfa_policy(AUDITOR,"Required",password)
   self.assertTrue(required(AUDITOR))
   set_role_mfa_policy("GRC Auditor","Required",password)
   set_role_mfa_policy("GRC Reviewer","Disabled",password)
   from ia_maturity.grc.account_security import role_default
   self.assertEqual(role_default({"GRC Auditor","GRC Reviewer"}),"Required")
   set_mfa_policy(AUDITOR,"Disabled",password)
   self.assertFalse(required(AUDITOR))
   set_mfa_policy(AUDITOR,"Default",password)
   self.assertTrue(required(AUDITOR))
   set_role_mfa_policy("GRC App Admin","Disabled",password)
   self.assertFalse(required(APP_ADMIN))
   with self.assertRaises(frappe.ValidationError):set_role_mfa_policy("GRC Customer","Disabled",password)
   self.assertFalse(required(CUSTOMER))
   frappe.set_user(CUSTOMER)
   self.assertFalse(api.profile()["authenticator"]["can_enroll"])
   with self.assertRaises(frappe.PermissionError):begin_authenticator("anything")
   with self.assertRaises(frappe.PermissionError):security_role_policies()
   with self.assertRaises(frappe.PermissionError):set_role_mfa_policy("GRC Customer","Required",password)
   frappe.set_user(APP_ADMIN)
   self.assertNotIn("GRC Customer",{r["role"] for r in security_role_policies()})
   frappe.db.set_value("Role","All","two_factor_auth",1)
   self.assertFalse(required(CUSTOMER))
   self.assertTrue(required(AUDITOR))
   frappe.db.set_value("Role","All","two_factor_auth",0)
   for role in ("GRC App Admin","GRC Auditor","GRC Reviewer"):
    set_role_mfa_policy(role,"Default",password)
   self.assertFalse(required(APP_ADMIN));self.assertFalse(required(AUDITOR))


 def test_all_letter_password_names_are_masked_in_profiles_staff_and_login(self):
  from frappe.utils.password import update_password
  from frappe.auth import CookieManager
  from werkzeug.wrappers import Response
  from ia_maturity.grc.administration import staff
  password="AlphabeticSecretValue"
  update_password(AUDITOR,password)
  frappe.db.set_value("User",AUDITOR,{"first_name":password,"last_name":"","full_name":password})
  frappe.set_user(AUDITOR)
  self.assertEqual(api.profile()["values"]["first_name"],"")
  self.assertEqual(api.bootstrap()["full_name"],AUDITOR)
  response=Response(frappe.as_json({"message":"Logged In","full_name":password}),mimetype="application/json")
  manager=CookieManager()
  manager.set_cookie("full_name",password)
  with patch.object(frappe.local,"cookie_manager",manager,create=True):
   sec.after_request(response)
  self.assertEqual(response.get_json()["full_name"],AUDITOR)
  self.assertEqual(manager.cookies["full_name"]["value"],AUDITOR)
  frappe.set_user(APP_ADMIN)
  self.assertEqual(next(row for row in staff() if row.name==AUDITOR)["full_name"],AUDITOR)
  frappe.set_user(AUDITOR)
  api.save_profile({"first_name":"Correct","last_name":"Auditor"})
  self.assertEqual(api.profile()["full_name"],"Correct Auditor")

 def test_names_and_passwords_are_separate_on_direct_user_updates(self):
  from frappe.utils.password import update_password
  from ia_maturity.grc.identity import display_name
  update_password(CUSTOMER,"Secret Customer")
  for values in ({"first_name":"Secret Customer"},{"first_name":"Secret","last_name":"Customer"},
                 {"first_name":"Safe Person","new_password":"Safe Person"}):
   doc=frappe.get_doc("User",CUSTOMER);doc.update(values)
   with sec.service_write(),self.assertRaises(frappe.ValidationError):
    doc.save(ignore_permissions=True)
  frappe.db.set_value("User",CUSTOMER,{"first_name":"Secret","middle_name":"","last_name":"Customer"})
  self.assertEqual(display_name(CUSTOMER),CUSTOMER)
  frappe.set_user(CUSTOMER)
  self.assertEqual(api.profile()["values"]["first_name"],"")
  self.assertEqual(api.profile()["values"]["last_name"],"")

 def test_mfa_requires_valid_user_bound_unexpired_single_use_challenge(self):
  import pyotp
  from frappe.twofactor import cache_2fa_data,set_default
  from frappe.utils.password import update_password,encrypt
  from ia_maturity.grc.auth import enforce_staff_mfa
  with sec.service_write():
   doc=frappe.get_doc("User",AUDITOR);doc.grc_mfa_policy="Required";doc.save(ignore_permissions=True)
  password="TestChallengePassword123!"
  update_password(AUDITOR,password)
  secret=pyotp.random_base32()
  set_default(AUDITOR+"_otpsecret",encrypt(secret))
  tmp_id=frappe.generate_hash(length=8)
  manager=SimpleNamespace(user=AUDITOR)
  # Proof validation scenarios are independent of the separate challenge rate-limit test.
  with patch.object(frappe.local,"form_dict",frappe._dict(pwd=password,tmp_id=tmp_id,otp=pyotp.TOTP(secret).now()),create=True),patch("ia_maturity.grc.auth.limit"):
   # Fabricated fields and recovery flags never authorize login.
   with patch.dict(frappe.flags,{"grc_password_recovery":True}):
    with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   cache_2fa_data(OTHER,0,secret,tmp_id)
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   cache_2fa_data(AUDITOR,0,secret,tmp_id)
   frappe.form_dict.otp="abcdef"
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   code=pyotp.TOTP(secret).now()
   frappe.form_dict.otp=("0" if code[0]!="0" else "1")+code[1:]
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   frappe.form_dict.otp=pyotp.TOTP(secret).now()
   # Expire the cached secret in both Frappe storage styles.
   frappe.cache.delete(tmp_id+"_otp_secret");frappe.cache.delete_value(tmp_id+"_otp_secret")
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   cache_2fa_data(AUDITOR,0,secret,tmp_id)
   with patch("ia_maturity.grc.mfa.configured",return_value=False):
    with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)
   enforce_staff_mfa(manager)
   from ia_maturity.grc.mfa import frappe_2fa_value
   for suffix in ("_usr","_pwd","_otp_secret","_token"):
    # Checks both Frappe storage styles: raw keys (older) and set_value (current v15/v16).
    self.assertIsNone(frappe_2fa_value(tmp_id,suffix))
   with self.assertRaises(frappe.AuthenticationError):enforce_staff_mfa(manager)

 def test_password_reset_checks_names_and_never_creates_a_grc_session(self):
  import secrets
  from urllib.parse import urlparse,parse_qs
  from unittest.mock import MagicMock
  from ia_maturity.grc.auth import reset_password
  from ia_maturity.grc.identity import matches_password
  doc=frappe.get_doc("User",AUDITOR)
  key=parse_qs(urlparse(doc._reset_password(send_email=False)).query)["key"][0]
  frappe.set_user("Guest")
  manager=MagicMock()
  with patch.object(frappe.local,"login_manager",manager,create=True):
   with self.assertRaises(frappe.ValidationError):reset_password(doc.first_name,key=key)
   password=secrets.token_urlsafe(24)
   self.assertEqual(reset_password(password,key=key),"/login")
   self.assertTrue(matches_password(AUDITOR,password))
   manager.login_as.assert_not_called()
   manager.make_session.assert_not_called()
   manager.logout.assert_not_called()
   self.assertEqual(frappe.session.user,"Guest")
   reset_password(secrets.token_urlsafe(24),key=key)
   self.assertEqual(frappe.response.http_status_code,410)
   self.assertTrue(matches_password(AUDITOR,password))

 def test_erp_password_recovery_still_uses_native_flow(self):
  from ia_maturity.grc.auth import reset_password
  from frappe.core.doctype.user import user as core
  with patch.object(core,"_get_user_for_update_password",return_value=frappe._dict(user=ERP)),patch.object(core,"update_password",return_value="/app") as native:
   self.assertEqual(reset_password("new-password",key="example-test-key"),"/app")
   native.assert_called_once_with("new-password",0,"example-test-key",None)


 def test_mfa_session_proof_cannot_be_supplied_by_client_or_api_token(self):
  from unittest.mock import MagicMock
  from ia_maturity.grc.mfa import require_verified_session,stamp_session
  with sec.service_write():
   doc=frappe.get_doc("User",AUDITOR);doc.grc_mfa_policy="Required";doc.save(ignore_permissions=True)
  frappe.set_user(AUDITOR)
  manager=MagicMock(user=AUDITOR)
  session=frappe._dict(user=AUDITOR,sid="test-session-proof",data=frappe._dict())
  with patch.object(frappe.local,"session",session),patch.object(frappe.local,"login_manager",manager,create=True),patch.object(frappe.local,"request",SimpleNamespace(path="/api/method/ia_maturity.grc.api.organizations"),create=True),patch("frappe.get_request_header",return_value=None),patch.object(frappe.local,"form_dict",frappe._dict(grc_validated_mfa_user=AUDITOR),create=True):
   with self.assertRaises(frappe.AuthenticationError):require_verified_session()
   manager.logout.assert_called_once()
   session.data.grc_validated_mfa_user=AUDITOR
   require_verified_session()
   with patch("frappe.get_request_header",return_value="token placeholder"):
    with self.assertRaises(frappe.AuthenticationError):require_verified_session()
   session.data.grc_validated_mfa_user=OTHER
   with self.assertRaises(frappe.AuthenticationError):require_verified_session()
   with patch.dict(frappe.flags,{"grc_validated_mfa_user":None}):
    with self.assertRaises(frappe.AuthenticationError):stamp_session(manager)
   with patch.dict(frappe.flags,{"grc_validated_mfa_user":AUDITOR}),patch.object(frappe.local,"session_obj",MagicMock(),create=True) as obj:
    stamp_session(manager)
    obj.update.assert_called_once_with(force=True)
    self.assertEqual(session.data.grc_validated_mfa_user,AUDITOR)
    self.assertIsNone(frappe.flags.get("grc_validated_mfa_user"))


 def test_signup_company_is_required_sector_optional_and_server_validated(self):
  from ia_maturity.grc.auth import request_code
  email="grc-test-signup-validation@example.test"
  frappe.set_user("Guest")
  with patch("frappe.sendmail",return_value=self.sent_email) as send,patch("ia_maturity.grc.auth.limit"),patch("ia_maturity.grc.auth.code_request_limit") as quota:
   for title,sector in [(None,"Manufacturing"),("","Manufacturing"),("X"*141,"Manufacturing"),("Bad\nName","Manufacturing"),("Valid","Unknown")]:
    with self.assertRaises(frappe.ValidationError):
     request_code(email,purpose="Start",full_name="New Customer",consent=1,organization_name=title,organization_sector=sector)
   send.assert_not_called();quota.assert_not_called()
   request_code(email,purpose="Start",full_name="New Customer",consent=1,organization_name="Valid",organization_sector=None)
   self.assertEqual(send.call_args.kwargs["recipients"],[email])
  self.assertFalse(frappe.db.exists("User",email))
  self.assertEqual(frappe.db.get_value("IA Maturity Registration",{"email":email,"status":"Pending"},"grc_organization_sector"),"")

 def test_signup_does_not_claim_existing_organizations_or_skip_invitations(self):
  from ia_maturity.grc.auth import request_code,consume
  from frappe.utils import add_to_date,now_datetime
  import re
  for suffix,title,invited in [("existing",ORG,False),("invited","_Test Invitation Signup",True)]:
   email="grc-test-signup-"+suffix+"@example.test"
   frappe.set_user("Administrator")
   if invited:
    with sec.service_write():
     frappe.get_doc(dict(doctype="GRC Invitation",entity=ORG,email=email,membership_role="Contributor",
      invited_by=APP_ADMIN,token_hash="test-signup-invitation",expires_on=add_to_date(now_datetime(),days=1))).insert(ignore_permissions=True)
   frappe.set_user("Guest")
   with patch("frappe.sendmail",return_value=self.sent_email) as send,patch("ia_maturity.grc.auth.limit"):
    request_code(email,purpose="Start",full_name="New Customer",consent=1,organization_name=title,organization_sector="Manufacturing")
   code=re.search(r">([0-9]{6})</p>",send.call_args.kwargs["message"]).group(1)
   registration=frappe.db.get_value("IA Maturity Registration",{"email":email,"status":"Pending"},"name")
   consume(registration,code=code)
   self.assertEqual(sec.entities(),[])
   self.assertEqual(api.bootstrap()["signup_organization"],{"entity_name":title,"sector":"Manufacturing"})
   with self.assertRaises(frappe.PermissionError):api.organization_detail(ORG)
   if invited:self.assertFalse(frappe.db.exists("IA Maturity Entity",title))

 def test_signup_for_existing_customer_never_rewrites_organization(self):
  from ia_maturity.grc.auth import request_code,consume
  import re
  before=frappe.db.get_value("IA Maturity Entity",ORG,["sector","contact_email"])
  frappe.set_user("Guest")
  with patch("frappe.sendmail",return_value=self.sent_email) as send,patch("ia_maturity.grc.auth.limit"):
   request_code(CUSTOMER,purpose="Start",full_name="Existing Customer",consent=1,
    organization_name="_Test Unwanted Organization",organization_sector="Healthcare")
  code=re.search(r">([0-9]{6})</p>",send.call_args.kwargs["message"]).group(1)
  name=frappe.db.get_value("IA Maturity Registration",{"email":CUSTOMER,"status":"Pending"},"name")
  consume(name,code=code)
  self.assertEqual(sec.entities(),[ORG])
  self.assertEqual(frappe.db.get_value("IA Maturity Entity",ORG,["sector","contact_email"]),before)
  self.assertFalse(frappe.db.exists("IA Maturity Entity","_Test Unwanted Organization"))

 def test_pre_upgrade_verification_keeps_manual_organization_onboarding(self):
  from ia_maturity.grc.auth import consume,digest
  from frappe.utils import add_to_date,now_datetime,today
  from uuid import uuid4
  email="grc-test-legacy-pending-"+uuid4().hex+"@example.test"
  frappe.set_user("Guest")
  # Genuine pre-upgrade pending registration: new signup can no longer omit company.
  reg=frappe.get_doc(dict(doctype="IA Maturity Registration",email=email,full_name="Legacy Customer",
   entity_name="Pending organization setup",grc_organization_signup=0,grc_organization_sector="",
   purpose="Start",language="en",consent=1,assessment_date=today(),status="Pending",
   code_hash=digest("123456"),link_key_hash=digest("legacy-fixture"),expires_on=add_to_date(now_datetime(),minutes=15))).insert(ignore_permissions=True)
  consume(reg.name,code="123456")
  self.assertEqual(sec.account_type(),"Customer")
  self.assertEqual(sec.entities(),[])
  self.assertFalse(frappe.db.exists("IA Maturity Entity","Pending organization setup"))

 def test_requirement_neutral_signup_and_server_cooldown(self):
  from ia_maturity.grc.auth import request_code, digest
  frappe.set_user("Guest")
  results=[]
  for email in (CUSTOMER,AUDITOR,"grc-test-unknown-r1@example.test"):
   frappe.cache.delete(f"grc:{frappe.local.site}:request-cooldown:{digest(email)}")
   frappe.cache.delete(f"grc:{frappe.local.site}:request-email:{digest(email)}")
   with patch("frappe.sendmail",return_value=self.sent_email) as send:
    results.append(request_code(email))
   self.assertEqual(send.called,email==CUSTOMER)
   with self.assertRaises(frappe.RateLimitExceededError):
    request_code(email)
  self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
  self.assertEqual(results[0]["resend_after_seconds"],60)
  self.assertEqual(results[0]["expires_in_seconds"],900)

 def test_requirement_delivery_failure_clear_feedback(self):
  from ia_maturity.grc.auth import request_code
  frappe.set_user("Guest")
  with patch("ia_maturity.grc.auth.limit"),patch("frappe.sendmail",side_effect=RuntimeError("SMTP unavailable")):
   with patch.object(frappe.db,"commit"),self.assertRaisesRegex(frappe.OutgoingEmailError,"could not be sent"):
    request_code(CUSTOMER)

 def test_requirement_multiple_memberships_and_holding_read_only(self):
  doc=self.make(ORG2,OTHER)
  frappe.set_user("Administrator")
  api.save_organization({"parent_organization":ORG},name=ORG2)
  frappe.set_user(CUSTOMER)
  self.assertIn(ORG2,sec.entities())
  self.assertFalse(api.assessment(doc.name)["editable"])
  self.assertIn(doc.name,[a["name"] for a in api.dashboard(entity=ORG2)["assessments"]])
  self.assertIn(doc.name,[a.name for a in frappe.get_list(svc.DOCTYPE)])
  with self.assertRaises(frappe.PermissionError):svc.save(doc.name,{})
  with self.assertRaises(frappe.PermissionError):api.save_organization({"notes":"unauthorized"},name=ORG2)
  with sec.service_write():
   frappe.get_doc(dict(doctype="GRC Organization Membership",entity=ORG2,user=CUSTOMER,
    membership_role="Contributor",active=1)).insert(ignore_permissions=True)
  self.assertFalse(api.assessment(doc.name)["editable"])
  self.assertIn(doc.name,[a["name"] for a in api.dashboard(entity=ORG2)["assessments"]])
  member=frappe.db.get_value("GRC Organization Membership",{"entity":ORG2,"user":CUSTOMER},"name")
  frappe.set_user(OTHER);api.update_membership(member,"Organization Admin",1)
  frappe.set_user(CUSTOMER);self.assertTrue(api.assessment(doc.name)["editable"])

 def test_requirement_holding_cycles_and_revocation(self):
  doc=self.make(ORG2,OTHER)
  frappe.set_user("Administrator");api.save_organization({"parent_organization":ORG},name=ORG2)
  with self.assertRaises(frappe.ValidationError):api.save_organization({"parent_organization":ORG2},name=ORG)
  # Validate failed cyclic save did not persist.
  self.assertFalse(frappe.db.get_value("IA Maturity Entity",ORG,"parent_organization"))
  frappe.set_user(CUSTOMER);self.assertTrue(sec.can_read_assessment(doc))
  frappe.set_user("Administrator")
  member=frappe.db.get_value("GRC Organization Membership",{"entity":ORG,"user":CUSTOMER},"name")
  with sec.service_write():
   m=frappe.get_doc("GRC Organization Membership",member);m.active=0;m.save(ignore_permissions=True)
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):api.assessment(doc.name)

 def test_requirement_consultant_entry_and_history(self):
  doc=self.make();self.assigned(doc)
  frappe.set_user(REVIEWER)
  with self.assertRaises(frappe.PermissionError):svc.save(doc.name,{})
  frappe.set_user(AUDITOR)
  svc.save(doc.name,{"Q1":{"selected_option":"B","comment":"Entered on behalf"}})
  events=api.activity(assignment=doc.grc_assignment)
  event=next(r for r in events if r.action=="Answers changed" and r.actor==AUDITOR)
  self.assertIn("Entered on behalf",event.details)
  frappe.set_user(CUSTOMER)
  event=next(r for r in api.activity(assignment=doc.grc_assignment) if r.name==event.name)
  self.assertEqual(json.loads(event.details),{"questions":["Q1"]})
  self.assertNotIn("Entered on behalf",event.details)
  frappe.set_user(OUTSIDER)
  with self.assertRaises(frappe.PermissionError):svc.save(doc.name,{})

 def test_requirement_staff_creates_customer_and_pending_draft(self):
  frappe.set_user(AUDITOR)
  org=api.save_organization({"entity_name":"_Test GRC staff prepared","sector":"Healthcare"})
  self.assertTrue(org["can_manage"])
  doc=svc.new_assessment(org["name"],SEED_TEMPLATE)
  self.assertTrue(api.assessment(doc.name)["customer_pending"])
  self.assertTrue(api.assessment(doc.name)["editable"])
  with self.assertRaisesRegex(frappe.ValidationError,"Invite a customer"):
   svc.submit(doc.name)
  with patch("frappe.sendmail",return_value=[1]) as send:
   api.invite_member(org["name"],OTHER,"Organization Admin")
  import re
  token=re.search(r"invitation=([^\"]+)",send.call_args.kwargs["message"]).group(1)
  frappe.set_user(OTHER);api.accept_invitation(token)
  result=api.assessment(doc.name)
  self.assertFalse(result["customer_pending"]);self.assertEqual(result["respondent"],OTHER)
  self.assertTrue(result["editable"])

 def test_requirement_transfer_reason_and_previous_owner_revocation(self):
  doc=self.make();self.assigned(doc)
  frappe.set_user("Administrator");assign_customer(ORG,OUTSIDER,"Consultant")
  frappe.set_user(AUDITOR)
  with self.assertRaisesRegex(frappe.ValidationError,"reason"):
   assign_assessment(doc.grc_assignment,consultant=OUTSIDER,reviewer=REVIEWER)
  assign_assessment(doc.grc_assignment,consultant=OUTSIDER,reviewer=REVIEWER,reason="Customer requested handover")
  with self.assertRaises(frappe.PermissionError):svc.save(doc.name,{})
  event=next(r for r in api.activity(assignment=doc.grc_assignment) if r.action=="Assessment transferred")
  detail=json.loads(event.details)
  self.assertEqual(detail["before"]["consultant"],AUDITOR)
  self.assertEqual(detail["after"]["consultant"],OUTSIDER)
  self.assertEqual(detail["reason"],"Customer requested handover")
  frappe.set_user(CUSTOMER)
  self.assertNotIn("Assessment transferred",[r.action for r in api.activity(assignment=doc.grc_assignment)])
  frappe.set_user(OUTSIDER);svc.save(doc.name,{"Q2":{"selected_option":"B"}})

 def test_requirement_notification_preference_matrix(self):
  from ia_maturity.grc.preferences import optional_allowed
  from ia_maturity.grc.notifications import queue
  for org,user,allowed in ((1,1,True),(0,1,False),(1,0,False),(0,0,False)):
   frappe.db.set_value("IA Maturity Entity",ORG,"grc_optional_reminders",org)
   frappe.db.set_value("User",CUSTOMER,"grc_optional_reminders",user)
   self.assertEqual(optional_allowed(ORG,CUSTOMER,"Reminder"),allowed)
   self.assertTrue(optional_allowed(ORG,CUSTOMER,"Clarification"))
  frappe.db.set_value("User",CUSTOMER,"grc_email_notifications",0)
  with patch("frappe.sendmail",return_value=[1]) as send:
   queue(ORG,"test",CUSTOMER,"Clarification Required","test-mandatory-r6",kind="Clarification")
   self.assertEqual(send.call_count,1)
   queue(ORG,"test",CUSTOMER,"Submitted","test-optional-r6",kind="Status")
   self.assertEqual(send.call_count,1)

 def test_requirement_timeline_internal_comment_hidden(self):
  doc=self.make(submit=True);self.assigned(doc)
  frappe.set_user(REVIEWER);svc.transition(doc.name,"start_review")
  svc.transition(doc.name,"approve","Sensitive internal review comment")
  staff=api.activity(assignment=doc.grc_assignment)
  self.assertIn("Sensitive internal review comment",frappe.as_json(staff))
  frappe.set_user(CUSTOMER)
  self.assertNotIn("Sensitive internal review comment",frappe.as_json(api.activity(assignment=doc.grc_assignment)))

 def test_requirement_evidence_delete_audited_and_scoped(self):
  doc=self.make()
  with sec.service_write():
   file=save_file("requirement-evidence-delete.txt",b"test deletion",doc.doctype,doc.name,is_private=1)
  svc.save(doc.name,{"Q1":{"evidence":file.file_url}})
  frappe.set_user(OTHER)
  with self.assertRaises(frappe.PermissionError):api.delete_evidence(doc.name,file.file_url)
  frappe.set_user(CUSTOMER);api.delete_evidence(doc.name,file.file_url)
  self.assertFalse(frappe.db.exists("File",file.name))
  self.assertIn("Evidence deleted",[r.action for r in api.activity(assignment=doc.grc_assignment)])

 def test_user_without_grc_roles_opens_erp_home(self):
  from ia_maturity.grc.routing import website_home
  desk="grc-test-desk-plain@example.test"
  respondent="grc-test-respondent-only@example.test"
  with sec.service_write():
   for email,roles in ((desk,["System Manager","IA Assessment Respondent"]),(respondent,["IA Assessment Respondent"])):
    if frappe.db.exists("User",email):
     frappe.delete_doc("User",email,force=True)
    frappe.get_doc(dict(doctype="User",email=email,first_name="Plain",send_welcome_email=0,
     user_type="Website User",roles=[{"role":role} for role in roles])).insert(ignore_permissions=True)
  desk_user=frappe.get_doc("User",desk)
  self.assertEqual(desk_user.grc_account_type,"")
  self.assertEqual(desk_user.user_type,"System User")
  self.assertEqual(sec.account_type(desk),"ERP")
  self.assertEqual(sec.home(desk),desk_url("home"))
  self.assertIsNone(website_home(desk))
  self.assertEqual(sec.account_type(respondent),"ERP")
  self.assertNotEqual(sec.home(respondent),"/login?access=inactive")
  frappe.set_user(respondent)
  for path in ("/app/home","/app","/api/resource/Sales Invoice"):
   with patch.object(frappe.local,"request",SimpleNamespace(path=path),create=True),patch.object(frappe.local,"form_dict",frappe._dict()):
    sec.guard_request()
  self.assertEqual(frappe.db.get_value("User",respondent,"user_type"),"System User")
  self.assertEqual(sec.home(respondent),desk_url("home"))
  self.assert_denied_request(CUSTOMER,"/app/home")

 def test_no_grc_roles_preserve_erp_access_despite_stale_classification(self):
  frappe.db.set_value("User",ERP,"grc_account_type","Customer")
  self.assertEqual(sec.account_type(ERP),"ERP")
  frappe.set_user(ERP)
  for path in ("/app/home","/app","/api/resource/Sales Invoice"):
   with patch.object(frappe.local,"request",SimpleNamespace(path=path),create=True),patch.object(frappe.local,"form_dict",frappe._dict()):
    sec.guard_request()
  with patch("frappe.apps.get_default_path",return_value="/app/home"):
   self.assertEqual(api.bootstrap(),{"enabled":True,"kind":"ERP","home":desk_url("home")})
  # A normal ERP System Manager can still administer ERP roles with a stale flag.
  user=frappe.get_doc("User",ERP);user.add_roles("Accounts User")
  self.assertEqual(user.grc_account_type,"")
  self.assertEqual(user.user_type,"System User")
  frappe.set_user(CUSTOMER)
  self.assertEqual(frappe.db.get_value("User",CUSTOMER,"user_type"),"Website User")
  self.assert_denied_request(CUSTOMER,"/app/grc-staff")
  self.assert_denied_request(CUSTOMER,"/desk/grc-staff")

 def test_legacy_staff_desk_redirects_to_custom_workspace_without_erp_access(self):
  from ia_maturity.grc.desk import boot_session
  frappe.set_user(AUDITOR)
  # v15 bookmarks use /app, v16 bookmarks use /desk; both must redirect, not 403.
  for bookmark in ("/app/grc-staff","/desk/grc-staff"):
   with self.subTest(bookmark=bookmark),patch("ia_maturity.grc.mfa.require_verified_session"),patch.object(frappe.local,"request",SimpleNamespace(path=bookmark),create=True),patch.object(frappe.local,"form_dict",frappe._dict()):
    from werkzeug.exceptions import HTTPException
    with self.assertRaises(HTTPException) as caught:
     sec.guard_request()
    response=caught.exception.get_response()
    self.assertEqual(response.status_code,302)
    self.assertEqual(response.headers["Location"],"/grc/auditor")
   self.assertEqual(response.headers["Cache-Control"],"no-store")
  self.assert_denied_request(AUDITOR,"/app/sales-invoice")
  self.assert_denied_request(AUDITOR,"/api/method/frappe.desk.desk_page.getpage",cmd="frappe.desk.desk_page.getpage")
  boot=frappe._dict(user={"can_read":["Sales Invoice"]},user_info={OTHER:{}},page_info={"grc-staff":{},"permission-manager":{}})
  boot_session(boot)
  self.assertEqual(boot.home_page,"grc-staff");self.assertEqual(boot.user["can_read"],[])
  self.assertNotIn(OTHER,boot.user_info)

 def test_requirement_erp_cannot_read_private_grc_evidence(self):
  doc=self.make()
  with sec.service_write():
   file=save_file("requirement-erp-boundary.txt",b"private",doc.doctype,doc.name,is_private=1)
  self.assertFalse(sec.file_permission(file,"read",ERP))
  self.assertTrue(sec.file_permission(file,"read",CUSTOMER))
  frappe.set_user("Administrator");api.save_organization({"parent_organization":ORG},name=ORG2)
  other_doc=self.make(ORG2,OTHER)
  with sec.service_write():
   other_file=save_file("requirement-holding-read.txt",b"holding read",other_doc.doctype,other_doc.name,is_private=1)
  self.assertTrue(sec.file_permission(other_file,"read",CUSTOMER))
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):api.delete_evidence(other_doc.name,other_file.file_url)

 def test_requirement_action_attachment_delete_has_timeline(self):
  doc=self.make(submit=True)
  action=frappe.get_all("IA Maturity Action",filters={"assessment":doc.name},pluck="name")
  if not action:
   # C answers do not create actions under every published policy.
   with sec.service_write():
    a=frappe.get_doc(dict(doctype="IA Maturity Action",entity=ORG,assessment=doc.name,
     question_code="Q1",finding_title="Evidence deletion test",status="Open")).insert(ignore_permissions=True)
  else:
   a=frappe.get_doc("IA Maturity Action",action[0])
  with sec.service_write():
   file=save_file("requirement-action-evidence.txt",b"action private",a.doctype,a.name,is_private=1)
   a.evidence=file.file_url;a.save(ignore_permissions=True)
  api.delete_evidence(a.name,file.file_url,doctype=a.doctype)
  self.assertFalse(frappe.db.exists("File",file.name))
  event=next(r for r in api.activity(assignment=doc.grc_assignment) if r.action=="Evidence deleted")
  self.assertEqual(json.loads(event.details)["filename"],file.file_name)

 def test_requirement_optional_status_and_legacy_optout(self):
  from ia_maturity.grc.preferences import optional_allowed
  for org,user,legacy,allowed in ((1,1,1,True),(0,1,1,False),(1,0,1,False),(1,1,0,False)):
   frappe.db.set_value("IA Maturity Entity",ORG,"grc_optional_status_updates",org)
   frappe.db.set_value("User",CUSTOMER,{"grc_optional_status_updates":user,"grc_email_notifications":legacy})
   self.assertEqual(optional_allowed(ORG,CUSTOMER,"Status"),allowed)
   self.assertTrue(optional_allowed(ORG,CUSTOMER,"Clarification"))

 def test_requirement_descendant_scope_is_transitive(self):
  frappe.set_user("Administrator")
  api.save_organization({"parent_organization":ORG},name=ORG2)
  child=api.save_organization({"entity_name":"_Test GRC Subsidiary Three","parent_organization":ORG2})
  frappe.set_user(CUSTOMER)
  self.assertIn(child["name"],sec.entities())
  self.assertEqual(sec.effective_membership(child["name"]),"Holding Viewer")
  with self.assertRaises(frappe.PermissionError):api.invite_member(child["name"],OTHER)
  with self.assertRaises(frappe.PermissionError):svc.new_assessment(child["name"],SEED_TEMPLATE)

 def test_requirement_customer_timeline_timestamps_have_offset(self):
  doc=self.make()
  activity=api.activity(assignment=doc.grc_assignment)
  self.assertTrue(activity)
  self.assertRegex(activity[0].creation,r"[+-][0-9]{2}:[0-9]{2}$")

 def test_requirement_manager_is_scoped_without_global_administration(self):
  frappe.set_user("Administrator")
  email="grc-test-scoped-manager@example.test"
  if not frappe.db.exists("User",email):
   with sec.service_write():
    frappe.get_doc(dict(doctype="User",email=email,first_name="Scoped Manager",
     send_welcome_email=0,roles=[{"role":"GRC Manager"}])).insert(ignore_permissions=True)
  # Organization-manager responsibility is narrower than department-manager
  # queue access. This fixture deliberately has no department-wide authority.
  departments.save_department_staff(email,"Internal Audit","Consultant")
  frappe.set_user(email)
  self.assertFalse(sec.is_admin())
  with self.assertRaises(frappe.PermissionError):api.settings()
  with self.assertRaises(frappe.PermissionError):api.organization_detail(ORG)
  org=api.save_organization({"entity_name":"_Test GRC Managed Organization"})
  self.assertTrue(org["can_manage"])
  self.assertTrue(sec.is_organization_manager(org["name"]))
  doc=svc.new_assessment(org["name"],SEED_TEMPLATE)
  self.assertTrue(api.assessment(doc.name)["editable"])
  assign_customer(org["name"],AUDITOR,"Consultant")
  with self.assertRaises(frappe.PermissionError):assign_customer(ORG,AUDITOR,"Consultant")
  with self.assertRaises(frappe.PermissionError):assign_customer(org["name"],OUTSIDER,"Manager")
  with self.assertRaises(frappe.PermissionError):api.save_staff("new@example.test","New Staff")

 def test_requirement_action_list_and_report_metadata_obey_owner_scope(self):
  other=self.make(submit=True)
  own=self.make(owner=CONTRIBUTOR,submit=True)
  with sec.service_write():
   foreign=frappe.get_doc(dict(doctype="IA Maturity Action",entity=ORG,assessment=other.name,
    question_code="Q1",finding_title="Other respondent action",status="Open")).insert(ignore_permissions=True)
   mine=frappe.get_doc(dict(doctype="IA Maturity Action",entity=ORG,assessment=own.name,
    question_code="Q1",finding_title="Own action",status="Open")).insert(ignore_permissions=True)
  visible={r.name for r in frappe.get_list("IA Maturity Action")}
  self.assertIn(mine.name,visible);self.assertNotIn(foreign.name,visible)
  release=frappe._dict(doctype="GRC Report Release",entity=ORG,assessment=other.name)
  self.assertFalse(sec.has_permission(release,"read",CONTRIBUTOR))
  with sec.service_write():
   foreign.assigned_to=CONTRIBUTOR;foreign.save(ignore_permissions=True)
  self.assertIn(foreign.name,{r.name for r in frappe.get_list("IA Maturity Action")})
  frappe.set_user("Administrator");save_settings({"results_visibility":"Status only"})
  frappe.set_user(CONTRIBUTOR)
  self.assertNotIn(mine.name,{r.name for r in frappe.get_list("IA Maturity Action")})

 def test_question_extras_default_policy_enforced_on_existing_draft(self):
  doc=self.make()
  frappe.set_user("Administrator")
  save_settings({"question_extras_enabled":0,"expand_maturity":0,"expand_report":0})
  frappe.set_user(CUSTOMER)
  payload=api.assessment(doc.name)
  self.assertFalse(payload["expand_maturity"])
  self.assertFalse(payload["expand_report"])
  self.assertTrue(all(not q["allow_comment"] and not q["allow_attachment"] for q in payload["questions"]))
  code=doc.answers[0].question_code
  with self.assertRaises(frappe.ValidationError):svc.save(doc.name,{code:{"comment":"Injected comment"}})
  with self.assertRaises(frappe.ValidationError):svc.save(doc.name,{code:{"evidence":"/private/files/injected.pdf"}})
  with self.assertRaises(frappe.PermissionError):api.upload_evidence(doc.name)
  with self.assertRaises(frappe.PermissionError):save_settings({"question_extras_enabled":1})
  svc.save(doc.name,{code:{"selected_option":"D"}})
  self.assertEqual(frappe.get_doc("IA Maturity Assessment",doc.name).answers[0].comment,"Documented current practice")

 def test_report_preview_and_download_share_identical_authorized_content(self):
  payload=b"%PDF-1.4 test transport"
  with patch("ia_maturity.grc.reports.content",return_value=payload) as authorized_content:
   for inline,disposition in [(0,"attachment"),(1,"inline")]:
    api.download_report("QA",inline=inline)
    self.assertEqual(frappe.local.response.filecontent,payload)
    self.assertEqual(frappe.local.response.content_type,"application/pdf")
    self.assertEqual(frappe.local.response.display_content_as,disposition)
    authorized_content.assert_called_with("QA")

 def test_default_template_can_be_revised_and_selected_for_new_assessments(self):
  existing=self.make()
  old_text=existing.answers[0].question_text
  frappe.set_user("Administrator")
  from ia_maturity.grc.administration import templates,save_template,publish_template
  from ia_maturity.grc.assessment_types import default_template
  default=default_template("Internal Audit")
  self.assertTrue(templates(default)["is_default"])
  revision=save_template({},name=default,clone=1)["name"]
  draft=frappe.get_doc("IA Maturity Template",revision)
  self.assertTrue(draft.grc_default_revision)
  self.assertFalse(draft.default_allow_comment)
  self.assertFalse(draft.default_allow_attachment)
  rows=[q.as_dict() for q in draft.questions]
  rows[0]["question_text"]="Revised default governance question"
  save_template({"questions":rows},name=revision)
  publish_template(revision,make_default=1)
  self.assertEqual(default_template("Internal Audit"),revision)
  self.assertEqual(templates()[0]["name"],revision)
  frappe.set_user(CUSTOMER)
  new=svc.new_assessment(ORG)
  self.assertEqual(new.template,revision)
  self.assertEqual(new.answers[0].question_text,"Revised default governance question")
  self.assertEqual(frappe.get_doc(svc.DOCTYPE,existing.name).answers[0].question_text,old_text)
  with self.assertRaises(frappe.PermissionError):publish_template(default,make_default=1)

 def test_customer_visibility_policies_are_admin_controlled_and_validated(self):
  doc=self.make()
  frappe.set_user("Administrator")
  save_settings({"customer_score_timing":"After all answers","customer_sections_visibility":"Collapsed until complete"})
  frappe.set_user(CUSTOMER)
  data=api.assessment(doc.name)
  self.assertEqual(data["customer_score_timing"],"After all answers")
  self.assertEqual(data["customer_sections_visibility"],"Collapsed until complete")
  with self.assertRaises(frappe.PermissionError):save_settings({"customer_score_timing":"During assessment"})
  frappe.set_user("Administrator")
  with self.assertRaises(frappe.ValidationError):save_settings({"customer_score_timing":"invalid"})
  with self.assertRaises(frappe.ValidationError):save_settings({"customer_sections_visibility":"invalid"})
  save_settings({"customer_score_timing":"After submission","customer_sections_visibility":"Hidden"})
  frappe.set_user(CUSTOMER)
  self.assertEqual(api.assessment(doc.name)["customer_score_timing"],"After submission")

 def test_opening_view_migration_updates_old_default_and_preserves_overrides(self):
  from ia_maturity.patches.v2_9.assessment_opening import execute
  frappe.set_user("Administrator")
  for initial,expected in [("Collapsed until complete","Always expanded"),("Always collapsed","Always collapsed"),("Hidden","Hidden"),("Always expanded","Always expanded")]:
   frappe.db.set_single_value("GRC Settings","customer_sections_visibility",initial)
   execute()
   self.assertEqual(frappe.db.get_single_value("GRC Settings","customer_sections_visibility"),expected)

 def test_manager_color_ranges_ten_bands_authorization_validation_and_live_payload(self):
  from ia_maturity.grc.color_policy import color_ranges,save_color_ranges,get_ranges
  from ia_maturity.grc.report_style import report_context
  doc=self.make()
  frappe.set_user("Administrator")
  manager="grc-test-range-manager@example.test"
  if not frappe.db.exists("User",manager):
   with sec.service_write():frappe.get_doc(dict(doctype="User",email=manager,first_name="Range Manager",send_welcome_email=0,roles=[{"role":"GRC Manager"}])).insert(ignore_permissions=True)
  before=frappe.db.get_single_value("GRC Settings","default_due_days")
  frappe.set_user(manager)
  for method in ("color_ranges","save_color_ranges"):
   with patch.object(frappe.local,"request",SimpleNamespace(path="/api/method/ia_maturity.grc.api."+method),create=True),patch.object(frappe.local,"form_dict",frappe._dict()),patch("ia_maturity.grc.mfa.require_verified_session") as verify:
    sec.guard_request()
    verify.assert_called_once()
  initial=color_ranges()
  ranges=[{"min_score":i*10,"color":"#%02X%02X%02X"%(i*20,60,180)} for i in range(10)]
  saved=save_color_ranges(ranges,expected_revision=initial["revision"])
  self.assertEqual(len(saved["ranges"]),10)
  self.assertEqual(get_ranges(),saved["ranges"])
  with self.assertRaises(frappe.TimestampMismatchError):save_color_ranges(ranges,expected_revision=initial["revision"])
  with self.assertRaises(frappe.PermissionError):save_settings({"default_due_days":999})
  self.assertEqual(frappe.db.get_single_value("GRC Settings","default_due_days"),before)
  for invalid in [[],[{"min_score":1,"color":"#112233"}],[{"min_score":0,"color":"red"}],[{"min_score":0,"color":"#112233"},{"min_score":0,"color":"#223344"}],[{"min_score":float("nan"),"color":"#112233"}],[{"min_score":101,"color":"#112233"}]]:
   with self.assertRaises(frappe.ValidationError):save_color_ranges(invalid)
  frappe.set_user(CUSTOMER)
  self.assertEqual(api.assessment(doc.name)["section_color_ranges"],saved["ranges"])
  for user in [CUSTOMER,AUDITOR,OTHER]:
   frappe.set_user(user)
   with self.assertRaises(frappe.PermissionError):color_ranges()
   with self.assertRaises(frappe.PermissionError):save_color_ranges(ranges)
  frappe.set_user("Administrator")
  from ia_maturity.grc.pdf import render
  from ia_maturity.report_data import get_report_context
  from io import BytesIO
  from pypdf import PdfReader
  from pypdf.generic import ContentStream
  reader=PdfReader(BytesIO(render(get_report_context(doc,audience="internal"))))
  fills={tuple(round(float(v)*255) for v in args) for page in reader.pages for args,operator in ContentStream(page.get_contents(),reader).operations if operator==b"rg"}
  for row in ranges:
   color=row["color"]
   self.assertIn(tuple(int(color[i:i+2],16) for i in (1,3,5)),fills)
  result=report_context({"sections":[{"pct":95,"level":"Medium"}]},saved["ranges"])
  self.assertEqual(result["sections"][0]["color"],ranges[9]["color"])

 def test_report_release_freezes_custom_colors_and_ui_policy(self):
  from ia_maturity.grc.color_policy import save_color_ranges
  doc=self.make(submit=True)
  frappe.set_user("Administrator")
  first=[{"min_score":0,"color":"#123456"},{"min_score":75,"color":"#ABCDEF"}]
  save_color_ranges(first)
  with sec.service_write():release=svc.release_report(doc)
  from io import BytesIO
  from pypdf import PdfReader
  from pypdf.generic import ContentStream
  reader=PdfReader(BytesIO(frappe.get_doc("File",release.pdf_file).get_content()))
  fills={tuple(round(float(v)*255) for v in args) for page in reader.pages for args,operator in ContentStream(page.get_contents(),reader).operations if operator==b"rg"}
  self.assertIn((171,205,239),fills)
  snapshot=json.loads(release.report_context)["section_color_ranges"]
  self.assertEqual(snapshot,first)
  save_color_ranges([{"min_score":0,"color":"#FEDCBA"}])
  self.assertEqual(api.assessment(doc.name)["section_color_ranges"],first)
  from ia_maturity.grc.report_style import report_context
  self.assertEqual(report_context(json.loads(release.report_context),[{"min_score":0,"color":"#FEDCBA"}])["sections"][0]["color"],"#ABCDEF")

 def test_maturity_visibility_modes_desk_validation_and_manager_access(self):
  from ia_maturity.grc.maturity_visibility import maturity_display_settings,save_maturity_display
  doc=self.make()
  frappe.set_user("Administrator")
  self.assertEqual(frappe.get_meta("GRC Settings").get_field("overall_maturity_visibility").default,"Hidden")
  manager="grc-test-panel-manager@example.test"
  if not frappe.db.exists("User",manager):
   with sec.service_write():frappe.get_doc(dict(doctype="User",email=manager,first_name="Panel Manager",send_welcome_email=0,roles=[{"role":"GRC Manager"}])).insert(ignore_permissions=True)
  save_maturity_display("Hidden")
  frappe.set_user(manager)
  for method in ("maturity_display_settings","save_maturity_display"):
   with patch.object(frappe.local,"request",SimpleNamespace(path="/api/method/ia_maturity.grc.api."+method),create=True),patch.object(frappe.local,"form_dict",frappe._dict()),patch("ia_maturity.grc.mfa.require_verified_session") as verify:
    sec.guard_request();verify.assert_called_once()
  self.assertEqual(maturity_display_settings()["mode"],"Hidden")
  for mode in ("After assessment completion","Completed sections only","Hidden"):
   save_maturity_display(mode)
   frappe.set_user(CUSTOMER)
   self.assertEqual(api.assessment(doc.name)["overall_maturity_visibility"],mode)
   frappe.set_user(manager)
  with self.assertRaises(frappe.TimestampMismatchError):save_maturity_display("Hidden",expected_mode="Completed sections only")
  with self.assertRaises(frappe.ValidationError):save_maturity_display("invalid")
  with self.assertRaises(frappe.PermissionError):save_settings({"default_due_days":999})
  frappe.set_user("Administrator")
  native=frappe.get_single("GRC Settings");native.overall_maturity_visibility="Completed sections only";native.save(ignore_permissions=True)
  self.assertEqual(maturity_display_settings()["mode"],"Completed sections only")
  native.overall_maturity_visibility="invalid"
  with self.assertRaises(frappe.ValidationError):native.save(ignore_permissions=True)
  for user in (CUSTOMER,AUDITOR):
   frappe.set_user(user)
   with self.assertRaises(frappe.PermissionError):maturity_display_settings()
   with self.assertRaises(frappe.PermissionError):save_maturity_display("Hidden")


 def test_customer_dashboard_only_dates_preserves_detailed_events(self):
  doc=self.make(submit=True)
  for n in range(7):
   sec.log("Answers changed",doc.entity,doc.grc_assignment,doc.name,details={"changes":[{"question":"Q1","note":str(n)}]},internal=False)
  before=frappe.db.count("GRC Activity",{"assessment":doc.name})
  events=api.dashboard()["recent_activity"]
  self.assertTrue(events)
  self.assertEqual({row.action for row in events},{"Assessment started","Submitted"})
  self.assertEqual(frappe.db.count("GRC Activity",{"assessment":doc.name}),before)
  frappe.set_user("Administrator")
  self.assertIn("Answers changed",[row.action for row in api.activity(assignment=doc.grc_assignment)])
