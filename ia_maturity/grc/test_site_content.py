"""Integration tests for draft isolation, role approvals and auditable publishing."""
import json
import frappe
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import security as sec
from ia_maturity.grc import site_content as site

EDITOR='grc-site-editor@example.test'
REVIEWER='grc-site-reviewer@example.test'
PUBLISHER='grc-site-publisher@example.test'
OUTSIDER='grc-site-outsider@example.test'

class TestSiteContent(FrappeTestCase):
 @classmethod
 def setUpClass(cls):
  super().setUpClass()
  frappe.set_user('Administrator');cls.created=[]
  for email,role in ((EDITOR,'GRC Auditor'),(REVIEWER,'GRC Reviewer'),(PUBLISHER,'GRC App Admin'),(OUTSIDER,'GRC Customer')):
   if not frappe.db.exists('User',email):
    cls.created.append(email)
    with sec.service_write():
     frappe.get_doc({'doctype':'User','email':email,'first_name':'Site','last_name':'Tester','roles':[{'role':role}],'send_welcome_email':0}).insert(ignore_permissions=True)
  frappe.db.commit()

 @classmethod
 def tearDownClass(cls):
  frappe.set_user('Administrator')
  for name in cls.created:
   if frappe.db.exists('User',name):
    with sec.service_write():frappe.delete_doc('User',name,ignore_permissions=True,force=True)
  frappe.db.commit()
  super().tearDownClass()

 def setUp(self):
  frappe.set_user('Administrator');frappe.flags.in_test=True
  # Test on the isolated site without exposing or modifying any real publication.
  site.site_content_configure(['GRC Auditor'],['GRC Reviewer','GRC App Admin'])

 def tearDown(self):
  frappe.set_user('Administrator');frappe.db.rollback();frappe.clear_cache()

 def test_ordered_approval_draft_isolation_and_audit(self):
  from ia_maturity.grc.public import info
  key=next(iter(site.defaults()));before=site.published();before_snapshot=site.published_snapshot();before_info=info();value={k:{'en':v['en'],'ar':v['ar']} for k,v in site.defaults().items()};value.update({'legal.privacy':{'en':'','ar':''},'legal.terms':{'en':'','ar':''}});value[key]={'en':'Updated public title','ar':'عنوان عام محدث'};value['legal.privacy']={'en':'Approved legal text','ar':'نص قانوني معتمد'}
  frappe.set_user(OUTSIDER)
  with self.assertRaises(frappe.PermissionError):site.site_content_save(value)
  with self.assertRaises(frappe.PermissionError):site.site_content_state()
  with self.assertRaises(frappe.PermissionError):site.site_content_revision('not-visible')
  frappe.set_user(EDITOR)
  draft=site.site_content_save(value);self.assertEqual(site.published(),before);self.assertEqual(info()['privacy_en'],before_info['privacy_en'])
  with self.assertRaises(frappe.ValidationError):site.site_content_save(value,draft['name'],'stale')
  submitted=site.site_content_submit(draft['name'],draft['modified']);self.assertEqual(submitted['status'],'Pending')
  with self.assertRaises(frappe.ValidationError):site.site_content_save(value,submitted['name'],submitted['modified'])
  frappe.set_user('Guest')
  from ia_maturity.grc.public import site_content as public_content
  self.assertEqual(public_content(),before)
  with self.assertRaises((frappe.AuthenticationError,frappe.PermissionError)):site.site_content_revision(submitted['name'])
  frappe.set_user(EDITOR)
  with self.assertRaises(frappe.ValidationError):site.site_content_decide(draft['name'],'Approve')
  frappe.set_user(PUBLISHER)
  with self.assertRaises(frappe.PermissionError):site.site_content_decide(draft['name'],'Approve')
  # A subsequent configuration change does not rewrite an already submitted workflow.
  site.site_content_configure(['GRC Auditor'],['GRC App Admin'])
  frappe.set_user(REVIEWER);self.assertTrue(site.can_access())
  first=site.site_content_decide(draft['name'],'Approve','Reviewed');self.assertEqual(first['step'],1)
  self.assertEqual(site.published(),before)
  frappe.set_user(PUBLISHER);last=site.site_content_decide(draft['name'],'Approve','Approved')
  self.assertEqual(last['status'],'Published');self.assertEqual(site.published()[key],value[key]);self.assertEqual(info()['privacy_en'],'Approved legal text')
  events=frappe.get_all('GRC Site Event',filters={'revision':draft['name']},fields=['name','actor','action','details'])
  saved=next(x for x in events if x.actor==EDITOR and x.action=='Draft saved')
  changes=json.loads(saved.details)['changes'];self.assertEqual(changes[key]['before'],before_snapshot[key]);self.assertEqual(changes[key]['after'],value[key])
  self.assertTrue(any(x.actor==REVIEWER and x.action=='Decision' for x in events))
  self.assertTrue(any(x.actor==PUBLISHER and x.action=='Published' for x in events))
  with self.assertRaises(frappe.PermissionError):
   doc=frappe.get_doc('GRC Site Revision',draft['name']);doc.status='Draft';doc.save(ignore_permissions=True)
  with self.assertRaises(frappe.PermissionError):
   frappe.delete_doc('GRC Site Event',events[0].name,ignore_permissions=True)

 def test_rejection_and_input_validation(self):
  frappe.set_user(EDITOR)
  with self.assertRaises(frappe.ValidationError):site.site_content_save({'unknown':{'en':'x','ar':'y'}})
  key=next(iter(site.defaults()));value={k:{'en':v['en'],'ar':v['ar']} for k,v in site.defaults().items()};value.update({'legal.privacy':{'en':'','ar':''},'legal.terms':{'en':'','ar':''}});value[key]={'en':'Draft','ar':'مسودة'};draft=site.site_content_save(value)
  submitted=site.site_content_submit(draft['name'],draft['modified'])
  frappe.set_user(REVIEWER)
  with self.assertRaises(frappe.ValidationError):site.site_content_decide(submitted['name'],'Reject')
  result=site.site_content_decide(submitted['name'],'Reject','Please revise')
  self.assertEqual(result['status'],'Rejected')
  frappe.set_user(EDITOR);value[key]={'en':'Revised','ar':'مراجعة'};new=site.site_content_save(value)
  self.assertNotEqual(new['name'],submitted['name'])
  site.site_content_discard(new['name'],new['modified'])

 def test_custom_role_and_admin_cancellation_are_audited(self):
  frappe.set_user('Administrator')
  role='GRC Site Content Test Editor'
  if not frappe.db.exists('Role',role):frappe.get_doc({'doctype':'Role','role_name':role}).insert(ignore_permissions=True)
  doc=frappe.get_doc('User',OUTSIDER)
  with sec.service_write():
   doc.append('roles',{'role':role});doc.save(ignore_permissions=True)
  frappe.clear_cache(user=OUTSIDER)
  site.site_content_configure([role],['GRC Reviewer'])
  with self.assertRaises(frappe.ValidationError):site.site_content_configure(['All'],['GRC Reviewer'])
  frappe.set_user(OUTSIDER);self.assertTrue(site.can_edit())
  value=site.published_snapshot();key=next(iter(site.defaults()));value[key]={'en':'Custom role draft','ar':'مسودة دور مخصص'}
  draft=site.site_content_save(value);submitted=site.site_content_submit(draft['name'],draft['modified'])
  with self.assertRaises(frappe.PermissionError):site.site_content_cancel(submitted['name'],'not authorized')
  frappe.set_user(PUBLISHER)
  with self.assertRaises(frappe.ValidationError):site.site_content_cancel(submitted['name'],'')
  cancelled=site.site_content_cancel(submitted['name'],'Reviewer role no longer available')
  self.assertEqual(cancelled['status'],'Rejected')
  self.assertTrue(frappe.db.exists('GRC Site Event',{'revision':submitted['name'],'action':'Submission cancelled','actor':PUBLISHER}))

 def test_submitter_approval_is_configurable_and_frozen(self):
  frappe.set_user(PUBLISHER)
  site.site_content_configure(['GRC App Admin'],['GRC App Admin'],1)
  value=site.published_snapshot();key=next(iter(site.defaults()));value[key]={'en':'Single administrator','ar':'مدير واحد'}
  draft=site.site_content_save(value);pending=site.site_content_submit(draft['name'],draft['modified'])
  self.assertTrue(pending['allow_submitter_approval'])
  site.site_content_configure(['GRC App Admin'],['GRC App Admin'],0)
  done=site.site_content_decide(draft['name'],'Approve')
  self.assertEqual(done['status'],'Published')

 def test_stale_pending_revision_cannot_overwrite_new_publication(self):
  frappe.set_user(EDITOR);key=next(iter(site.defaults()));value=site.published_snapshot();value[key]={'en':'First approved','ar':'الأول المعتمد'}
  first=site.site_content_save(value);first=site.site_content_submit(first['name'],first['modified'])
  value[key]={'en':'Second draft','ar':'المسودة الثانية'};second=site.site_content_save(value);second=site.site_content_submit(second['name'],second['modified'])
  frappe.set_user(REVIEWER);site.site_content_decide(first['name'],'Approve')
  frappe.set_user(PUBLISHER);site.site_content_decide(first['name'],'Approve')
  frappe.set_user(REVIEWER)
  with self.assertRaises(frappe.ValidationError):site.site_content_decide(second['name'],'Approve')
  result=site.site_content_decide(second['name'],'Reject','Newer version is live')
  self.assertEqual(result['status'],'Rejected');self.assertEqual(site.published()[key]['en'],'First approved')

 def test_audit_history_is_paginated_without_losing_events(self):
  frappe.set_user(PUBLISHER)
  for index in range(55):site.event('Pagination test',details={'index':index})
  first=site.site_content_state(event_page=1);second=site.site_content_state(event_page=2)
  self.assertEqual(len(first['events']),50);self.assertTrue(first['events_more'])
  self.assertTrue(second['events']);self.assertFalse({e['name'] for e in first['events']} & {e['name'] for e in second['events']})

 def test_structural_changes_are_frozen_audited_and_published(self):
  frappe.set_user(EDITOR);value=site.published_snapshot()
  value['custom.example.title']={'en':'New section','ar':'قسم جديد'};value['custom.example.body']={'en':'Body','ar':'المحتوى'}
  layout={'hidden':['home.assurance'],'removedCards':{'services.main':[0]},'cards':{'services.main':[{'id':'newcard','title':'custom.example.title','body':'custom.example.body'}]},'sections':{'home':[{'id':'newsection','title':'custom.example.title','body':'custom.example.body','cards':[]}]}}
  value['__layout']={'en':json.dumps(layout),'ar':json.dumps(layout)}
  before=site.published();draft=site.site_content_save(value);pending=site.site_content_submit(draft['name'],draft['modified']);self.assertEqual(site.published(),before)
  frappe.set_user(REVIEWER);site.site_content_decide(pending['name'],'Approve')
  frappe.set_user(PUBLISHER);site.site_content_decide(pending['name'],'Approve')
  self.assertEqual(json.loads(site.published()['__layout']['en']),layout)
  self.assertEqual(site.published()['custom.example.title']['ar'],'قسم جديد')
  value['__layout']['ar']='{}'
  with self.assertRaises(frappe.ValidationError):site.validate_content(value)
  value['__layout']['ar']=value['__layout']['en'];layout['sections']['home'][0]['title']='missing';value['__layout']={'en':json.dumps(layout),'ar':json.dumps(layout)}
  with self.assertRaises(frappe.ValidationError):site.validate_content(value)
