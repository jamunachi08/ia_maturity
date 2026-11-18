"""Latest customer OTP-only and registered-recipient PDF delivery contracts."""
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime, today

from ia_maturity import i18n
from ia_maturity.grc import auth, mfa, report_delivery, report_policy, security as sec


class DemoIdentityReportsCase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.assertTrue(sec.enabled(), "Use the disposable GRC site.")
        self.customer = "otp-demo-" + uuid4().hex + "@example.test"
        self.auditor = "otp-auditor-" + uuid4().hex + "@example.test"
        with sec.service_write():
            for email, role, name in [(self.customer, "GRC Customer", "Demo Customer"),
                                      (self.auditor, "GRC Auditor", "Demo Auditor")]:
                frappe.get_doc({"doctype": "User", "email": email, "first_name": name,
                    "enabled": 1, "send_welcome_email": 0, "roles": [{"role": role}]}).insert(ignore_permissions=True)
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()
        frappe.flags.pop("grc_consumed_customer_otp", None)
        frappe.local.message_log = []

    def registration(self):
        return frappe.get_doc({"doctype": auth.REG, "email": self.customer,
            "full_name": "Demo Customer", "entity_name": "Pending organization setup",
            "purpose": "Resume", "assessment_date": today(), "consent": 1,
            "status": "Pending", "code_hash": auth.digest("123456"),
            "link_key_hash": auth.digest("local-fixture-link"),
            "expires_on": add_to_date(now_datetime(), minutes=15)}).insert(ignore_permissions=True)

    def test_consumed_otp_is_the_only_customer_session_creation_proof(self):
        reg = self.registration()
        session = frappe._dict(user="Guest", sid="local-fixture-session", data=frappe._dict())
        manager = SimpleNamespace(user=self.customer, logout=Mock())

        def login(user):
            manager.user = user
            auth.enforce_staff_mfa(manager)
            session.user = user
            mfa.stamp_session(manager)

        manager.login_as = Mock(side_effect=login)
        with patch.object(frappe.local, "session", session), \
                patch.object(frappe.local, "login_manager", manager, create=True), \
                patch.object(frappe.local, "session_obj", Mock(), create=True), \
                patch.object(frappe.local, "request", SimpleNamespace(path="/api/method/ia_maturity.grc.auth.verify_code"), create=True):
            with self.assertRaises(frappe.AuthenticationError):
                auth.enforce_staff_mfa(manager)
            result = auth.consume(reg.name, code="123456")
            self.assertEqual(result["user"], self.customer)
            self.assertNotIn("requires_mfa", result)
            self.assertEqual(session.data.grc_customer_otp_user, self.customer)
            self.assertIsNone(frappe.flags.get("grc_consumed_customer_otp"))
            with self.assertRaises(frappe.ValidationError):
                auth.consume(reg.name, code="123456")

    def test_signup_company_is_required_before_reserving_email_allowance(self):
        for email in (self.customer, "new-"+self.customer):
            with patch("ia_maturity.grc.auth.limit"), \
                    patch("ia_maturity.grc.auth.code_request_limit") as quota:
                with self.assertRaises(frappe.ValidationError):
                    auth.request_code(email, purpose="Start", full_name="Demo Customer", consent=1)
                quota.assert_not_called()

    def test_password_and_client_supplied_flags_cannot_create_customer_session(self):
        manager = SimpleNamespace(user=self.customer, logout=Mock())
        with patch.object(frappe.local, "form_dict", frappe._dict(grc_consumed_customer_otp=self.customer), create=True):
            with self.assertRaises(frappe.AuthenticationError):
                auth.enforce_staff_mfa(manager)
            with self.assertRaises(frappe.AuthenticationError):
                mfa.stamp_session(manager)
        manager.logout.assert_called_once()

    def test_legacy_sessions_cross_user_proof_and_api_tokens_are_rejected(self):
        session = frappe._dict(user=self.customer, sid="local-fixture-session", data=frappe._dict())
        manager = SimpleNamespace(logout=Mock())
        with patch.object(frappe.local, "session", session), \
                patch.object(frappe.local, "login_manager", manager, create=True), \
                patch.object(frappe.local, "request", SimpleNamespace(path="/api/method/ia_maturity.grc.api.organizations"), create=True), \
                patch.object(frappe.local, "form_dict", frappe._dict(), create=True), \
                patch("frappe.get_request_header", return_value=None):
            with self.assertRaises(frappe.AuthenticationError):
                mfa.require_verified_session()
            session.data.grc_customer_otp_user = self.auditor
            with self.assertRaises(frappe.AuthenticationError):
                mfa.require_verified_session()
            session.data.grc_customer_otp_user = self.customer
            mfa.require_verified_session()
            with patch("frappe.get_request_header", return_value="token invalid-local-fixture"):
                with self.assertRaises(frappe.AuthenticationError):
                    mfa.require_verified_session()

    def test_historic_customer_mfa_flags_do_not_require_passwords_or_enrollment(self):
        frappe.db.set_value("User", self.customer, "grc_mfa_policy", "Required")
        frappe.set_user(self.customer)
        self.assertFalse(mfa.required())
        self.assertTrue(mfa.status()["customer_otp_only"])
        self.assertFalse(mfa.status()["can_enroll"])
        with self.assertRaises(frappe.PermissionError):
            mfa.begin_authenticator("unused")
        from ia_maturity.grc.mfa_policy import set_optional_mfa
        with self.assertRaises(frappe.PermissionError):
            set_optional_mfa(1, "unused")
        from ia_maturity.grc.account_security import desired, set_mfa_policy, set_role_mfa_policy
        self.assertFalse(desired(frappe.get_doc("User", self.customer)))
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.ValidationError):
            set_mfa_policy(self.customer, "Required", "unused")
        with self.assertRaises(frappe.ValidationError):
            set_role_mfa_policy("GRC Customer", "Required", "unused")

    def test_staff_login_still_requires_valid_native_challenge(self):
        manager = SimpleNamespace(user=self.auditor)
        with patch("ia_maturity.grc.mfa.required", return_value=True), \
                patch("ia_maturity.grc.mfa.validate_login_challenge", side_effect=frappe.AuthenticationError) as check:
            with self.assertRaises(frappe.AuthenticationError):
                auth.enforce_staff_mfa(manager)
            check.assert_called_once_with(self.auditor)

    def test_customer_password_reset_is_disabled_and_erp_reset_is_delegated(self):
        from frappe.core.doctype.user import user as core
        with patch.object(core, "_get_user_for_update_password", return_value=frappe._dict(user=self.customer)):
            with self.assertRaises(frappe.AuthenticationError):
                auth.reset_password("unused-password", key="local-fixture")
        with patch.object(core, "_get_user_for_update_password", return_value=frappe._dict(user="Administrator")), \
                patch.object(core, "update_password", return_value="/app") as reset:
            self.assertEqual(auth.reset_password("unused-password", key="local-fixture"), "/app")
            reset.assert_called_once()

    def test_report_recipient_is_customer_actor_or_registered_assessment_customer(self):
        doc = SimpleNamespace(respondent=self.customer)
        with patch("ia_maturity.grc.security.can_read_assessment", return_value=True):
            for user in (self.customer, self.auditor):
                frappe.set_user(user)
                self.assertEqual(report_delivery.report_recipient(doc), self.customer)
            frappe.set_user(self.auditor)
            doc.respondent = self.auditor
            with self.assertRaises(frappe.PermissionError):
                report_delivery.report_recipient(doc)
            doc.respondent = self.customer
            frappe.db.set_value("User", self.customer, "enabled", 0)
            with self.assertRaises(frappe.PermissionError):
                report_delivery.report_recipient(doc)

    def test_revoked_customer_cannot_receive_pdf_even_when_staff_can_read(self):
        frappe.set_user(self.auditor)
        with patch("ia_maturity.grc.security.can_read_assessment", return_value=False):
            with self.assertRaises(frappe.PermissionError):
                report_delivery.report_recipient(SimpleNamespace(respondent=self.customer))

    def test_email_capability_is_independent_of_download_and_preserves_frozen_bytes(self):
        pdf = b"%PDF-1.7 local immutable fixture"
        doc = SimpleNamespace(name="local-fixture", language="en")
        release = SimpleNamespace(pdf_sha256=hashlib.sha256(pdf).hexdigest())
        file = SimpleNamespace(get_content=lambda: pdf)
        with patch("frappe.get_doc", return_value=doc), \
                patch("frappe.db.get_value", return_value="release-fixture"), \
                patch("ia_maturity.grc.security.require_assessment"), \
                patch("ia_maturity.grc.report_policy.require_email", return_value={"released": True}) as email, \
                patch("ia_maturity.grc.report_policy.require_download", side_effect=AssertionError("Email must not use download capability")), \
                patch("ia_maturity.grc.reports.released_file", return_value=(doc, release, file)):
            content, caps = report_policy.pdf_bytes(doc.name, for_email=True)
        self.assertEqual(content, pdf)
        self.assertTrue(caps["released"])
        email.assert_called_once_with(doc)

    def test_native_queued_message_contains_exact_pdf_attachment_for_registered_customer(self):
        from email import policy
        from email.parser import Parser
        frappe.set_user(self.customer)
        pdf = b"%PDF-1.7 immutable attachment fixture"
        doc = frappe._dict(name="report-fixture-"+uuid4().hex, entity="fixture", grc_assignment=None,
            doctype="IA Maturity Assessment", respondent=self.customer, language="en", grc_assessment_type="Internal Audit")
        account = frappe.get_doc({"doctype": "Email Account", "name": "_Test Report Sender",
            "email_id": "reports@example.test", "enable_outgoing": 1, "default_outgoing": 1})
        get_doc = frappe.get_doc

        def fetch(doctype, *args, **kwargs):
            if doctype == "IA Maturity Assessment" and args and args[0] == doc.name:
                return doc
            return get_doc(doctype, *args, **kwargs)

        with patch("ia_maturity.grc.report_delivery.frappe.get_doc", side_effect=fetch), \
                patch("ia_maturity.grc.security.require_assessment"), \
                patch("ia_maturity.grc.report_delivery.report_recipient", return_value=self.customer), \
                patch("ia_maturity.grc.report_policy.require_email", return_value={"released": False}), \
                patch("ia_maturity.grc.report_policy.pdf_bytes", return_value=(pdf, {})), \
                patch("ia_maturity.grc.security.log"), patch("ia_maturity.grc.auth.limit"), \
                patch("frappe.are_emails_muted", return_value=False), \
                patch("frappe.email.email_body.inline_style_in_html", side_effect=lambda html, **_kw: html), \
                patch("frappe.email.doctype.email_account.email_account.EmailAccount.find_outgoing", return_value=account):
            result = report_delivery.email_report(doc.name)
        self.assertTrue(result["queued"])
        queue = frappe.get_doc("Email Queue", {"reference_doctype": doc.doctype, "reference_name": doc.name})
        self.assertEqual([row.recipient for row in queue.recipients], [self.customer])
        message = Parser(policy=policy.default).parsestr(queue.message)
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_content_type(), "application/pdf")
        self.assertEqual(attachments[0].get_payload(decode=True), pdf)
        self.assertTrue(attachments[0].get_filename().endswith(".pdf"))

    def test_report_copy_follows_assessment_type_without_mutating_ia_strings(self):
        for lang in ("en", "ar"):
            before = dict(i18n.strings(lang))
            grc = i18n.report_strings(lang, "GRC", "GRC instrument fixture")
            self.assertEqual(grc["framework_value"], "GRC instrument fixture")
            self.assertNotEqual(grc["title"], before["title"])
            self.assertEqual(i18n.strings(lang), before)
        self.assertNotIn("Gating", i18n.report_strings("en", "GRC")["scoring_text"])
