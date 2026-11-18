"""Approval application, immutable workflow snapshots and manager isolation."""
import frappe
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import security as sec,operations as ops
from ia_maturity.grc.administration import assign_customer,assign_assessment,save_staff
from ia_maturity.grc.organizations import save_organization
from ia_maturity.grc import assessments
from ia_maturity.install import SEED_TEMPLATE

MANAGER='ops-manager@example.test'
SECOND='ops-second@example.test'
ADMIN='ops-admin@example.test'
CUSTOMER='ops-customer@example.test'
AUDITOR='ops-auditor@example.test'
OUTSIDER='ops-outsider@example.test'
ORG='_Test Operations Alpha'
OTHER='_Test Operations Other'

class TestOperations(FrappeTestCase):
 def setUp(self):
  frappe.set_user('Administrator');frappe.flags.in_test=True
  # Every record and policy in this module is rolled back after each test.
  with ops.writing():frappe.db.set_single_value('GRC Operations Policy','policies','{}')
  with sec.service_write():
   for email,role in ((MANAGER,'GRC Manager'),(SECOND,'GRC Manager'),(ADMIN,'GRC App Admin'),(CUSTOMER,'GRC Customer'),(AUDITOR,'GRC Auditor'),(OUTSIDER,'GRC Auditor')):
    if not frappe.db.exists('User',email):
     frappe.get_doc(dict(doctype='User',email=email,first_name='Operations',last_name='Tester',send_welcome_email=0,roles=[{'role':role}])).insert(ignore_permissions=True)
   for name in (ORG,OTHER):
    if not frappe.db.exists('IA Maturity Entity',name):frappe.get_doc(dict(doctype='IA Maturity Entity',entity_name=name)).insert(ignore_permissions=True)
   if not frappe.db.exists('GRC Organization Membership',{'entity':ORG,'user':CUSTOMER}):
    frappe.get_doc(dict(doctype='GRC Organization Membership',entity=ORG,user=CUSTOMER,membership_role='Organization Admin',active=1)).insert(ignore_permissions=True)
  # Since v3.0 staff and organizations must share a department before assignment.
  from ia_maturity.grc import departments
  # Minimum department membership: these tests check assignment-scoped GRC Managers, not
  # department-wide managers (who see every organization in the department).
  for user,role in ((MANAGER,'Consultant'),(SECOND,'Consultant'),(OUTSIDER,'Consultant'),(AUDITOR,'Consultant')):
   departments.save_department_staff(user,'Internal Audit',role)
  for entity in (ORG,OTHER):
   departments.grant(entity,'Internal Audit','Operations regression fixture')
  assign_customer(ORG,MANAGER,'Manager');assign_customer(ORG,SECOND,'Manager');assign_customer(OTHER,OUTSIDER,'Manager')
  frappe.clear_cache()

 def tearDown(self):
  frappe.set_user('Administrator');frappe.db.rollback();frappe.clear_cache()

 def config(self,entity=None,stages=None,allow_self=False,onboarding=True,assignments=True):
  return ops.operations_configure(dict(onboarding=onboarding,assignments=assignments,stages=stages or ['GRC App Admin'],allow_self=allow_self),entity)

 def test_manager_scope_and_reports(self):
  frappe.set_user(MANAGER)
  overview=ops.operations_overview()
  self.assertEqual([r.name for r in overview['customers']],[ORG])
  self.assertNotIn(OUTSIDER,[r['name'] for r in overview['auditors']])
  self.assertEqual(ops.operations_detail('customer',ORG)['profile']['entity_name'],ORG)
  ops.operations_detail('auditor',SECOND)
  for kind,name in (('customer',OTHER),('auditor',OUTSIDER)):
   with self.assertRaises(frappe.PermissionError):ops.operations_detail(kind,name)
  with self.assertRaises(frappe.PermissionError):self.config()
  with self.assertRaises(frappe.PermissionError):self.config(OTHER)
  self.config(ORG,['GRC Manager','GRC App Admin'])
  frappe.set_user(CUSTOMER)
  with self.assertRaises(frappe.PermissionError):ops.operations_overview()
  with self.assertRaises(frappe.PermissionError):ops.operations_decide('missing','Approve')
  frappe.set_user('Guest')
  with self.assertRaises(frappe.AuthenticationError):ops.operations_overview()

 def test_customer_assignment_order_and_frozen_workflow(self):
  frappe.set_user(MANAGER);self.config(ORG,['GRC Manager','GRC App Admin'])
  request=assign_customer(ORG,AUDITOR,'Consultant')
  self.assertTrue(request['pending_approval']);self.assertFalse(sec.can_access(ORG,AUDITOR))
  duplicate=assign_customer(ORG,AUDITOR,'Consultant');self.assertEqual(duplicate['name'],request['name'])
  with self.assertRaises(frappe.ValidationError):ops.operations_decide(request['name'],'Approve')
  self.config(ORG,['GRC App Admin'])
  frappe.set_user(SECOND);self.assertEqual(ops.operations_decide(request['name'],'Approve')['status'],'Pending')
  self.assertFalse(sec.can_access(ORG,AUDITOR))
  with self.assertRaises(frappe.PermissionError):ops.operations_decide(request['name'],'Approve')
  frappe.set_user(ADMIN);self.assertEqual(ops.operations_decide(request['name'],'Approve')['status'],'Approved')
  self.assertTrue(sec.can_access(ORG,AUDITOR))
  doc=frappe.get_doc('GRC Operations Request',request['name'])
  with self.assertRaises(frappe.PermissionError):doc.status='Pending';doc.save(ignore_permissions=True)
  with self.assertRaises(frappe.PermissionError):frappe.delete_doc(doc.doctype,doc.name,ignore_permissions=True)
  self.assertEqual(len(frappe.parse_json(doc.decisions)),2)

 def test_onboarding_customer_membership_and_rejection(self):
  self.config()
  frappe.set_user(CUSTOMER);request=save_organization({'entity_name':'_Test Operations New Customer','sector':'Other'})
  self.assertTrue(request['pending_approval']);self.assertFalse(frappe.db.exists('IA Maturity Entity','_Test Operations New Customer'))
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Approve')
  self.assertEqual(sec.membership('_Test Operations New Customer',CUSTOMER),'Organization Admin')
  frappe.set_user(CUSTOMER);request=save_organization({'entity_name':'_Test Operations Rejected'})
  frappe.set_user(ADMIN)
  with self.assertRaises(frappe.ValidationError):ops.operations_decide(request['name'],'Reject')
  ops.operations_decide(request['name'],'Reject','Incomplete registration')
  self.assertFalse(frappe.db.exists('IA Maturity Entity','_Test Operations Rejected'))

 def test_auditor_requested_customer_onboarding_joins_requester_department(self):
  # Regression (3.1.2): approval ran as Administrator, skipped the department grant that direct
  # creation applies, and then refused the requester's assignment.
  self.config()
  frappe.set_user(AUDITOR);request=save_organization({'entity_name':'_Test Operations Staff Customer','sector':'Other'})
  self.assertTrue(request['pending_approval']);self.assertFalse(frappe.db.exists('IA Maturity Entity','_Test Operations Staff Customer'))
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Approve')
  from ia_maturity.grc.departments import entity_types
  self.assertEqual(entity_types('_Test Operations Staff Customer'),{'Internal Audit'})
  self.assertTrue(sec.can_access('_Test Operations Staff Customer',AUDITOR))
  self.assertIn('Consultant',sec.responsibilities('_Test Operations Staff Customer',AUDITOR))
  self.assertFalse(sec.can_access('_Test Operations Staff Customer',OUTSIDER))

 def test_auditor_onboarding_manager_cannot_escalate(self):
  frappe.set_user(MANAGER)
  with self.assertRaises(frappe.PermissionError):ops.operations_onboard_auditor(ORG,'ops-new@example.test','Operations New','GRC App Admin')
  with self.assertRaises(frappe.PermissionError):ops.operations_onboard_auditor(OTHER,'ops-new@example.test','Operations New')
  request=ops.operations_onboard_auditor(ORG,'ops-new@example.test','Operations New','GRC Reviewer')
  self.assertFalse(frappe.db.exists('User','ops-new@example.test'))
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Approve')
  self.assertEqual(sec.account_type('ops-new@example.test'),'Auditor')
  self.assertIn('Reviewer',sec.responsibilities(ORG,'ops-new@example.test'))
  self.assertNotIn('GRC App Admin',sec.roles('ops-new@example.test'))

 def test_admin_staff_creation_is_queued_and_cancel_preserves_account(self):
  self.config()
  request=save_staff('ops-admin-new@example.test','Operations New')
  self.assertTrue(request['pending_approval']);self.assertFalse(frappe.db.exists('User','ops-admin-new@example.test'))
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Cancel','Withdrawn')
  self.assertFalse(frappe.db.exists('User','ops-admin-new@example.test'))

 def test_assignment_snapshot_blocks_stale_change_and_revocation_waits(self):
  assign_customer(ORG,AUDITOR,'Consultant')
  self.config(ORG)
  request=assign_customer(ORG,AUDITOR,'Consultant',0)
  self.assertTrue(sec.can_access(ORG,AUDITOR))
  with ops.writing(True):assign_customer(ORG,AUDITOR,'Consultant',0)
  frappe.set_user(ADMIN)
  with self.assertRaises(frappe.ValidationError):ops.operations_decide(request['name'],'Approve')
  ops.operations_decide(request['name'],'Reject','Allocation changed')

 def test_assessment_allocation_waits_until_approval(self):
  assign_customer(ORG,AUDITOR,'Consultant')
  frappe.set_user(CUSTOMER);doc=assessments.new_assessment(ORG,SEED_TEMPLATE)
  frappe.set_user('Administrator');self.config(ORG)
  request=assign_assessment(doc.grc_assignment,consultant=AUDITOR)
  self.assertTrue(request['pending_approval'])
  self.assertFalse(frappe.db.get_value('GRC Assessment Assignment',doc.grc_assignment,'consultant'))
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Approve')
  self.assertEqual(frappe.db.get_value('GRC Assessment Assignment',doc.grc_assignment,'consultant'),AUDITOR)


 def test_invitation_and_membership_changes_require_final_approval(self):
  from ia_maturity.grc.organizations import invite_member,update_membership
  from unittest.mock import patch
  self.config(ORG)
  frappe.set_user(CUSTOMER)
  request=invite_member(ORG,'ops-invited@example.test','Contributor')
  self.assertTrue(request['pending_approval'])
  self.assertFalse(frappe.db.exists('GRC Invitation',{'entity':ORG,'email':'ops-invited@example.test'}))
  frappe.set_user(ADMIN)
  with patch('frappe.sendmail') as send:
   ops.operations_decide(request['name'],'Approve')
   send.assert_called_once()
  self.assertTrue(frappe.db.exists('GRC Invitation',{'entity':ORG,'email':'ops-invited@example.test'}))
  with sec.service_write():
   membership=frappe.get_doc(dict(doctype='GRC Organization Membership',entity=ORG,user=CUSTOMER,membership_role='Contributor',active=1))
   # Use a separate customer for membership tests while retaining the organization admin.
   email='ops-member@example.test'
   frappe.get_doc(dict(doctype='User',email=email,first_name='Member',send_welcome_email=0,roles=[{'role':'GRC Customer'}])).insert(ignore_permissions=True)
   membership.user=email;membership.insert(ignore_permissions=True)
  frappe.set_user(MANAGER)
  request=update_membership(membership.name,'Viewer',0)
  self.assertEqual(sec.membership(ORG,email),'Contributor')
  frappe.set_user(ADMIN);ops.operations_decide(request['name'],'Approve')
  self.assertFalse(sec.membership(ORG,email))

 def test_self_approval_requires_explicit_setting_and_scope_is_rechecked(self):
  frappe.set_user(MANAGER);self.config(ORG,['GRC Manager'],allow_self=True)
  request=assign_customer(ORG,AUDITOR,'Reviewer')
  self.assertEqual(ops.operations_decide(request['name'],'Approve')['status'],'Approved')
  request=assign_customer(ORG,AUDITOR,'Consultant')
  frappe.set_user('Administrator')
  with ops.writing(True):assign_customer(ORG,MANAGER,'Manager',0)
  frappe.set_user(MANAGER)
  with self.assertRaises(frappe.PermissionError):ops.operations_decide(request['name'],'Approve')
