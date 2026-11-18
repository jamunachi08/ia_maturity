"""Signup throttling regressions; run only on a disposable GRC test site."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from ia_maturity.grc import auth, security


class SignupRateLimitCase(FrappeTestCase):
    def setUp(self):
        self.assertTrue(security.enabled())
        self.sent_email = frappe._dict(status="Sent", reload=lambda: None, send=lambda: None)
        self.email = f"grc-rate-test-{uuid4().hex}@example.test"
        self.ip = f"grc-rate-test-{uuid4().hex}"
        self.ip_patch = patch.object(frappe.local, "request_ip", self.ip, create=True)
        self.ip_patch.start()
        self.addCleanup(self.ip_patch.stop)
        self.keys = [f"grc:{frappe.local.site}:{kind}:{auth.digest(self.email)}"
            for kind in ("request-email", "request-cooldown")]
        self.ip_key = f"grc:{frappe.local.site}:request-ip:{auth.digest(self.ip)}"
        self.addCleanup(lambda: frappe.cache.delete(*self.keys, self.ip_key))
        frappe.local.response.pop("retry_after_seconds", None)
        frappe.db.set_single_value("GRC Settings", "signup_email_policy", "All valid emails")
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.local.response.pop("retry_after_seconds", None)

    def signup(self, **changes):
        values = dict(email=self.email, purpose="Start", full_name="New Customer", consent=1,
            organization_name="_Test Signup Rate Organization", organization_sector="Healthcare")
        return auth.request_code(**{**values, **changes})

    def test_invalid_form_retries_do_not_consume_email_allowance(self):
        with patch("frappe.sendmail", return_value=self.sent_email) as send:
            for changes in ({"full_name": ""}, {"consent": 0}, {"full_name": "1234"},
                    {"organization_name": ""}, {"organization_sector": "invalid"}, {"organization_name": ""}):
                with self.assertRaises(frappe.ValidationError):
                    self.signup(**changes)
                self.assertIsNone(frappe.cache.get(self.keys[0]))
                self.assertIsNone(frappe.cache.get(self.keys[1]))
            send.assert_not_called()
            result = self.signup()
        self.assertEqual(result["resend_after_seconds"], 60)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(int(frappe.cache.get(self.keys[0])), 1)
        self.assertEqual(int(frappe.cache.get(self.ip_key)), 7)

    def test_rejected_cooldown_retries_leave_hourly_budget_unchanged(self):
        with patch("frappe.sendmail", return_value=self.sent_email) as send:
            self.signup()
            for _ in range(6):
                with self.assertRaises(frappe.RateLimitExceededError):
                    self.signup()
                self.assertLessEqual(frappe.local.response["retry_after_seconds"], 60)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(int(frappe.cache.get(self.keys[0])), 1)
        self.assertEqual(int(frappe.cache.get(self.keys[1])), 1)

    def test_five_accepted_requests_still_exhaust_hourly_budget(self):
        for _ in range(5):
            auth.code_request_limit(self.email)
            frappe.cache.delete(self.keys[1])  # Simulate waiting out the one-minute cooldown.
        before = frappe.cache.ttl(self.keys[0])
        with self.assertRaises(frappe.RateLimitExceededError):
            auth.code_request_limit(self.email)
        self.assertEqual(int(frappe.cache.get(self.keys[0])), 5)
        self.assertIsNone(frappe.cache.get(self.keys[1]))
        self.assertGreater(frappe.local.response["retry_after_seconds"], 3500)
        self.assertLessEqual(frappe.cache.ttl(self.keys[0]), before)

    def test_existing_lockout_keeps_its_original_expiry(self):
        frappe.cache.setex(self.keys[0], 1500, 8)
        with self.assertRaises(frappe.RateLimitExceededError):
            auth.code_request_limit(self.email)
        self.assertEqual(int(frappe.cache.get(self.keys[0])), 8)
        self.assertLessEqual(frappe.local.response["retry_after_seconds"], 1500)
        self.assertGreater(frappe.local.response["retry_after_seconds"], 1490)

    def test_concurrent_requests_reserve_one_email_slot(self):
        cache = frappe.cache
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: cache.eval(auth.CODE_REQUEST_LIMIT, 2, *self.keys), range(20)))
        self.assertEqual(sum(row[0] for row in results), 1)
        self.assertEqual(int(cache.get(self.keys[0])), 1)

    def test_invalid_form_requests_still_hit_ip_limit(self):
        for _ in range(30):
            with self.assertRaises(frappe.ValidationError):
                self.signup(consent=0)
        with self.assertRaises(frappe.RateLimitExceededError):
            self.signup(consent=0)
        self.assertGreater(frappe.local.response["retry_after_seconds"], 3500)
        self.assertIsNone(frappe.cache.get(self.keys[0]))

    def test_expired_cooldown_allows_another_request(self):
        auth.code_request_limit(self.email)
        frappe.cache.delete(self.keys[1])
        auth.code_request_limit(self.email)
        self.assertEqual(int(frappe.cache.get(self.keys[0])), 2)

    def test_legacy_counter_without_ttl_gets_bounded_expiry(self):
        frappe.cache.set(self.keys[0], 8)
        with self.assertRaises(frappe.RateLimitExceededError):
            auth.code_request_limit(self.email)
        self.assertGreater(frappe.cache.ttl(self.keys[0]), 3500)
        frappe.cache.delete(self.keys[0])
        frappe.cache.set(self.keys[1], 2)
        with self.assertRaises(frappe.RateLimitExceededError):
            auth.code_request_limit(self.email)
        self.assertGreater(frappe.cache.ttl(self.keys[1]), 50)
