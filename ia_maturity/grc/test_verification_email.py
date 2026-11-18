"""Immediate verification delivery through the native queue, without network SMTP."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, now_datetime

from ia_maturity.grc import auth, security


class TestVerificationEmail(FrappeTestCase):
    def setUp(self):
        self.assertTrue(security.enabled(), "Use a disposable GRC test site.")
        frappe.set_user("Administrator")
        frappe.db.set_single_value("GRC Settings", "signup_email_policy", "All valid emails")
        frappe.db.set_default("suspend_email_queue", 0)
        self.email = f"grc-immediate-{uuid4().hex}@example.test"
        self.smtp = Mock()
        # Frappe v16 queries SMTP extensions (SIZE, DSN) before sending; a plain server
        # advertises none. A bare Mock answers truthy and breaks the size check.
        self.smtp.has_extn.return_value = False
        account = frappe.get_doc({"doctype": "Email Account", "name": "_Test Verification Sender",
            "email_id": "verification@example.test", "enable_outgoing": 1, "default_outgoing": 1})
        for p in (
            patch("frappe.email.doctype.email_account.email_account.EmailAccount.find_outgoing", return_value=account),
            patch("frappe.email.doctype.email_account.email_account.EmailAccount.get_smtp_server",
                  return_value=SimpleNamespace(session=self.smtp)),
            patch("frappe.email.email_body.inline_style_in_html", side_effect=lambda html, **_kw: html),
            patch("frappe.are_emails_muted", return_value=False),
            patch.dict(frappe.flags, testing_email=True),
            # Real SMTP sends commit internally. Keep this disposable test inside
            # its transaction while executing the real queue/status code.
            patch.object(frappe.db, "commit"),
            patch("ia_maturity.grc.auth.limit"),
            patch("ia_maturity.grc.auth.code_request_limit"),
        ):
            p.start()
            self.addCleanup(p.stop)
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.local.message_log = []

    def request(self, language="en"):
        return auth.request_code(self.email, purpose="Start", full_name="Verification Tester",
                                 consent=1, language=language, organization_name="_Test Verification " + self.email.split("@")[0])

    def records(self):
        registration = frappe.get_doc(auth.REG, {"email": self.email})
        queue = frappe.get_doc("Email Queue", {"reference_doctype": auth.REG,
                                               "reference_name": registration.name})
        return registration, queue

    def test_sends_before_return_without_scheduler_or_worker(self):
        from ia_maturity.grc import onboarding
        with patch("frappe.enqueue", side_effect=AssertionError("Verification must not enqueue a worker")), \
                patch("ia_maturity.grc.onboarding.registration_started", wraps=onboarding.registration_started) as started:
            self.smtp.sendmail.side_effect = lambda **kwargs: self.assertTrue(started.called)
            result = self.request()
        self.smtp.sendmail.assert_called_once()
        registration, queue = self.records()
        self.assertEqual(queue.status, "Sent")
        self.assertEqual(queue.recipients[0].recipient, self.email)
        self.assertEqual(queue.recipients[0].status, "Sent")
        self.assertEqual(registration.status, "Pending")
        self.assertEqual(result["expires_in_seconds"], 900)
        self.assertEqual(result["resend_after_seconds"], 60)
        self.assertAlmostEqual((get_datetime(registration.expires_on) - now_datetime()).total_seconds(), 900, delta=10)
        # Verify the code actually handed to SMTP, then reject reuse.
        from email import policy
        from email.parser import BytesParser
        import re
        message = BytesParser(policy=policy.default).parsebytes(self.smtp.sendmail.call_args.kwargs["msg"])
        code = re.search(r"\b[0-9]{6}\b", message.get_body(preferencelist=("plain",)).get_content()).group()
        self.assertEqual(registration.code_hash, auth.digest(code))
        self.assertNotEqual(registration.code_hash, code)
        # Historic customer MFA settings must not redirect OTP-only users to passwords.
        with patch("ia_maturity.grc.mfa.required", return_value=True):
            verified = auth.consume(registration.name, code=code)
        self.assertNotIn("requires_mfa", verified)
        self.assertEqual(verified["user"], self.email)
        self.assertEqual(frappe.session.user, self.email)
        with self.assertRaises(frappe.ValidationError):
            auth.consume(registration.name, code=code)

    def test_smtp_failure_expires_registration_and_stops_delayed_retry(self):
        self.smtp.sendmail.side_effect = RuntimeError("SMTP unavailable")
        with self.assertRaisesRegex(frappe.OutgoingEmailError, "could not be sent"):
            self.request()
        registration, queue = self.records()
        self.assertEqual(registration.status, "Expired")
        self.assertEqual(queue.status, "Expired")
        self.assertFalse(queue.can_send_now())

    def test_suspended_delivery_reports_failure_without_smtp(self):
        frappe.db.set_default("suspend_email_queue", 1)
        with self.assertRaisesRegex(frappe.OutgoingEmailError, "could not be sent"):
            self.request()
        self.smtp.sendmail.assert_not_called()
        registration, queue = self.records()
        self.assertEqual(registration.status, "Expired")
        self.assertEqual(queue.status, "Expired")

    def test_muted_delivery_reports_failure_without_smtp(self):
        with patch("frappe.are_emails_muted", return_value=True):
            with self.assertRaisesRegex(frappe.OutgoingEmailError, "could not be sent"):
                self.request()
        self.smtp.sendmail.assert_not_called()
        self.assertEqual(self.records()[0].status, "Expired")

    def test_missing_outgoing_account_reports_delivery_failure(self):
        with patch("frappe.email.doctype.email_account.email_account.EmailAccount.find_outgoing",
                   side_effect=frappe.OutgoingEmailError("No outgoing account")):
            with self.assertRaisesRegex(frappe.OutgoingEmailError, "could not be sent"):
                self.request()
        self.smtp.sendmail.assert_not_called()
        self.assertEqual(frappe.db.get_value(auth.REG, {"email": self.email}, "status"), "Expired")

    def test_arabic_code_uses_immediate_delivery(self):
        self.request(language="ar")
        self.smtp.sendmail.assert_called_once()
        self.assertEqual(self.records()[1].status, "Sent")
