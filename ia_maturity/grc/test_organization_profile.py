"""Workbook-profile validation, authorization and snapshot regression tests."""
from copy import deepcopy
import frappe
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import organization_profile as service, security as sec, assessments
from ia_maturity.install import SEED_TEMPLATE

OWNER = "profile-owner@example.test"
OTHER = "profile-other@example.test"
VIEWER = "profile-viewer@example.test"
ORG = "_Test Workbook Company Profile"


def valid_profile():
    data = service.catalog()
    return {"organization": ORG, "industry_type": "Financial Services", "industry_sector": "Banking",
        "other_sector": "", "company_nationality": data["nationalities"][0]["name"], "cr_number": "0123456789",
        "ksa_license_type": "SAMA license", "ksa_license_na": 0,
        "ksa_license_rows": [{"license_name": "SAMA", "valid": "Yes", "expiry_date": "2099-01-01"}],
        "regulators": [], "other_regulator": ""}


class OrganizationProfileCase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.assertTrue(sec.enabled())
        with sec.service_write():
            for email in (OWNER, OTHER, VIEWER):
                if not frappe.db.exists("User", email):
                    frappe.get_doc({"doctype": "User", "email": email, "first_name": "Profile", "last_name": "Tester",
                        "send_welcome_email": 0, "roles": [{"role": "GRC Customer"}]}).insert(ignore_permissions=True)
            if not frappe.db.exists("IA Maturity Entity", ORG):
                frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": ORG}).insert(ignore_permissions=True)
            for email, role in [(OWNER, "Organization Admin"), (VIEWER, "Viewer")]:
                if not frappe.db.exists("GRC Organization Membership", {"entity": ORG, "user": email}):
                    frappe.get_doc({"doctype": "GRC Organization Membership", "entity": ORG, "user": email,
                        "membership_role": role, "active": 1}).insert(ignore_permissions=True)
        frappe.set_user(OWNER)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def test_exact_catalog_and_regulator_precedence(self):
        c = service.catalog()
        self.assertEqual(len(c["industries"]), 23)
        self.assertEqual(sum(len(i["sectors"]) for i in c["industries"]), 278)
        self.assertEqual(len(c["sector_regulators"]), 120)
        self.assertEqual(sum(not v for v in c["sector_regulators"].values()), 10)
        self.assertEqual(service.regulator_names("Financial Services", "Banking", c["nationalities"][0]["name"]), c["general_regulators"] + ["SAMA (Saudi Central Bank)"])
        self.assertEqual(service.regulator_names("Healthcare and Medical Services", "Social care", c["nationalities"][0]["name"]), c["general_regulators"])
        names = service.regulator_names("Financial Services", "Other", c["nationalities"][1]["name"])
        self.assertIn("CMA (Capital Market Authority)", names)
        self.assertIn("MISA (Ministry of Investment)", names)

    def test_catalog_exposes_configured_answer_presentation_with_safe_default(self):
        frappe.db.set_single_value("GRC Settings", "organization_yes_no_display", "Buttons")
        self.assertEqual(service.profile_catalog()["organization_yes_no_display"], "Buttons")
        frappe.db.set_single_value("GRC Settings", "organization_yes_no_display", "")
        self.assertEqual(service.profile_catalog()["organization_yes_no_display"], "Dropdown")
        self.assertNotIn("organization_yes_no_display", service.catalog())

    def test_required_fields_and_dependents(self):
        for field in ("organization", "industry_type", "industry_sector", "company_nationality"):
            value = valid_profile(); value[field] = ""
            with self.assertRaises(frappe.ValidationError): service.validate_profile(value)
        value = valid_profile(); value["industry_sector"] = "Other"
        with self.assertRaises(frappe.ValidationError): service.validate_profile(value)
        value["other_sector"] = "Named business"
        self.assertEqual(service.validate_profile(value)["other_sector"], "Named business")
        value["industry_type"] = "Procurement"; value["industry_sector"] = "Banking"
        with self.assertRaises(frappe.ValidationError): service.validate_profile(value)

    def test_nationality_cr_and_ascii_digits(self):
        value = valid_profile()
        self.assertEqual(service.validate_profile(value)["cr_number"], "0123456789")
        for invalid in ("123", "١٢٣٤٥٦٧٨٩٠", "123456789A"):
            value["cr_number"] = invalid
            with self.assertRaises(frappe.ValidationError): service.validate_profile(value)
        value["company_nationality"] = service.catalog()["nationalities"][3]["name"]
        self.assertEqual(service.validate_profile(value)["cr_number"], "")

    def test_license_optional_rows_and_dates(self):
        value = valid_profile(); value["ksa_license_rows"] = []
        self.assertTrue(service.validate_profile(value))
        value["ksa_license_type"] = ""
        with self.assertRaises(frappe.ValidationError): service.validate_profile(value)
        value["ksa_license_type"] = "License"
        for row in ({"license_name": "Partial"}, {"license_name": "X", "valid": "Yes", "expiry_date": "2026-02-30"}, {"license_name": "X", "valid": "Yes", "expiry_date": "2026-11-10"}):
            value["ksa_license_rows"] = [row]
            with self.assertRaises(frappe.ValidationError): service.validate_profile(value, "2026-11-11")
        value["ksa_license_rows"] = [{"license_name": "X", "valid": "Yes", "expiry_date": "2026-11-11"}]
        self.assertTrue(service.validate_profile(value, "2026-11-11"))
        value["ksa_license_rows"][0].update(valid="No", expiry_date="2026-11-10")
        self.assertTrue(service.validate_profile(value, "2026-11-11"))

    def test_profile_messages_have_arabic_translation(self):
        previous = frappe.local.lang
        frappe.local.lang = "ar"
        try:
            value = valid_profile(); value["organization"] = ""
            with self.assertRaisesRegex(frappe.ValidationError, "أدخل اسم المنشأة"):
                service.validate_profile(value)
        finally:
            frappe.local.lang = previous

    def test_authorization_precedes_validation_and_revocation(self):
        for user in (OTHER, VIEWER):
            frappe.set_user(user)
            with self.assertRaises(frappe.PermissionError): service.save_organization_profile(ORG, {"roles": "tampered"})
        frappe.set_user(OTHER)
        with self.assertRaises(frappe.PermissionError): service.organization_profile(ORG)
        frappe.set_user("Administrator")
        frappe.db.set_value("GRC Organization Membership", {"entity": ORG, "user": OWNER}, "active", 0)
        frappe.set_user(OWNER)
        with self.assertRaises(frappe.PermissionError): service.organization_profile(ORG)

    def test_save_canonical_rows_and_stale_conflict(self):
        before = service.organization_profile(ORG)
        saved = service.save_organization_profile(ORG, valid_profile(), before["modified"])
        self.assertTrue(saved["complete"])
        self.assertEqual(saved["profile"]["cr_number"], "0123456789")
        value = deepcopy(saved["profile"]); value["ksa_license_na"] = 1
        hidden = service.save_organization_profile(ORG, value, saved["modified"])
        self.assertEqual(hidden["profile"]["ksa_license_rows"], [])
        self.assertEqual(len(frappe.get_doc("IA Maturity Entity", ORG).grc_license_rows), 1)
        with self.assertRaises(frappe.TimestampMismatchError): service.save_organization_profile(ORG, valid_profile(), before["modified"])
        with self.assertRaises(frappe.ValidationError): service.save_organization_profile(ORG, dict(valid_profile(), roles="System Manager"))
        value = valid_profile(); value["regulators"] = [{"name": "CMA (Capital Market Authority)", "answer": "Yes"}]
        with self.assertRaises(frappe.ValidationError): service.save_organization_profile(ORG, value)

    def test_grc_save_gate_and_frozen_submission_profile(self):
        frappe.set_user("Administrator")
        template = frappe.copy_doc(frappe.get_doc("IA Maturity Template", SEED_TEMPLATE))
        template.template_name = "_Test Workbook Profile GRC"
        template.grc_published, template.grc_policy = 0, ""
        template.assessment_type = "GRC"
        for question in template.questions:
            question.allow_na = 1
            question.auto_source = ""
            question.is_gating = 0
        template.insert(ignore_permissions=True)
        assessments.publish(template.name)
        frappe.set_user(OWNER)
        doc = assessments.new_assessment(ORG, template=template.name)
        frappe.db.set_value("IA Maturity Template", template.name, "assessment_type", "Internal Audit")
        self.assertTrue(assessments.payload(doc)["profile_required"])
        with self.assertRaises(frappe.ValidationError): assessments.save(doc.name, {})
        service.save_organization_profile(ORG, valid_profile())
        doc.reload()
        self.assertFalse(assessments.payload(doc)["profile_required"])
        assessments.save(doc.name, {q.question_code: {"selected_option": "N/A"} for q in doc.answers})
        submitted = assessments.submit(doc.name)
        self.assertEqual(submitted["docstatus"], 1)
        doc.reload()
        snapshot = doc.grc_profile_snapshot
        value = valid_profile(); value["organization"] = "Changed current company"
        service.save_organization_profile(ORG, value)
        self.assertEqual(doc.grc_profile_snapshot, snapshot)
        from ia_maturity.report_data import get_report_context
        self.assertEqual(get_report_context(doc)["organization_profile"]["organization"], ORG)
        old = frappe._dict(docstatus=1, grc_profile_snapshot=snapshot)
        from unittest.mock import patch
        with patch.object(doc, "get_doc_before_save", return_value=old):
            doc.grc_profile_snapshot = "{}"
            with self.assertRaises(frappe.ValidationError): service.guard_snapshot(doc)
