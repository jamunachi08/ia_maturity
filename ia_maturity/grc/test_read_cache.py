"""Private read reuse must never survive actors, sites, mutations or requests."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from ia_maturity.grc.read_cache import read_cached, read_scope
from ia_maturity.grc import security as sec


class TestReadCache(unittest.TestCase):
    def setUp(self):
        self.previous = getattr(frappe.local, "grc_read_cache", None)
        frappe.local.grc_read_cache = None
        self.calls = Mock(return_value={"roles": ["reader"]})
        self.read = read_cached(self.value)

    def tearDown(self):
        frappe.local.grc_read_cache = self.previous

    def value(self, user=None):
        return self.calls(user)

    def test_no_reuse_outside_scope_or_between_requests(self):
        self.read(); self.read()
        self.assertEqual(self.calls.call_count, 2)
        with read_scope():
            self.read(); self.read()
        with read_scope():
            self.read()
        self.assertEqual(self.calls.call_count, 4)

    def test_copies_results_and_isolates_user_and_site(self):
        with read_scope():
            self.read()["roles"].append("must-not-leak")
            self.assertEqual(self.read(), {"roles": ["reader"]})
            with patch.object(frappe.local, "session", frappe._dict(user="other@example.test")):
                self.read()
            with patch.object(frappe.local, "site", "other-site.local"):
                self.read()
        self.assertEqual(self.calls.call_count, 3)

    def test_direct_write_invalidates_and_disables_reuse(self):
        db = SimpleNamespace(transaction_writes=0, after_commit=Mock(), after_rollback=Mock())
        with patch.object(frappe.local, "db", db), read_scope():
            self.read(); self.read()
            db.transaction_writes += 1
            self.read(); self.read()
        self.assertEqual(self.calls.call_count, 3)

    def test_unknown_database_write_tracking_fails_closed(self):
        for db in (SimpleNamespace(), SimpleNamespace(transaction_writes=0)):
            self.calls.reset_mock()
            with patch.object(frappe.local, "db", db), read_scope():
                self.read(); self.read()
            self.assertEqual(self.calls.call_count, 2)

    def test_commit_and_rollback_disable_reuse_even_when_write_count_resets(self):
        for event in ("after_commit", "after_rollback"):
            callbacks = {}
            db = SimpleNamespace(transaction_writes=0,
                after_commit=SimpleNamespace(add=lambda fn: callbacks.update(after_commit=fn)),
                after_rollback=SimpleNamespace(add=lambda fn: callbacks.update(after_rollback=fn)))
            self.calls.reset_mock()
            with self.subTest(event=event), patch.object(frappe.local, "db", db), read_scope():
                self.read(); self.read()
                callbacks[event]()
                self.read(); self.read()
                self.assertEqual(self.calls.call_count, 3)

    def test_service_write_does_not_retain_authority_after_mutation(self):
        with read_scope():
            self.read(); self.read()
            with sec.service_write():
                self.calls.return_value = {"roles": []}
            self.assertEqual(self.read(), {"roles": []})
            self.read()
        self.assertEqual(self.calls.call_count, 3)

    def test_name_masking_checks_each_candidate_only_once_per_read(self):
        from ia_maturity.grc import identity
        document = frappe._dict(name="name-test@example.test", first_name="Private",
            middle_name="", last_name="")
        with patch("frappe.db.sql", return_value=[("stored-hash",)]), patch(
                "frappe.utils.password.passlibctx.verify", return_value=True) as verify:
            with read_scope():
                for _ in range(3):
                    values, invalid = identity.safe_profile_names(document)
                    self.assertEqual(values["first_name"], "")
                    self.assertIn("first_name", invalid)
            self.assertEqual(verify.call_count, 1)
            with read_scope():
                identity.safe_profile_names(document)
            self.assertEqual(verify.call_count, 2)

    def test_standalone_owner_label_keeps_masking_without_duplicate_hash_work(self):
        from ia_maturity.grc.identity import display_name
        user = "name-test@example.test"
        document = frappe._dict(name=user, first_name="Private", middle_name="", last_name="")
        with patch("frappe.db.get_value", return_value=document), patch(
                "frappe.db.sql", return_value=[("stored-hash",)]), patch(
                "frappe.utils.password.passlibctx.verify", return_value=True) as verify:
            self.assertEqual(display_name(user), user)
            self.assertEqual(verify.call_count, 1)
            self.assertEqual(display_name(user), user)
            self.assertEqual(verify.call_count, 2)
