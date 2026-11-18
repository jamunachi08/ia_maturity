import frappe
from ia_maturity.grc import security as sec
from ia_maturity.grc.test_scope_onboarding import ScopeOnboardingCase, MANAGER, CUSTOMER, ORG
from ia_maturity.grc.assessment_types import set_template_type
from ia_maturity.grc.api import templates, start_assessment
from ia_maturity.grc.assessments import new_assessment
from ia_maturity.install import SEED_TEMPLATE


class TestAssessmentTypes(ScopeOnboardingCase):
    def setUp(self):
        super().setUp()
        # Classification/default tests are independent of second-type approval,
        # which is exercised by the demo department acceptance suite.
        from ia_maturity.grc import departments
        with sec.service_write():
            departments.grant(ORG, "GRC", "Reserved approved classification fixture")
            if not frappe.db.exists("GRC Department Staff", {"user": MANAGER, "department": "GRC"}):
                frappe.get_doc({"doctype": "GRC Department Staff", "user": MANAGER, "department": "GRC", "role": "Manager", "active": 1}).insert(ignore_permissions=True)

    def test_manager_mapping_and_filtered_customer_choices(self):
        frappe.set_user(MANAGER)
        doc = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        set_template_type(doc.name, "GRC", str(doc.modified))
        frappe.set_user(CUSTOMER)
        self.assertIn(doc.name, [r.name for r in templates(assessment_type="GRC")])
        self.assertNotIn(doc.name, [r.name for r in templates(assessment_type="Internal Audit")])
        with self.assertRaises(frappe.ValidationError):
            start_assessment(ORG, doc.name, assessment_type="Internal Audit")
        self.assertEqual(new_assessment(ORG, doc.name, assessment_type="GRC").template, doc.name)

    def test_customer_cannot_change_classification(self):
        doc = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.PermissionError):
            set_template_type(doc.name, "GRC", str(doc.modified))

    def test_invalid_and_stale_mapping_rejected(self):
        frappe.set_user(MANAGER)
        doc = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        with self.assertRaises(frappe.ValidationError):
            set_template_type(doc.name, "Invalid", str(doc.modified))
        with self.assertRaises(frappe.TimestampMismatchError):
            set_template_type(doc.name, "GRC", "stale")

    def test_defaults_are_independent_and_disabled_choices_hidden(self):
        from ia_maturity.grc.assessment_types import default_template
        from ia_maturity.grc.api import save_template, publish_template
        frappe.set_user("Administrator")
        source = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        set_template_type(source.name, "Internal Audit", str(source.modified), is_active=1, make_default=1)
        clone = save_template({}, name=source.name, clone=1)["name"]
        publish_template(clone)
        row = frappe.get_doc("IA Maturity Template", clone)
        frappe.set_user(MANAGER)
        set_template_type(clone, "GRC", str(row.modified), make_default=1)
        self.assertEqual(default_template("Internal Audit"), source.name)
        self.assertEqual(default_template("GRC"), clone)
        frappe.set_user(CUSTOMER)
        self.assertEqual(new_assessment(ORG, assessment_type="GRC").template, clone)
        frappe.set_user(MANAGER)
        row.reload()
        set_template_type(clone, "GRC", str(row.modified), is_active=0)
        self.assertIsNone(default_template("GRC"))
        for user in (CUSTOMER, MANAGER, "Administrator"):
            frappe.set_user(user)
            self.assertNotIn(clone, [r.name for r in templates()])
        self.assertIn(clone, [r.name for r in templates(management=1)])
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.ValidationError):
            new_assessment(ORG, clone, assessment_type="GRC")
        with self.assertRaises(frappe.PermissionError):
            templates(management=1)
        frappe.set_user(MANAGER)
        row.reload()
        set_template_type(clone, "GRC", str(row.modified), is_active=1, make_default=1)
        row.reload()
        set_template_type(clone, "Internal Audit", str(row.modified))
        self.assertIsNone(default_template("GRC"))
        self.assertEqual(default_template("Internal Audit"), source.name)
        row.reload()
        set_template_type(clone, "Internal Audit", str(row.modified), make_default=1)
        self.assertEqual(default_template("Internal Audit"), clone)
        self.assertFalse(frappe.db.get_value("IA Maturity Template", source.name, "grc_is_default"))

    def test_inactive_cannot_be_default(self):
        frappe.set_user(MANAGER)
        row = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
        with self.assertRaises(frappe.ValidationError):
            set_template_type(row.name, "Internal Audit", str(row.modified), is_active=0, make_default=1)
