"""Targeted verification throttle administration on a disposable site."""
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import auth, verification_limits as limits


class VerificationLimitsCase(FrappeTestCase):
    def setUp(self):
        self.email = f"limits-{uuid4().hex}@example.test"
        self.other = f"limits-{uuid4().hex}@example.test"
        self.keys = [key for _, key in limits._keys("email", self.email)[1]]
        self.other_keys = [key for _, key in limits._keys("email", self.other)[1]]
        self.addCleanup(lambda: frappe.cache.delete(*(self.keys + self.other_keys)))
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_inspect_and_reset_are_targeted_and_audited(self):
        for key in self.keys + self.other_keys:
            frappe.cache.setex(key, 120, 5)
        status = limits.verification_limit_status("email", self.email.upper())
        self.assertEqual(status["target"], self.email)
        self.assertEqual([row["count"] for row in status["limits"]], [5, 5])
        self.assertTrue(all(0 < row["remaining_seconds"] <= 120 for row in status["limits"]))
        with patch.object(limits.sec, "log") as log, patch.object(frappe.db, "commit"):
            limits.clear_verification_limits("email", self.email, "Support request")
        self.assertTrue(all(frappe.cache.get(key) is None for key in self.keys))
        self.assertTrue(all(frappe.cache.get(key) is not None for key in self.other_keys))
        self.assertEqual(log.call_args.kwargs["details"]["target"], self.email)

    def test_guest_cannot_inspect_or_clear(self):
        frappe.set_user("Guest")
        for method, args in ((limits.verification_limit_status, ("email", self.email)),
                             (limits.clear_verification_limits, ("email", self.email, "Support request")),
                             (limits.verification_limit_policy, ()),
                             (limits.set_verification_limit_policy, (0, 0, "Support request"))):
            with self.assertRaises((frappe.PermissionError, frappe.AuthenticationError)):
                method(*args)

    def test_non_admin_auditor_cannot_change_policy(self):
        email = f"limits-auditor-{uuid4().hex}@example.test"
        with limits.sec.service_write():
            frappe.get_doc(dict(doctype="User", email=email, first_name="Test Auditor",
                send_welcome_email=0, roles=[{"role": "GRC Auditor"}])).insert(ignore_permissions=True)
        frappe.set_user(email)
        with self.assertRaises(frappe.PermissionError):
            limits.set_verification_limit_policy("0", "0", "Support request")
        with self.assertRaises(frappe.PermissionError):
            limits.verification_limit_policy()

    def test_validation_and_ip_scope(self):
        with self.assertRaises(frappe.ValidationError):
            limits.verification_limit_status("ip", "not an ip")
        with self.assertRaises(frappe.ValidationError):
            limits.clear_verification_limits("email", self.email, "")
        target, keys = limits._keys("ip", "192.0.2.1")
        self.assertEqual(target, "192.0.2.1")
        self.assertEqual([name for name, _ in keys], ["request-ip", "verify-ip"])
        self.assertEqual(keys[0][1], f"grc:{frappe.local.site}:request-ip:{auth.digest(target)}")

    def test_switches_are_independent_and_audited(self):
        for field in limits.POLICY_FIELDS.values():
            frappe.db.set_single_value("GRC Settings", field, 1)
        with patch.object(limits.sec, "log") as log:
            self.assertEqual(limits.set_verification_limit_policy("0", "1", "Investigate delivery"),
                             {"email": False, "ip": True})
            self.assertEqual(log.call_args.kwargs["details"]["before"], {"email": True, "ip": True})
            self.assertEqual(log.call_args.kwargs["details"]["after"], {"email": False, "ip": True})
            self.assertEqual(log.call_args.kwargs["details"]["reason"], "Investigate delivery")
        with patch.object(frappe.cache, "eval", side_effect=AssertionError("email limit must be bypassed")):
            auth.code_request_limit(self.email)
        with patch.object(frappe.cache, "incr", return_value=31), patch.object(frappe.cache, "ttl", return_value=60):
            with self.assertRaises(frappe.RateLimitExceededError):
                auth.limit("request-ip", "192.0.2.1", 30)
        with patch.object(limits.sec, "log"):
            limits.set_verification_limit_policy("1", "0", "Resolve IP lockout")
        with patch.object(frappe.cache, "incr", side_effect=AssertionError("IP limit must be bypassed")):
            auth.limit("request-ip", "192.0.2.1", 30)
            auth.limit("verify-ip", "192.0.2.1", 60)
        with patch.object(frappe.cache, "eval", return_value=[0, 60]):
            with self.assertRaises(frappe.RateLimitExceededError):
                auth.code_request_limit(self.email)

    def test_legacy_missing_policy_is_enabled(self):
        with patch.object(frappe.db, "sql", return_value=[]):
            self.assertTrue(limits.limit_enabled("email"))
            self.assertTrue(limits.limit_enabled("ip"))

    def test_invalid_policy_and_direct_settings_change_denied(self):
        with self.assertRaises(frappe.ValidationError):
            limits.set_verification_limit_policy("2", "1", "Support request")
        with self.assertRaises(frappe.ValidationError):
            limits.set_verification_limit_policy("0", "1", "")
        for field in limits.POLICY_FIELDS.values():
            frappe.db.set_single_value("GRC Settings", field, 1)
        doc = frappe.get_single("GRC Settings")
        doc.set(limits.POLICY_FIELDS["email"], int(not limits.limit_enabled("email")))
        with self.assertRaises(frappe.PermissionError):
            doc.save(ignore_permissions=True)

    def test_unrelated_settings_save_initializes_missing_and_preserves_disabled(self):
        email_field = limits.POLICY_FIELDS["email"]
        ip_field = limits.POLICY_FIELDS["ip"]
        frappe.db.sql("delete from `tabSingles` where doctype=%s and field=%s", ("GRC Settings", email_field))
        frappe.db.set_single_value("GRC Settings", ip_field, 0)
        doc = frappe.get_single("GRC Settings")
        doc.onboarding_attention_hours = 73
        with limits.sec.service_write():
            doc.save(ignore_permissions=True)
        self.assertTrue(limits.limit_enabled("email"))
        self.assertFalse(limits.limit_enabled("ip"))
        self.assertEqual(frappe.db.get_single_value("GRC Settings", email_field, cache=False), 1)
