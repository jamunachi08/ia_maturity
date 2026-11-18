"""v3.2 configuration: themes, screen layouts, assessment types and role-based report access."""
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ia_maturity.grc import assessment_types as types
from ia_maturity.grc import report_access, screen_layouts, themes
from ia_maturity.grc import security as sec
from ia_maturity.grc import assessments as svc
from ia_maturity.grc.administration import assign_assessment, assign_customer
from ia_maturity.install import SEED_TEMPLATE

ADMIN = "cfg-admin@example.test"
MANAGER = "cfg-manager@example.test"
AUDITOR = "cfg-auditor@example.test"
CUSTOMER = "cfg-customer@example.test"
OUTSIDER = "cfg-outsider@example.test"
ORG = "_Test Configuration Org"
OTHER_ORG = "_Test Configuration Other"


class ConfigurationCase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.in_test = True
        self.assertTrue(sec.enabled(), "Use a disposable GRC test site.")
        with sec.service_write():
            for email, role in ((ADMIN, "GRC App Admin"), (MANAGER, "GRC Manager"), (AUDITOR, "GRC Auditor"),
                                (CUSTOMER, "GRC Customer"), (OUTSIDER, "GRC Customer")):
                if not frappe.db.exists("User", email):
                    frappe.get_doc({"doctype": "User", "email": email, "first_name": "Config", "send_welcome_email": 0,
                        "grc_email_verified": 1, "roles": [{"role": role}]}).insert(ignore_permissions=True)
            for entity, user in ((ORG, CUSTOMER), (OTHER_ORG, OUTSIDER)):
                if not frappe.db.exists("IA Maturity Entity", entity):
                    frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": entity}).insert(ignore_permissions=True)
                if not frappe.db.exists("GRC Organization Membership", {"entity": entity, "user": user}):
                    frappe.get_doc({"doctype": "GRC Organization Membership", "entity": entity, "user": user,
                        "membership_role": "Organization Admin", "active": 1}).insert(ignore_permissions=True)
        from ia_maturity.grc import departments
        for user in (MANAGER, AUDITOR):
            departments.save_department_staff(user, "Internal Audit", "Consultant")
        for entity in (ORG, OTHER_ORG):
            departments.grant(entity, "Internal Audit", "Configuration regression fixture")
        frappe.db.set_single_value("GRC Operations Policy", "policies", "{}")
        frappe.db.set_single_value("GRC Settings", {"report_access_timing": "After Audit",
            "report_access_roles": frappe.as_json(report_access.DEFAULT_ROLES), "report_access_assigned_staff": 1})
        assign_customer(ORG, MANAGER, "Manager")
        assign_customer(ORG, AUDITOR, "Consultant")
        frappe.clear_cache()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def submitted(self):
        frappe.set_user(CUSTOMER)
        doc = svc.new_assessment(ORG, SEED_TEMPLATE, assessment_type="Internal Audit")
        svc.save(doc.name, {a.question_code: {"selected_option": "C"} for a in doc.answers})
        svc.submit(doc.name)
        frappe.set_user("Administrator")
        return frappe.get_doc("IA Maturity Assessment", doc.name)

    # Themes ------------------------------------------------------------------------------------

    def test_presets_seeded_with_irsaa_default_and_readable_colours(self):
        self.assertEqual(themes.tokens()["name"], "IRSAA")
        self.assertEqual(themes.tokens()["primary"], "#12506E")
        for values in themes.PRESETS.values():
            themes.validate_colours(values)

    def test_theme_admin_only_contrast_enforced_and_default_protected(self):
        colours = dict(themes.PRESETS["IRSAA"])
        frappe.set_user(MANAGER)
        with self.assertRaises(frappe.PermissionError):
            themes.save_theme({**colours, "theme_name": "Manager Theme"})
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.ValidationError):
            themes.save_theme({**colours, "primary": "#9FC8DD", "theme_name": "Washed Out"})
        with self.assertRaises(frappe.ValidationError):
            themes.save_theme({**colours, "accent": "red", "theme_name": "Not Hex"})
        themes.save_theme({**colours, "primary": "#5B2C83", "primary_dark": "#3E1D5A", "theme_name": "Royal"})
        self.assertEqual(themes.set_default_theme("Royal")["primary"], "#5B2C83")
        self.assertEqual(themes.tokens()["name"], "Royal")
        with self.assertRaises(frappe.ValidationError):
            themes.delete_theme("Royal")
        with self.assertRaises(frappe.ValidationError):
            themes.save_theme({**colours}, name="IRSAA")
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("GRC Theme", "IRSAA").save()

    # Screen layouts ------------------------------------------------------------------------------

    def test_layouts_default_standard_and_compact_can_be_chosen(self):
        self.assertEqual(screen_layouts.layout_for()["style"], "Standard")
        frappe.set_user(ADMIN)
        chosen = screen_layouts.set_default_screen_layout("Compact")
        self.assertEqual(chosen["style"], "Compact")
        self.assertEqual(chosen["yes_no_display"], "Buttons")
        self.assertEqual(chosen["columns"], 1)
        self.assertTrue(chosen["show_report_lookup"] and chosen["show_saved_assessments"])
        frappe.set_user(CUSTOMER)
        from ia_maturity.grc.organization_profile import profile_catalog
        self.assertEqual(profile_catalog()["layout"]["name"], "Compact")
        with self.assertRaises(frappe.PermissionError):
            screen_layouts.set_default_screen_layout("Standard")

    def test_report_lookup_and_saved_list_never_cross_organizations(self):
        doc = self.submitted()
        report_id = doc.grc_report_id or doc.name
        frappe.set_user(CUSTOMER)
        self.assertEqual(screen_layouts.find_report(report_id)["name"], doc.name)
        self.assertIn(doc.name, [row["name"] for row in screen_layouts.saved_assessments(ORG)])
        frappe.set_user(OUTSIDER)
        with patch("ia_maturity.grc.auth.limit"), self.assertRaises(frappe.ValidationError) as hidden:
            screen_layouts.find_report(report_id)
        with patch("ia_maturity.grc.auth.limit"), self.assertRaises(frappe.ValidationError) as missing:
            screen_layouts.find_report("IA-00000000000000-deadbeef")
        # The same answer whether the report exists or not: IDs cannot be probed.
        self.assertEqual(str(hidden.exception), str(missing.exception))
        with self.assertRaises(frappe.PermissionError):
            screen_layouts.saved_assessments(ORG)

    # Assessment types ----------------------------------------------------------------------------

    def test_custom_type_with_grc_behaviour(self):
        frappe.set_user(ADMIN)
        types.save_assessment_type({"name": "ESG", "label": "Environmental, Social and Governance",
            "label_ar": "الاستدامة", "behaviour": "GRC", "requires_company_profile": 1, "icon": "leaf",
            "report_prefix": "esg", "sort_order": 30})
        from ia_maturity.grc.read_cache import invalidate
        invalidate()
        self.assertIn("ESG", types.type_names(active_only=True))
        self.assertTrue(types.behaves_like_grc("ESG"))
        self.assertTrue(types.requires_profile("ESG"))
        self.assertEqual(types.report_prefix("ESG"), "ESG")
        self.assertEqual(types.label("ESG", "ar"), "الاستدامة")
        self.assertFalse(types.behaves_like_grc("Internal Audit"))
        self.assertTrue(types.behaves_like_grc("GRC"))
        from ia_maturity.i18n import report_strings
        self.assertEqual(report_strings("en", "ESG")["title"], "Environmental, Social and Governance Maturity Assessment")
        self.assertEqual(report_strings("en", "GRC")["title"], "Governance, Risk and Compliance Maturity Assessment")
        with self.assertRaises(frappe.ValidationError):
            types.save_assessment_type({"name": "ESG", "label": "Duplicate", "report_prefix": "ESG"})
        with self.assertRaises(frappe.ValidationError):
            types.save_assessment_type({"label": "Internal Audit", "behaviour": "GRC", "report_prefix": "IA"}, name="Internal Audit")
        types.save_assessment_type({"label": "ESG", "behaviour": "GRC", "report_prefix": "ESG", "active": 0}, name="ESG")
        invalidate()
        from ia_maturity.grc import departments
        with self.assertRaises(frappe.ValidationError):
            departments.validate_type("ESG")
        frappe.set_user(MANAGER)
        with self.assertRaises(frappe.PermissionError):
            types.save_assessment_type({"name": "Shadow", "label": "Shadow", "report_prefix": "SH"})

    def test_template_type_must_be_configured(self):
        frappe.set_user("Administrator")
        template = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        template.flags.ignore_permissions = True
        template.assessment_type = "Unknown Type"
        with self.assertRaises(frappe.ValidationError):
            from ia_maturity.grc.assessments import validate_template
            validate_template(template)

    # Report access -------------------------------------------------------------------------------

    def test_managers_see_reports_by_default_and_auditors_need_role_or_assignment(self):
        doc = self.submitted()
        frappe.set_user(MANAGER)
        self.assertTrue(report_access.staff_access(doc)["view"])
        view = report_access.report_view(doc.name)
        self.assertEqual(view["assessment"], doc.name)
        self.assertTrue(view["preliminary"])
        self.assertIn(doc.name, [row["name"] for row in report_access.report_list()["rows"]])
        frappe.set_user(AUDITOR)
        self.assertTrue(sec.can_read_assessment(doc))  # can work on it, but its report is role-gated
        self.assertFalse(report_access.staff_access(doc)["view"])
        with self.assertRaises(frappe.PermissionError):
            report_access.report_view(doc.name)
        self.assertNotIn(doc.name, [row["name"] for row in report_access.report_list()["rows"]])
        # The assigned consultant keeps access to their own assessment.
        frappe.set_user(ADMIN)
        assign_assessment(doc.grc_assignment, consultant=AUDITOR, reason="Regression test reassignment")
        frappe.set_user(AUDITOR)
        self.assertTrue(report_access.staff_access(doc)["view"])
        # With the assignment rule off, access comes from roles alone; the tenant boundary still applies.
        frappe.set_user(ADMIN)
        report_access.save_report_access(report_access.DEFAULT_ROLES, assigned_staff=0)
        frappe.set_user(AUDITOR)
        self.assertFalse(report_access.staff_access(doc)["view"])
        frappe.set_user(ADMIN)
        roles = {**report_access.DEFAULT_ROLES, "GRC Auditor": {"view": 1, "download": 0, "email": 0}}
        report_access.save_report_access(roles, assigned_staff=0)
        frappe.set_user(AUDITOR)
        self.assertEqual(report_access.staff_access(doc), {"view": True, "download": False, "email": False})
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            report_access.report_view(doc.name)

    def test_report_access_settings_admin_only_and_consistent(self):
        frappe.set_user(MANAGER)
        with self.assertRaises(frappe.PermissionError):
            report_access.save_report_access(report_access.DEFAULT_ROLES)
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.ValidationError):
            report_access.save_report_access({"GRC Manager": {"view": 0, "download": 1, "email": 0}})
        with self.assertRaises(frappe.ValidationError):
            report_access.save_report_access({"Unknown Role": {"view": 1}})
        saved = report_access.save_report_access({"GRC App Admin": {"view": 0}}, assigned_staff=0)
        self.assertEqual(saved["roles"]["GRC App Admin"], {"view": 1, "download": 1, "email": 1})
        self.assertEqual(saved["roles"]["GRC Manager"], {"view": 0, "download": 0, "email": 0})
        self.assertEqual(saved["assigned_staff"], 0)

    def test_customer_report_view_follows_release_policy(self):
        doc = self.submitted()
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.PermissionError):
            report_access.report_view(doc.name)  # After Audit: only once released
        frappe.set_user("Administrator")
        frappe.db.set_single_value("GRC Settings", "report_access_timing", "Before Audit")
        frappe.clear_document_cache("GRC Settings", "GRC Settings")
        frappe.set_user(CUSTOMER)
        self.assertEqual(report_access.report_view(doc.name)["assessment"], doc.name)
