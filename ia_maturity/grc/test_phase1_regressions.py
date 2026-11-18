"""Regression tests for the v3.1.1 stabilisation fixes."""
import http.server
import threading

import frappe
from frappe.tests.utils import FrappeTestCase

from ia_maturity import compat
from ia_maturity.grc import administration, pdf, verification_limits

# 1x1 transparent PNG, embedded so the report renderer is allowed to load it.
PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
       "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
ERP_USER = "grc-phase1-erp@example.test"


class _Recorder(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        self.hits.append(self.path)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class Phase1RegressionCase(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_desk_helpers_follow_the_running_frappe_version(self):
        expected = "/desk" if compat.frappe_major_version() >= 16 else "/app"
        self.assertEqual(compat.desk_url(), expected)
        self.assertEqual(compat.desk_url("home"), expected + "/home")
        self.assertEqual(compat.desk_url("/grc-staff/"), expected + "/grc-staff")
        for path in ("/app/grc-staff", "/desk/grc-staff"):
            self.assertTrue(compat.is_desk_path(path, "grc-staff"))
        for path in ("/app/grc-staff/x", "/grc-staff", "/desk/home", "/apps/grc-staff"):
            self.assertFalse(compat.is_desk_path(path, "grc-staff"))

    def test_save_staff_validation_messages_reach_the_admin(self):
        # Before 3.1.1 a local "_" shadowed the translator, so these raised UnboundLocalError (HTTP 500).
        with self.assertRaises(frappe.ValidationError) as invalid:
            administration.save_staff("not-an-email", "Test Person")
        self.assertIn("valid email", str(invalid.exception))

        if not frappe.db.exists("User", ERP_USER):
            frappe.get_doc({"doctype": "User", "email": ERP_USER, "first_name": "Phase1",
                            "send_welcome_email": 0, "roles": [{"role": "System Manager"}]}).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError) as convert:
            administration.save_staff(ERP_USER, "Phase One")
        self.assertIn("separate GRC staff account", str(convert.exception))

    def test_verification_limit_policy_returns_the_saved_state(self):
        # Before 3.1.1 the function ended with "return afte", which rolled the change back.
        original = {kind: verification_limits.limit_enabled(kind) for kind in verification_limits.POLICY_FIELDS}
        result = verification_limits.set_verification_limit_policy(
            email_enabled=0 if original["email"] else 1, ip_enabled=1 if original["ip"] else 0,
            reason="Regression test toggle")
        self.assertEqual(result, {"email": not original["email"], "ip": original["ip"]})

    def test_report_pdf_embeds_data_urls_and_never_fetches_external_resources(self):
        _Recorder.hits = []
        server = http.server.HTTPServer(("127.0.0.1", 0), _Recorder)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        try:
            html = (f'<p dir="rtl">تقرير</p><img src="{PNG}">'
                    f'<img src="http://127.0.0.1:{port}/leak.png">'
                    f'<link rel="stylesheet" href="http://127.0.0.1:{port}/leak.css">'
                    '<img src="file:///etc/passwd">')
            document = pdf.render_html(html)
        finally:
            server.shutdown()
        self.assertTrue(document.startswith(b"%PDF-"))
        self.assertIn(b"/Image", document)
        self.assertEqual(_Recorder.hits, [])

    def test_fresh_install_sets_a_default_template_per_assessment_type(self):
        # Regression (3.1.2): Frappe marks patches done on a new install without running them,
        # so fresh GRC sites had no Internal Audit default and invited customers could not start.
        from unittest.mock import patch
        from ia_maturity.grc.assessment_types import default_template
        from ia_maturity.install import SEED_TEMPLATE, install_type_defaults

        frappe.db.set_value("IA Maturity Template", {"assessment_type": "Internal Audit"}, "grc_is_default", 0)
        self.assertFalse(default_template("Internal Audit"))
        with patch.object(frappe.db, "commit"):
            install_type_defaults()
        self.assertEqual(default_template("Internal Audit"), SEED_TEMPLATE)

    def test_immediate_send_delivers_inside_the_call(self):
        # Regression (3.1.2): frappe.sendmail(now=True) now defers delivery until after commit, so
        # the verification flow always saw "Not Sent" and refused every customer sign-in.
        from unittest.mock import Mock, patch
        from ia_maturity.grc.auth import send_immediately

        queue = Mock()
        with patch("frappe.sendmail", return_value=queue) as sendmail:
            self.assertIs(send_immediately(recipients=["a@example.test"], subject="s", message="m"), queue)
        kwargs = sendmail.call_args.kwargs
        self.assertTrue(kwargs["delayed"])
        self.assertFalse(kwargs["now"])
        queue.send.assert_called_once_with()
        with patch("frappe.sendmail", return_value=[]):
            self.assertIsNone(send_immediately(recipients=["a@example.test"], subject="s", message="m"))

    def test_two_factor_values_are_read_and_consumed_in_both_storage_styles(self):
        # Regression (3.1.2): current Frappe caches 2FA data with set_value; the app read raw keys only,
        # so every staff MFA login was rejected.
        from ia_maturity.grc.mfa import forget_frappe_2fa, frappe_2fa_value

        tmp = frappe.generate_hash(length=8)
        frappe.cache.set_value(tmp + "_usr", "staff@example.test", expires_in_sec=60)
        frappe.cache.set(tmp + "_pwd", "raw-style-secret")
        self.assertEqual(frappe_2fa_value(tmp, "_usr"), "staff@example.test")
        self.assertEqual(frappe_2fa_value(tmp, "_pwd"), "raw-style-secret")
        forget_frappe_2fa(tmp)
        self.assertIsNone(frappe_2fa_value(tmp, "_usr"))
        self.assertIsNone(frappe_2fa_value(tmp, "_pwd"))
