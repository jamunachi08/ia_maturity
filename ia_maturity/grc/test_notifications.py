"""Native mail-queue regressions for customer assessment completion."""
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ia_maturity.grc import api, assessments, notifications, security as sec
from ia_maturity.grc.administration import assign_customer, assign_assessment
from ia_maturity.install import SEED_TEMPLATE

CUSTOMER = "grc-notice-customer@example.test"
CONSULTANT = "grc-notice-consultant@example.test"
REVIEWER = "grc-notice-reviewer@example.test"
ADMIN = "grc-notice-admin@example.test"
OUTSIDER = "grc-notice-outsider@example.test"
ENTITY = "_Test Notification Assessment"


class TestWorkflowNotifications(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        assert sec.enabled(), "Use an isolated GRC test site."
        for email, role in [(CUSTOMER, "GRC Customer"), (CONSULTANT, "GRC Auditor"),
                            (REVIEWER, "GRC Reviewer"), (ADMIN, "GRC App Admin"),
                            (OUTSIDER, "GRC Auditor")]:
            if not frappe.db.exists("User", email):
                with sec.service_write():
                    frappe.get_doc({"doctype":"User","email":email,"first_name":"Notification Fixture",
                        "send_welcome_email":0,"roles":[{"role":role}]}).insert(ignore_permissions=True)
        with sec.service_write():
            if not frappe.db.exists("IA Maturity Entity", ENTITY):
                frappe.get_doc({"doctype":"IA Maturity Entity","entity_name":ENTITY}).insert(ignore_permissions=True)
            if not frappe.db.exists("GRC Organization Membership", {"entity":ENTITY,"user":CUSTOMER}):
                frappe.get_doc({"doctype":"GRC Organization Membership","entity":ENTITY,"user":CUSTOMER,
                    "membership_role":"Organization Admin","active":1}).insert(ignore_permissions=True)
        # Since v3.0 staff and organizations must share a department before assignment.
        from ia_maturity.grc import departments
        for user, role in ((CONSULTANT, "Consultant"), (REVIEWER, "Reviewer")):
            departments.save_department_staff(user, "Internal Audit", role)
        departments.grant(ENTITY, "Internal Audit", "Notification regression fixture")
        assign_customer(ENTITY, CONSULTANT, "Consultant")
        assign_customer(ENTITY, REVIEWER, "Reviewer")
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.in_test = True
        frappe.local.message_log = []
        for user in (CUSTOMER, CONSULTANT, REVIEWER, ADMIN, OUTSIDER):
            frappe.db.set_value("User",user,{"enabled":1,"grc_email_notifications":1,
                "grc_optional_status_updates":1,"grc_optional_reminders":1})
        frappe.db.set_value("IA Maturity Entity",ENTITY,{"grc_optional_status_updates":1,
                                                       "grc_optional_reminders":1})
        # Match the customer backup: the built-in platform operator has an
        # explicit GRC App Admin row, even though it is not a GRC staff identity.
        doc=frappe.get_doc("User","Administrator")
        if "GRC App Admin" not in {r.role for r in doc.roles}:
            doc.append("roles",{"role":"GRC App Admin"})
            with sec.service_write():
                doc.save(ignore_permissions=True)
        account=frappe.get_doc({"doctype":"Email Account","name":"_Test Notification Sender",
            "email_id":"notices@example.test","enable_outgoing":1,"default_outgoing":1})
        # Only environment/transport are replaced: native EmailQueue creation,
        # child recipient validation and frappe.sendmail remain real.
        for p in (
            patch("frappe.email.doctype.email_account.email_account.EmailAccount.find_outgoing",return_value=account),
            patch("frappe.email.email_body.inline_style_in_html",side_effect=lambda html, **_kw: html),
            patch("frappe.email.doctype.email_queue.email_queue.EmailQueue.send",
                  side_effect=AssertionError("SMTP transport must not run in these tests")),
        ):
            p.start()
            self.addCleanup(p.stop)
        frappe.set_user(CUSTOMER)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()
        frappe.local.message_log = []

    def complete(self):
        frappe.set_user(CUSTOMER)
        doc=assessments.new_assessment(ENTITY,SEED_TEMPLATE)
        answers={row.question_code:{"selected_option":"C"} for row in doc.answers}
        api.save_assessment(doc.name,answers)
        frappe.set_user(ADMIN)
        assign_assessment(doc.grc_assignment,consultant=CONSULTANT,reviewer=REVIEWER)
        frappe.set_user(CUSTOMER)
        return doc

    def delivery(self,key):
        return frappe.get_doc("GRC Reminder Delivery",{"delivery_key":key})

    def test_customer_submission_uses_native_queue_without_platform_recipients(self):
        doc=self.complete()
        result=api.submit_assessment(doc.name)
        self.assertEqual(result["state"],"Submitted")
        self.assertEqual(frappe.db.get_value("IA Maturity Assessment",doc.name,"docstatus"),1)
        self.assertEqual(frappe.db.get_value("GRC Assessment Assignment",doc.grc_assignment,"workflow_state"),"Submitted")
        rows=frappe.get_all("GRC Reminder Delivery",filters={"reference_name":doc.grc_assignment},
                           fields=["recipient","status","email_queue"])
        self.assertTrue({CONSULTANT,REVIEWER,ADMIN}.issubset({r.recipient for r in rows}))
        self.assertFalse(set(frappe.STANDARD_USERS)&{r.recipient for r in rows})
        self.assertTrue(all(r.status=="Queued" and r.email_queue for r in rows))
        self.assertEqual(frappe.local.message_log,[])

    def test_customer_can_resubmit_after_clarification(self):
        doc=self.complete()
        api.submit_assessment(doc.name)
        frappe.set_user(CONSULTANT)
        assessments.transition(doc.name,"start_review")
        frappe.set_user(REVIEWER)
        amended=assessments.transition(doc.name,"clarify","Please confirm the supporting answer.")
        frappe.set_user(CUSTOMER)
        result=api.submit_assessment(amended["name"])
        self.assertEqual(result["state"],"Resubmitted")
        rows=frappe.get_all("GRC Reminder Delivery",
            filters={"reference_name":doc.grc_assignment,"subject":"AlphaX | Resubmitted"},
            fields=["recipient","status"])
        self.assertTrue(rows and all(row.status=="Queued" for row in rows))
        self.assertFalse(set(frappe.STANDARD_USERS)&{row.recipient for row in rows})

    def test_workflow_selection_excludes_standard_users(self):
        # frappe._dict, like a real document, supports the .get() lookups used to find the department.
        assignment=frappe._dict(entity=ENTITY,name="notice-reference",assessment="notice-assessment",
            workflow_state="Submitted",consultant="Administrator",reviewer="Guest",modified="2026-11-02")
        with patch.object(notifications,"queue") as queue:
            notifications.workflow_notice(assignment)
        recipients={call.args[2] for call in queue.call_args_list}
        self.assertIn(ADMIN,recipients)
        self.assertFalse(set(frappe.STANDARD_USERS)&recipients)

    def test_direct_platform_notice_is_ignored(self):
        with patch("frappe.sendmail") as send:
            for user in frappe.STANDARD_USERS:
                notifications.queue(ENTITY,"test",user,"Submitted","standard-"+user)
                self.assertFalse(frappe.db.exists("GRC Reminder Delivery",{"delivery_key":"standard-"+user}))
        send.assert_not_called()
        self.assertEqual(frappe.local.message_log,[])

    def test_queue_uses_user_email_and_retains_user_link(self):
        email="notification-destination@example.test"
        frappe.db.set_value("User",CONSULTANT,"email",email)
        notifications.queue(ENTITY,"test",CONSULTANT,"Submitted","profile-email")
        delivery=self.delivery("profile-email")
        self.assertEqual(delivery.recipient,CONSULTANT)
        self.assertEqual(delivery.status,"Queued")
        queued=frappe.get_doc("Email Queue",delivery.email_queue)
        self.assertEqual([r.recipient for r in queued.recipients],[email])

    def test_missing_or_invalid_profile_email_is_failed_without_sending(self):
        with patch("frappe.sendmail") as send:
            for i,email in enumerate(("", "not-an-address", "one@example.test,two@example.test")):
                frappe.db.set_value("User",CONSULTANT,"email",email)
                key="invalid-profile-email-"+str(i)
                notifications.queue(ENTITY,"test",CONSULTANT,"Submitted",key)
                self.assertEqual(self.delivery(key).status,"Failed")
                self.assertIn("valid email",self.delivery(key).error)
        send.assert_not_called()
        self.assertEqual(frappe.local.message_log,[])

    def test_invalid_recipient_email_does_not_abort_assessment_submission(self):
        frappe.db.set_value("User",CONSULTANT,"email","not-an-address")
        doc=self.complete()
        result=api.submit_assessment(doc.name)
        self.assertEqual(result["state"],"Submitted")
        failed=frappe.get_all("GRC Reminder Delivery",
            filters={"reference_name":doc.grc_assignment,"recipient":CONSULTANT},fields=["status","error"])
        self.assertEqual(len(failed),1)
        self.assertEqual(failed[0].status,"Failed")
        self.assertEqual(frappe.local.message_log,[])

    def test_mail_configuration_errors_are_recorded_without_failing_submission(self):
        def invalid_sender(**kwargs):
            frappe.utils.validate_email_address("invalid-sender",throw=True)
        doc=self.complete()
        with patch("frappe.sendmail",side_effect=invalid_sender),patch("frappe.log_error"):
            result=api.submit_assessment(doc.name)
        self.assertEqual(result["state"],"Submitted")
        rows=frappe.get_all("GRC Reminder Delivery",filters={"reference_name":doc.grc_assignment},pluck="status")
        self.assertTrue(rows and all(s=="Failed" for s in rows))
        self.assertEqual(frappe.local.message_log,[])

    def test_idempotency_preferences_and_access_remain_enforced(self):
        notifications.queue(ENTITY,"test",CONSULTANT,"Submitted","once-only")
        notifications.queue(ENTITY,"test",CONSULTANT,"Submitted","once-only")
        self.assertEqual(frappe.db.count("GRC Reminder Delivery",{"delivery_key":"once-only"}),1)
        self.assertEqual(frappe.db.count("Email Queue",{"reference_name":self.delivery("once-only").name}),1)
        frappe.db.set_value("User",CONSULTANT,"grc_optional_status_updates",0)
        with patch("frappe.sendmail") as send:
            notifications.queue(ENTITY,"test",CONSULTANT,"Submitted","opted-out")
            notifications.queue(ENTITY,"test",OUTSIDER,"Submitted","outside-scope")
            frappe.db.set_value("User",REVIEWER,"enabled",0)
            notifications.queue(ENTITY,"test",REVIEWER,"Submitted","disabled-user")
        send.assert_not_called()
        for key in ("opted-out","outside-scope","disabled-user"):
            self.assertFalse(frappe.db.exists("GRC Reminder Delivery",{"delivery_key":key}))

    def test_unexpected_programming_errors_are_not_silenced(self):
        with patch("frappe.sendmail",side_effect=RuntimeError("Unexpected mail integration defect")):
            with self.assertRaises(RuntimeError):
                notifications.queue(ENTITY,"test",CONSULTANT,"Submitted","unexpected-defect")
