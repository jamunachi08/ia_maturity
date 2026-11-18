"""Personal workspace controls persist on the account without changing profile policy."""
import unittest
from uuid import uuid4
import frappe
from ia_maturity.grc import security as sec
from ia_maturity.grc.api import bootstrap
from ia_maturity.grc.profile import profile, save_workspace_preferences, workspace_preferences

CUSTOMER="grc-workspace-customer@example.test"
AUDITOR="grc-workspace-auditor@example.test"

class TestWorkspacePreferences(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        assert sec.enabled() and frappe.conf.get("allow_tests")
        for email,role in [(CUSTOMER,"GRC Customer"),(AUDITOR,"GRC Auditor")]:
            if not frappe.db.exists("User",email):
                with sec.service_write():
                    frappe.get_doc(dict(doctype="User",email=email,first_name="Workspace Fixture",
                        roles=[{"role":role}],send_welcome_email=0)).insert(ignore_permissions=True)
            frappe.db.set_value("User",email,{"grc_hide_page_tour":0,"grc_hide_help":0})
            frappe.clear_cache(user=email)
        frappe.set_user(CUSTOMER)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def test_existing_and_new_accounts_default_to_visible_controls(self):
        self.assertEqual(workspace_preferences(frappe._dict()),{"show_page_tour":True,"show_help":True})
        self.assertEqual(profile()["workspace_preferences"],{"show_page_tour":True,"show_help":True})

    def test_customer_and_auditor_save_only_their_own_visibility(self):
        # Personal controls remain available even when an admin locks personal details.
        frappe.db.set_single_value("GRC Settings","profile_editable_fields","[]")
        first=save_workspace_preferences({"show_page_tour":False,"show_help":True})
        self.assertEqual(first,{"show_page_tour":False,"show_help":True})
        self.assertEqual(profile()["workspace_preferences"],first)
        self.assertEqual(bootstrap()["workspace_preferences"],first)
        frappe.set_user(AUDITOR)
        self.assertEqual(profile()["workspace_preferences"],{"show_page_tour":True,"show_help":True})
        second=save_workspace_preferences({"show_page_tour":"1","show_help":"0"})
        self.assertEqual(second,{"show_page_tour":True,"show_help":False})
        frappe.set_user(CUSTOMER)
        self.assertEqual(profile()["workspace_preferences"],first)
        self.assertEqual(save_workspace_preferences({"show_page_tour":1,"show_help":1}),
                         {"show_page_tour":True,"show_help":True})

    def test_invalid_values_and_identity_changes_are_rejected_atomically(self):
        for data in [[],{"user":AUDITOR},{"roles":[]},{"show_help":"yes"},
                     {"show_help":None},{"show_page_tour":False,"show_help":2}]:
            with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):
                save_workspace_preferences(data)
        self.assertEqual(workspace_preferences(),{"show_page_tour":True,"show_help":True})

    def test_guest_and_erp_accounts_cannot_use_portal_preferences(self):
        for user in ("Guest","Administrator"):
            frappe.set_user(user)
            with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):
                save_workspace_preferences({"show_help":False})

    def test_new_grc_user_defaults_are_snapshotted_and_user_can_override(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("GRC Settings", {"new_user_page_tour_default": "Disabled", "new_user_help_default": "Disabled"})
        email = f"grc-workspace-new-{uuid4().hex}@example.test"
        with sec.service_write():
            user = frappe.get_doc(dict(doctype="User", email=email, first_name="New user",
                user_type="Website User", send_welcome_email=0,
                roles=[{"role":"GRC Customer"}])).insert(ignore_permissions=True)
        self.assertEqual(workspace_preferences(user), {"show_page_tour": False, "show_help": False})
        frappe.db.set_single_value("GRC Settings", {"new_user_page_tour_default": "Enabled", "new_user_help_default": "Enabled"})
        self.assertEqual(workspace_preferences(frappe.get_doc("User", email)), {"show_page_tour": False, "show_help": False})
        frappe.set_user(email)
        self.assertEqual(save_workspace_preferences({"show_page_tour": True, "show_help": True}),
                         {"show_page_tour": True, "show_help": True})
