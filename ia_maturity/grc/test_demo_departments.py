"""Real database acceptance for department-controlled IA/GRC demo journeys.

Run sequentially on the isolated, muted grc.local site. All account/organization
fixtures are reserved test records; no real recipient receives an email.
"""
from itertools import combinations
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from ia_maturity.grc import api, assessments, departments as dept, onboarding, scope
from ia_maturity.grc import organization_profile, organizations, report_policy, security as sec
from ia_maturity.grc.workbook import TEMPLATE_NAME, install_grc_template
from ia_maturity.install import SEED_TEMPLATE

CUSTOMER = "demo-dept-customer@example.test"
OTHER_CUSTOMER = "demo-dept-other@example.test"
IA_AUDITOR = "demo-dept-ia-auditor@example.test"
GRC_AUDITOR = "demo-dept-grc-auditor@example.test"
IA_MANAGER = "demo-dept-ia-manager@example.test"
GRC_MANAGER = "demo-dept-grc-manager@example.test"
ORG = "_Test Demo Department Customer"
INVITED_COMPANY = "_Test Demo Invited Locked Company"


class TestDemoDepartments(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.assertTrue(sec.enabled())
        self.assertTrue(frappe.conf.get("mute_emails"), "Never run demo acceptance on an unmuted site")
        with sec.service_write():
            for email, role in [(CUSTOMER, "GRC Customer"), (OTHER_CUSTOMER, "GRC Customer"),
                (IA_AUDITOR, "GRC Auditor"), (GRC_AUDITOR, "GRC Auditor"),
                (IA_MANAGER, "GRC Manager"), (GRC_MANAGER, "GRC Manager")]:
                if not frappe.db.exists("User", email):
                    frappe.get_doc({"doctype": "User", "email": email, "first_name": "Demo", "last_name": "Tester",
                        "grc_email_verified": 1, "send_welcome_email": 0, "roles": [{"role": role}]}).insert(ignore_permissions=True)
            for user, kind, role in [(IA_AUDITOR, "Internal Audit", "Consultant"), (GRC_AUDITOR, "GRC", "Consultant"),
                (IA_MANAGER, "Internal Audit", "Manager"), (GRC_MANAGER, "GRC", "Manager")]:
                if not frappe.db.exists("GRC Department Staff", {"user": user, "department": kind}):
                    frappe.get_doc({"doctype": "GRC Department Staff", "user": user, "department": kind,
                        "role": role, "active": 1}).insert(ignore_permissions=True)
            if not frappe.db.exists("IA Maturity Entity", ORG):
                frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": ORG}).insert(ignore_permissions=True)
            if not frappe.db.exists("GRC Organization Membership", {"entity": ORG, "user": CUSTOMER}):
                frappe.get_doc({"doctype": "GRC Organization Membership", "entity": ORG, "user": CUSTOMER,
                    "membership_role": "Organization Admin", "active": 1}).insert(ignore_permissions=True)
            # Both auditors deliberately have assignments. Department checks must
            # still deny the other department independently of organization rows.
            for user in (IA_AUDITOR, GRC_AUDITOR):
                frappe.get_doc({"doctype": "Auditor Customer Assignment", "entity": ORG, "auditor": user,
                    "responsibility": "Consultant", "active": 1}).insert(ignore_permissions=True)
        self.assertEqual(install_grc_template(), TEMPLATE_NAME)
        frappe.db.set_single_value("GRC Operations Policy", "policies", "{}")
        frappe.db.set_single_value("GRC Settings", "results_visibility", "Preliminary scorecard")
        frappe.db.set_single_value("GRC Settings", "overall_maturity_visibility", "After assessment completion")
        frappe.db.set_single_value("GRC Settings", "customer_score_timing", "After assessment completion")
        frappe.db.set_single_value("GRC Settings", "report_access_timing", "Before Audit")
        frappe.db.set_single_value("GRC Settings", "allow_report_download", 1)
        frappe.db.set_single_value("GRC Settings", "allow_report_email", 1)
        self.mail = patch("frappe.sendmail", return_value=frappe._dict(status="Sent", reload=lambda: None, send=lambda: None))
        self.sent_mail = self.mail.start(); self.addCleanup(self.mail.stop)
        self.rate = patch("ia_maturity.grc.onboarding.limit")
        self.rate.start(); self.addCleanup(self.rate.stop)
        frappe.clear_cache()
        frappe.set_user(CUSTOMER)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def start(self, kind):
        return assessments.new_assessment(ORG, SEED_TEMPLATE if kind == "Internal Audit" else TEMPLATE_NAME, assessment_type=kind)

    def valid_profile(self, entity=ORG):
        data = organization_profile.catalog()
        return {"organization": entity, "industry_type": "Financial Services", "industry_sector": "Banking",
            "other_sector": "", "company_nationality": data["nationalities"][0]["name"], "cr_number": "0123456789",
            "ksa_license_type": "", "ksa_license_na": 1, "ksa_license_rows": [], "regulators": [], "other_regulator": ""}

    def grant_second(self):
        request = dept.request_audit_type(ORG, "GRC")
        frappe.set_user(IA_MANAGER)
        dept.decide_audit_type_request(request["name"], 1, "Customer requested GRC")
        frappe.set_user(GRC_MANAGER)
        dept.decide_audit_type_request(request["name"], 1, "GRC team accepts the additional audit")
        frappe.set_user(CUSTOMER)

    def invite(self, kind="GRC", minimum=None):
        frappe.set_user(GRC_AUDITOR if kind == "GRC" else IA_AUDITOR)
        token = "reserved-demo-department-invitation-token-123456789"
        with patch("ia_maturity.grc.onboarding.secrets.token_urlsafe", return_value=token):
            result = onboarding.create_onboarding_invitation(OTHER_CUSTOMER, company=INVITED_COMPANY,
                assessment_type=kind, minimum_sections=minimum or [])
        return result["name"], token

    def test_first_audit_choice_grants_only_the_selected_type(self):
        self.assertEqual(set(dept.allowed_types(ORG)), set(dept.types()))
        doc = self.start("Internal Audit")
        self.assertEqual(dept.entity_types(ORG), {"Internal Audit"})
        self.assertFalse(doc.grc_scope_snapshot)
        self.assertEqual(dept.allowed_types(ORG), ["Internal Audit"])
        with self.assertRaises(frappe.PermissionError):
            self.start("GRC")
        self.assertEqual(dept.entity_types(ORG), {"Internal Audit"})

    def test_second_audit_requires_both_correct_department_managers(self):
        self.start("Internal Audit")
        request = dept.request_audit_type(ORG, "GRC")
        self.assertEqual(request["status"], "Pending Source Approval")
        frappe.set_user(GRC_MANAGER)
        self.assertFalse(any(r["name"] == request["name"] for r in dept.audit_type_requests()))
        with self.assertRaises(frappe.PermissionError):
            dept.decide_audit_type_request(request["name"], 1, "Wrong department")
        frappe.set_user(IA_MANAGER)
        with self.assertRaises(frappe.ValidationError):
            dept.decide_audit_type_request(request["name"], 1, "")
        source = dept.decide_audit_type_request(request["name"], 1, "IA manager approves")
        self.assertEqual(source["status"], "Pending Target Approval")
        self.assertEqual(dept.entity_types(ORG), {"Internal Audit"})
        with self.assertRaises(frappe.PermissionError):
            dept.decide_audit_type_request(request["name"], 1, "Source manager cannot accept for GRC")
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.PermissionError):
            self.start("GRC")
        frappe.set_user(GRC_MANAGER)
        result = dept.decide_audit_type_request(request["name"], 1, "GRC manager accepts")
        self.assertEqual(result["status"], "Approved")
        frappe.set_user(CUSTOMER)
        self.assertEqual(self.start("GRC").grc_assessment_type, "GRC")
        with self.assertRaises(frappe.ValidationError):
            dept.request_audit_type(ORG, "GRC")

    def test_source_rejected_request_remains_hidden_from_target_department(self):
        self.start("Internal Audit")
        request = dept.request_audit_type(ORG, "GRC")
        frappe.set_user(IA_MANAGER)
        result = dept.decide_audit_type_request(request["name"], 0, "IA manager declines sharing")
        self.assertEqual(result["status"], "Rejected")
        self.assertEqual(dept.entity_types(ORG), {"Internal Audit"})
        frappe.set_user(GRC_MANAGER)
        self.assertFalse(any(r["name"] == request["name"] for r in dept.audit_type_requests()))
        with self.assertRaises(frappe.ValidationError):
            dept.decide_audit_type_request(request["name"], 1, "Target cannot revive source rejection")

    def test_manager_demotion_revokes_approval_but_keeps_staff_department_access(self):
        doc = self.start("Internal Audit")
        request = dept.request_audit_type(ORG, "GRC")
        frappe.set_user("Administrator")
        dept.save_department_staff(IA_MANAGER, "Internal Audit", "Consultant", 1)
        frappe.set_user(IA_MANAGER)
        self.assertEqual(dept.staff_types(), {"Internal Audit"})
        self.assertFalse(dept.manager("Internal Audit"))
        with self.assertRaises(frappe.PermissionError):
            dept.decide_audit_type_request(request["name"], 1, "Former manager cannot approve")
        self.assertFalse(sec.can_read_assessment(doc))

    def test_basics_only_profile_grant_hides_company_details_and_regulators(self):
        self.start("GRC")
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        frappe.set_user("Administrator")
        frappe.db.set_value("IA Maturity Entity", ORG, "regulators", "Private legacy regulator details")
        dept.grant(ORG, "GRC", "Reserved basics-only test", profile_access=0)
        frappe.set_user(GRC_AUDITOR)
        self.assertTrue(sec.can_access(ORG))
        with self.assertRaises(frappe.PermissionError):
            organization_profile.organization_profile(ORG)
        with self.assertRaises(frappe.PermissionError):
            organization_profile.save_organization_profile(ORG, self.valid_profile())
        details = organizations.organization_detail(ORG)
        self.assertFalse(details.get("regulators"))
        self.assertFalse(any(k.startswith("grc_profile_") for k in details))
        self.assertNotIn("0123456789", frappe.as_json(details))
        self.assertNotIn("Private legacy regulator details", frappe.as_json(details))

    def test_basics_only_profile_grant_cannot_expose_submitted_report_snapshot(self):
        from ia_maturity.report_data import get_report_context
        doc = self.start("GRC")
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        scope.confirm_assessment_scope(doc.name, ["Risk"], doc.modified)
        doc.reload()
        assessments.save(doc.name, {q.question_code: {"selected_option": "C"} for q in scope.answers(doc)}, str(doc.modified))
        assessments.submit(doc.name)
        doc.reload()
        self.assertIn("0123456789", doc.grc_profile_snapshot)
        frappe.set_user("Administrator")
        dept.grant(ORG, "GRC", "Reserved basics-only report test", profile_access=0)
        frappe.set_user(GRC_AUDITOR)
        self.assertTrue(sec.can_access(ORG))
        try:
            context = get_report_context(doc, include_benchmark=False)
        except frappe.PermissionError:
            pass  # A basics-only grant may deny the full assessment/report.
        else:
            self.assertFalse(context.get("organization_profile"))
            self.assertNotIn("0123456789", frappe.as_json(context))

    def test_wrong_department_assignment_cannot_read_counts_api_or_pdf(self):
        doc = self.start("Internal Audit")
        frappe.set_user(GRC_AUDITOR)
        self.assertNotIn(ORG, sec.entities())
        self.assertFalse(sec.can_read_assessment(doc))
        self.assertNotIn(ORG, [r.name for r in organizations.organizations()])
        dashboard = api.dashboard()
        self.assertEqual(dashboard["total"], 0)
        self.assertEqual(dashboard["counts"], {})
        self.assertEqual(dashboard["customer_count"], 0)
        self.assertEqual(frappe.get_list("IA Maturity Assessment", filters={"name": doc.name}), [])
        with self.assertRaises(frappe.PermissionError):
            api.assessment(doc.name)
        with self.assertRaises(frappe.PermissionError):
            report_policy.pdf_bytes(doc.name)
        frappe.set_user(IA_AUDITOR)
        self.assertTrue(sec.can_read_assessment(doc))
        self.assertEqual(api.dashboard()["total"], 1)

    def test_shared_company_still_keeps_ia_and_grc_assessments_separate(self):
        ia = self.start("Internal Audit")
        self.grant_second()
        grc = self.start("GRC")
        for user, own, other in [(IA_AUDITOR, ia, grc), (GRC_AUDITOR, grc, ia)]:
            frappe.set_user(user)
            self.assertIn(ORG, sec.entities())
            self.assertTrue(sec.can_read_assessment(own))
            self.assertFalse(sec.can_read_assessment(other))
            dashboard = api.dashboard()
            self.assertEqual(dashboard["total"], 1)
            self.assertEqual({r["name"] for r in dashboard["assessments"]}, {own.name})
            self.assertEqual([r.name for r in frappe.get_list("IA Maturity Assessment", filters={"entity": ORG})], [own.name])
            with self.assertRaises(frappe.PermissionError):
                api.assessment(other.name)
            with self.assertRaises(frappe.PermissionError):
                report_policy.pdf_bytes(other.name)

    def test_assessment_assignment_checks_actor_and_selected_staff_department(self):
        from ia_maturity.grc.administration import assign_assessment
        ia = self.start("Internal Audit")
        self.grant_second()
        grc = self.start("GRC")
        frappe.set_user(IA_MANAGER)
        with self.assertRaises(frappe.PermissionError):
            assign_assessment(ia.grc_assignment, consultant=GRC_AUDITOR)
        with self.assertRaises(frappe.PermissionError):
            assign_assessment(grc.grc_assignment, consultant=GRC_AUDITOR)
        frappe.set_user(GRC_MANAGER)
        with self.assertRaises(frappe.PermissionError):
            assign_assessment(ia.grc_assignment, consultant=IA_AUDITOR)
        assign_assessment(grc.grc_assignment, consultant=GRC_AUDITOR)
        self.assertEqual(frappe.db.get_value("GRC Assessment Assignment", grc.grc_assignment, "consultant"), GRC_AUDITOR)

    def test_manager_cannot_assign_other_department_staff_even_on_shared_company(self):
        from ia_maturity.grc.administration import assign_customer
        self.start("Internal Audit")
        frappe.set_user(IA_MANAGER)
        with self.assertRaises(frappe.PermissionError):
            assign_customer(ORG, GRC_AUDITOR, "Reviewer")
        frappe.set_user(CUSTOMER)
        self.grant_second()
        frappe.set_user(IA_MANAGER)
        with self.assertRaises(frappe.PermissionError):
            assign_customer(ORG, GRC_AUDITOR, "Reviewer")
        frappe.set_user(GRC_MANAGER)
        with self.assertRaises(frappe.PermissionError):
            assign_customer(ORG, IA_AUDITOR, "Reviewer")

    def test_notification_cannot_cross_department_on_shared_company(self):
        from ia_maturity.grc import notifications
        ia = self.start("Internal Audit")
        self.grant_second()
        grc = self.start("GRC")
        for reference, wrong_user in [(ia, GRC_AUDITOR), (grc, IA_AUDITOR)]:
            key = "reserved-demo-wrong-department:" + reference.name
            before = self.sent_mail.call_count
            notifications.queue(ORG, reference.grc_assignment, wrong_user, "Submitted", key)
            self.assertEqual(self.sent_mail.call_count, before)
            self.assertFalse(frappe.db.exists("GRC Reminder Delivery", {"delivery_key": key}))

    def test_operations_oversight_filters_other_department_records_and_counts(self):
        from ia_maturity.grc import operations
        ia = self.start("Internal Audit")
        self.grant_second()
        grc = self.start("GRC")
        frappe.set_user(IA_AUDITOR)
        ia_followup = api.save_followup(ORG, "Reserved IA private follow-up")
        frappe.set_user(GRC_AUDITOR)
        grc_followup = api.save_followup(ORG, "Reserved GRC private follow-up")
        for user, own, other, own_followup, other_followup, other_auditor in [
            (IA_MANAGER, ia, grc, ia_followup, grc_followup, GRC_AUDITOR),
            (GRC_MANAGER, grc, ia, grc_followup, ia_followup, IA_AUDITOR)]:
            frappe.set_user(user)
            detail = operations.operations_detail("customer", ORG)
            self.assertEqual({r.assessment for r in detail["assessments"]}, {own.name})
            self.assertNotIn(other.name, frappe.as_json(detail))
            self.assertIn(own_followup["name"], {r.name for r in detail["followups"]})
            self.assertNotIn(other_followup["name"], {r.name for r in detail["followups"]})
            self.assertEqual(sum(detail["activity_summary"].values()), len(detail["activity"]))
            overview = operations.operations_overview()
            self.assertNotIn(other_auditor, {r["name"] for r in overview["auditors"]})
            self.assertNotIn(other_auditor, {r.auditor for r in overview["assignments"]})
            with self.assertRaises(frappe.PermissionError):
                operations.operations_detail("auditor", other_auditor)

    def test_revoked_staff_and_disabled_manager_lose_access_on_next_call(self):
        doc = self.start("Internal Audit")
        frappe.set_user(IA_AUDITOR)
        self.assertTrue(sec.can_read_assessment(doc))
        frappe.set_user("Administrator")
        dept.save_department_staff(IA_AUDITOR, "Internal Audit", "Consultant", 0)
        frappe.set_user(IA_AUDITOR)
        self.assertFalse(sec.can_read_assessment(doc))
        self.assertEqual(api.dashboard()["total"], 0)
        with self.assertRaises(frappe.PermissionError):
            api.assessment(doc.name)
        frappe.set_user(CUSTOMER)
        request = dept.request_audit_type(ORG, "GRC")
        frappe.set_user("Administrator")
        frappe.db.set_value("User", IA_MANAGER, "enabled", 0)
        frappe.set_user(IA_MANAGER)
        with self.assertRaises((frappe.PermissionError, frappe.AuthenticationError)):
            dept.decide_audit_type_request(request["name"], 1, "Disabled session cannot approve")

    def test_ia_invitation_email_uses_only_the_inviting_audit_type(self):
        self.invite("Internal Audit")
        values = self.sent_mail.call_args.kwargs
        self.assertIn("Invited by the Internal Audit team", values["message"])
        self.assertNotIn("GRC", values["subject"])
        self.assertNotIn("GRC", values["message"])

    def test_invitation_pins_recipient_company_type_and_minimum_scope(self):
        name, token = self.invite(minimum=["Risk"])
        frappe.set_user("Guest")
        landing = onboarding.onboarding_link(token)
        self.assertEqual((landing["email"], landing["company"], landing["assessment_type"]), (OTHER_CUSTOMER, INVITED_COMPANY, "GRC"))
        self.assertEqual(set(landing["minimum_sections"]), {"Awareness", "Risk"})
        self.assertEqual(landing["team_label"], "Invited by the GRC team")
        with self.assertRaises(frappe.PermissionError):
            onboarding.registration_invitation(CUSTOMER, token=token)
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.PermissionError):
            onboarding.resume_onboarding(name)
        frappe.set_user(OTHER_CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, "Tampered Company", "Other")
        self.assertEqual(result["status"], "Completed")
        self.assertEqual(result["entity"], INVITED_COMPANY)
        doc = frappe.get_doc("IA Maturity Assessment", result["assessment"])
        self.assertEqual(doc.grc_assessment_type, "GRC")
        self.assertEqual(set(frappe.parse_json(doc.grc_invited_sections)), {"Awareness", "Risk"})
        self.assertEqual(dept.allowed_types(INVITED_COMPANY), ["GRC"])
        organization_profile.save_organization_profile(INVITED_COMPANY, self.valid_profile(INVITED_COMPANY))
        with self.assertRaises(frappe.ValidationError):
            scope.confirm_assessment_scope(doc.name, ["Compliance"], doc.modified)
        result = scope.confirm_assessment_scope(doc.name, ["Risk", "Compliance"], doc.modified)
        self.assertEqual(result["question_count"], 32)
        with self.assertRaises(frappe.PermissionError):
            assessments.new_assessment(INVITED_COMPANY, SEED_TEMPLATE, assessment_type="Internal Audit")

    def test_invitation_cannot_survive_revoked_original_department(self):
        name, token = self.invite(kind="Internal Audit")
        frappe.set_user("Administrator")
        # Keep the auditor employed in GRC, but remove their original IA grant.
        dept.save_department_staff(IA_AUDITOR, "GRC", "Consultant", 1)
        dept.save_department_staff(IA_AUDITOR, "Internal Audit", "Consultant", 0)
        frappe.set_user("Guest")
        with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
            onboarding.onboarding_link(token)
        frappe.set_user(OTHER_CUSTOMER)
        with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
            onboarding.resume_onboarding(name)

    def test_revoked_department_inviter_cannot_list_old_department_recipients(self):
        name, _token = self.invite(kind="Internal Audit")
        frappe.set_user("Administrator")
        dept.save_department_staff(IA_AUDITOR, "GRC", "Consultant", 1)
        dept.save_department_staff(IA_AUDITOR, "Internal Audit", "Consultant", 0)
        frappe.set_user(IA_AUDITOR)
        self.assertEqual(onboarding.onboarding_invitations(), [])
        self.assertEqual(onboarding.owner_alert_count(), 0)
        try:
            visible = frappe.get_list("GRC Onboarding Invitation", filters={"name": name})
        except frappe.PermissionError:
            visible = []  # Complete DocType denial is also a valid fail-closed result.
        self.assertEqual(visible, [])
        self.assertFalse(onboarding.has_permission(frappe.get_doc("GRC Onboarding Invitation", name), "read"))

    def test_invited_internal_audit_starts_without_grc_profile_or_scope_choice(self):
        name, token = self.invite(kind="Internal Audit")
        frappe.set_user("Guest")
        landing = onboarding.onboarding_link(token)
        self.assertEqual(landing["team_label"], "Invited by the Internal Audit team")
        self.assertEqual(landing["assessment_type"], "Internal Audit")
        self.assertEqual(landing["minimum_sections"], [])
        frappe.set_user(OTHER_CUSTOMER)
        onboarding.resume_onboarding(name)
        accepted = onboarding.complete_onboarding(name)
        self.assertEqual(accepted["status"], "Completed")
        doc = frappe.get_doc("IA Maturity Assessment", accepted["assessment"])
        self.assertEqual(doc.grc_assessment_type, "Internal Audit")
        self.assertFalse(doc.grc_scope_snapshot)
        self.assertFalse(assessments.payload(doc)["profile_required"])
        self.assertEqual(dept.allowed_types(doc.entity), ["Internal Audit"])
        assessments.save(doc.name, {q.question_code: {"selected_option": "D"} for q in doc.answers}, str(doc.modified))
        result = assessments.submit(doc.name)
        self.assertEqual(result["docstatus"], 1)
        self.assertEqual(result["overall_score"], 100)
        frappe.set_user(IA_AUDITOR)
        self.assertTrue(sec.can_read_assessment(doc))
        frappe.set_user(GRC_AUDITOR)
        self.assertFalse(sec.can_read_assessment(doc))

    def test_real_grc_all_seven_scopes_profile_gate_and_required_answers(self):
        doc = self.start("GRC")
        with self.assertRaises(frappe.ValidationError):
            scope.confirm_assessment_scope(doc.name, ["Risk"], doc.modified)
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        expected = {frozenset(["Governance"]): 16, frozenset(["Risk"]): 19, frozenset(["Compliance"]): 15,
            frozenset(["Governance", "Risk"]): 33, frozenset(["Governance", "Compliance"]): 29,
            frozenset(["Risk", "Compliance"]): 32, frozenset(["Governance", "Risk", "Compliance"]): 46}
        for size in range(1, 4):
            for chosen in combinations(("Governance", "Risk", "Compliance"), size):
                doc = self.start("GRC")
                result = scope.confirm_assessment_scope(doc.name, list(chosen), doc.modified)
                self.assertEqual(result["question_count"], expected[frozenset(chosen)])
                self.assertEqual({q["section_code"] for q in result["questions"]}, set(chosen) | {"Awareness"})
                with self.assertRaises(frappe.ValidationError):
                    assessments.submit(doc.name)
                doc.reload()
                answers = {q.question_code: {"selected_option": "D"} for q in scope.answers(doc)}
                answers["Q1"] = {"selected_option": "N/A"}
                assessments.save(doc.name, answers, str(doc.modified))
                doc.reload()
                with self.assertRaises(frappe.ValidationError):
                    scope.confirm_assessment_scope(doc.name, list(chosen), doc.modified)
                result = assessments.submit(doc.name)
                self.assertEqual(result["docstatus"], 1)
                self.assertEqual(result["overall_score"], 100)
                self.assertEqual(result["maturity_level"], "Leading")
                doc.reload()
                self.assertEqual(doc.answered_count, len(answers))
                self.assertEqual(doc.na_count, 1)
                self.assertTrue(doc.grc_profile_snapshot)
                self.assertEqual(doc.max_points, (len(answers) - 1) * 100)
                self.assertEqual({s.section_code for s in doc.section_scores}, set(chosen) | {"Awareness"})

    def test_real_grc_single_choice_response_policy_and_optional_na(self):
        doc = self.start("GRC")
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        scope.confirm_assessment_scope(doc.name, ["Risk"], doc.modified)
        doc.reload()
        for value in ("A", "B", "C", "D", "N/A"):
            assessments.save(doc.name, {"Q1": {"selected_option": value}}, str(doc.modified))
            doc.reload()
            self.assertEqual(next(q.selected_option for q in doc.answers if q.question_code == "Q1"), value)
        self.assertTrue(all(q.allow_na and q.selection_mode == "Single" for q in doc.answers))
        self.assertFalse(any(q.auto_calculated or q.is_gating or q.auto_source for q in doc.answers))
        for unsupported in ("E", "A,C", ["A"], {"choice": "A"}):
            with self.assertRaises(frappe.ValidationError):
                assessments.save(doc.name, {"Q1": {"selected_option": unsupported}}, str(doc.modified))
            doc.reload()
            self.assertEqual(next(q.selected_option for q in doc.answers if q.question_code == "Q1"), "N/A")
        for forbidden in ({"comment": "GRC answers have no required comment box"}, {"evidence": "/private/files/not-an-authorized-file.pdf"}):
            with self.assertRaises(frappe.ValidationError):
                assessments.save(doc.name, {"Q1": forbidden}, str(doc.modified))

    def test_profile_and_policy_snapshots_survive_later_company_changes(self):
        doc = self.start("GRC")
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        scope.confirm_assessment_scope(doc.name, ["Risk"], doc.modified)
        doc.reload()
        assessments.save(doc.name, {q.question_code: {"selected_option": "C"} for q in scope.answers(doc)}, str(doc.modified))
        assessments.submit(doc.name)
        doc.reload()
        old_profile, old_policy = doc.grc_profile_snapshot, doc.grc_policy_snapshot
        profile = self.valid_profile(); profile["cr_number"] = "9876543210"
        organization_profile.save_organization_profile(ORG, profile)
        frappe.set_user("Administrator")
        frappe.db.set_single_value("IA Maturity Settings", "points_c", 1)
        doc.reload()
        self.assertEqual((doc.grc_profile_snapshot, doc.grc_policy_snapshot), (old_profile, old_policy))
        self.assertEqual(doc.overall_score, 75)
        self.assertEqual(frappe.parse_json(old_profile)["profile"]["cr_number"], "0123456789")

    def test_clarification_revision_has_new_report_id_and_preserves_prior_history(self):
        from ia_maturity.grc.administration import assign_assessment
        doc = self.start("GRC")
        organization_profile.save_organization_profile(ORG, self.valid_profile())
        scope.confirm_assessment_scope(doc.name, ["Risk"], doc.modified)
        doc.reload()
        assessments.save(doc.name, {q.question_code: {"selected_option": "C"} for q in scope.answers(doc)}, str(doc.modified))
        assessments.submit(doc.name)
        doc.reload()
        original_id, original_profile = doc.grc_report_id, doc.grc_profile_snapshot
        original_policy, original_scope = doc.grc_policy_snapshot, doc.grc_scope_sections
        frappe.set_user(GRC_MANAGER)
        assign_assessment(doc.grc_assignment, consultant=GRC_AUDITOR, reviewer=GRC_MANAGER)
        assessments.transition(doc.name, "start_review")
        revision = assessments.transition(doc.name, "clarify", "Confirm the current evidence behind the awareness answer")
        amended = frappe.get_doc("IA Maturity Assessment", revision["name"])
        self.assertNotEqual(amended.name, doc.name)
        self.assertNotEqual(amended.grc_report_id, original_id)
        self.assertTrue(amended.grc_report_id.startswith("GRC-"))
        self.assertEqual(amended.amended_from, doc.name)
        self.assertEqual(amended.grc_scope_sections, original_scope)
        self.assertEqual(amended.grc_policy_snapshot, original_policy)
        amended_id = amended.grc_report_id
        frappe.set_user(CUSTOMER)
        changed_profile = self.valid_profile(); changed_profile["cr_number"] = "9876543210"
        organization_profile.save_organization_profile(ORG, changed_profile)
        assessments.save(amended.name, {"Q1": {"selected_option": "D"}}, str(amended.modified))
        result = assessments.submit(amended.name)
        self.assertEqual(result["state"], "Resubmitted")
        amended.reload(); doc.reload()
        self.assertEqual(amended.grc_report_id, amended_id)
        self.assertEqual(amended.grc_scope_sections, original_scope)
        self.assertEqual(amended.overall_score, 76.3)
        self.assertEqual(frappe.parse_json(amended.grc_profile_snapshot)["profile"]["cr_number"], "9876543210")
        self.assertEqual((doc.grc_report_id, doc.grc_profile_snapshot, doc.grc_policy_snapshot), (original_id, original_profile, original_policy))
        self.assertEqual(doc.overall_score, 75)
        self.assertEqual(doc.docstatus, 2)
        self.assertTrue(all(q.selected_option == "C" for q in scope.answers(doc)))

    def test_cross_department_invitation_returns_private_request_until_both_approvals(self):
        self.start("Internal Audit")
        frappe.set_user(GRC_AUDITOR)
        result = onboarding.create_onboarding_invitation(CUSTOMER, company="Different company cannot bypass source approval",
            assessment_type="GRC", minimum_sections=["Risk"])
        self.assertTrue(result["pending_approval"])
        self.assertEqual(set(result), {"name", "status", "pending_approval"})
        self.assertNotIn(ORG, frappe.as_json(result))
        self.assertNotIn(CUSTOMER, frappe.as_json(result))
        self.assertFalse(frappe.db.exists("GRC Onboarding Invitation", {"email": CUSTOMER}))
        self.assertEqual(dept.entity_types(ORG), {"Internal Audit"})
        self.assertEqual(dept.audit_type_requests(), [])
        self.assertNotIn(ORG, sec.entities())
        frappe.set_user(IA_MANAGER)
        dept.decide_audit_type_request(result["name"], 1, "Source manager authorizes GRC request")
        frappe.set_user(GRC_AUDITOR)
        self.assertEqual(dept.audit_type_requests(), [])
        self.assertNotIn(ORG, sec.entities())
        frappe.set_user(GRC_MANAGER)
        dept.decide_audit_type_request(result["name"], 1, "Target manager accepts GRC request")
        frappe.set_user(GRC_AUDITOR)
        # The already-provisioned assignment only becomes usable after approval.
        self.assertIn(ORG, sec.entities())
        invitation = onboarding.create_onboarding_invitation(CUSTOMER, company=ORG,
            assessment_type="GRC", minimum_sections=["Risk"])
        self.assertFalse(invitation.get("pending_approval"))
        self.assertEqual(invitation["assessment_type"], "GRC")
        self.assertEqual(invitation["company"], ORG)

    def test_inactive_department_blocks_new_assessments_invitations_and_manager_actions(self):
        frappe.set_user("Administrator")
        frappe.db.set_value("GRC Department", "GRC", "active", 0)
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.ValidationError):
            self.start("GRC")
        frappe.set_user(GRC_AUDITOR)
        self.assertEqual(dept.staff_types(), set())
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            onboarding.create_onboarding_invitation(OTHER_CUSTOMER, company=INVITED_COMPANY, assessment_type="GRC")
        frappe.set_user(GRC_MANAGER)
        self.assertFalse(dept.manager("GRC"))
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            dept.save_department_staff(IA_AUDITOR, "GRC", "Consultant", 1)

    def test_setup_never_publishes_a_cloned_unpublished_workbook_draft(self):
        frappe.set_user("Administrator")
        seed = frappe.get_doc("IA Maturity Template", TEMPLATE_NAME)
        clone = frappe.copy_doc(seed)
        clone.template_name = "_Test Unpublished GRC Workbook Clone"
        clone.grc_published, clone.grc_policy, clone.grc_is_default = 0, "", 0
        clone.insert(ignore_permissions=True)
        self.assertEqual(clone.grc_source_sha256, seed.grc_source_sha256)
        self.assertEqual(install_grc_template(), seed.name)
        clone.reload()
        self.assertFalse(clone.grc_published)
        self.assertFalse(clone.grc_is_default)
        self.assertEqual(clone.grc_policy, "")

    def test_ia_auto_issue_statistics_exclude_grc_and_ambiguous_legacy_rows(self):
        from ia_maturity.issues import closure_stats
        self.start("Internal Audit")
        self.grant_second()
        frappe.set_user("Administrator")
        with sec.service_write():
            for department, status, raised, closed in [
                ("Internal Audit", "Closed", "2026-01-01", "2026-01-31"),
                ("Internal Audit", "Open", "2025-01-01", None),
                ("GRC", "Closed", "2025-01-01", "2026-01-01"),
                ("GRC", "Open", "2025-01-01", None)]:
                frappe.get_doc({"doctype": "IA Audit Issue", "entity": ORG, "title": "Reserved department issue statistic",
                    "grc_department": department, "status": status, "raised_on": raised, "closed_on": closed}).insert(ignore_permissions=True)
            ambiguous = frappe.get_doc({"doctype": "IA Audit Issue", "entity": ORG, "title": "Reserved ambiguous historical issue",
                "grc_department": "Internal Audit", "status": "Closed", "raised_on": "2025-01-01", "closed_on": "2026-06-01"}).insert(ignore_permissions=True)
        # Simulate unclassified old data in an organization shared by both teams.
        frappe.db.set_value("IA Audit Issue", ambiguous.name, "grc_department", None)
        stats = closure_stats(ORG, as_of="2026-11-12")
        self.assertEqual(stats.count, 1)
        self.assertEqual(stats.avg_months, 1.0)
        self.assertEqual(stats.open_over_12, 1)

    def test_empty_active_department_manager_overview_explains_scope_without_granting_writes(self):
        self.start("GRC")
        frappe.set_user(IA_MANAGER)
        self.assertTrue(api.bootstrap()["can_operations"])
        # Other reserved runs may already have department customers. Exercise a
        # legitimately empty managed scope without deleting unrelated fixtures.
        with patch("ia_maturity.grc.operations.managed", return_value=[]):
            result = api.operations_overview()
        self.assertEqual(result["customers"], [])
        self.assertEqual(result["assignments"], [])
        self.assertNotIn(ORG, api.bootstrap()["managed_entities"])
        with self.assertRaises(frappe.PermissionError):
            api.assign_customer(ORG, IA_AUDITOR, "Consultant")
        for user in (IA_AUDITOR, CUSTOMER):
            frappe.set_user(user)
            with self.assertRaises(frappe.PermissionError):
                api.operations_overview()

    def test_first_reviewer_assignment_roster_is_scoped_to_the_customer_department(self):
        self.start("Internal Audit")
        frappe.set_user("Administrator")
        reviewer = "demo-dept-roster-reviewer@example.test"
        with sec.service_write():
            frappe.get_doc({"doctype":"User", "email":reviewer, "first_name":"Roster reviewer",
                "send_welcome_email":0, "roles":[{"role":"GRC Reviewer"}]}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype":"GRC Department Staff", "user":reviewer,
                "department":"Internal Audit", "role":"Reviewer", "active":1}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype":"GRC Department Staff", "user":IA_MANAGER,
                "department":"GRC", "role":"Manager", "active":1}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype":"Auditor Customer Assignment", "entity":ORG,
                "auditor":IA_MANAGER, "responsibility":"Manager", "active":1}).insert(ignore_permissions=True)
        frappe.set_user(IA_MANAGER)
        roster = {row.name for row in api.staff(entity=ORG)}
        self.assertIn(reviewer, roster)
        self.assertNotIn(GRC_AUDITOR, roster)
        self.assertNotIn(GRC_MANAGER, roster)
        result = api.assign_customer(ORG, reviewer, "Reviewer")
        self.assertTrue(result["active"])
        self.assertFalse(next(r for r in api.operations_overview()["customers"] if r.name == ORG)["ownership_locked"])

    def test_profile_capability_and_managed_entities_honor_basics_only_grants(self):
        self.start("Internal Audit")
        self.grant_second()
        frappe.set_user("Administrator")
        with sec.service_write():
            dept.grant(ORG, "GRC", "Manager approval", profile_access=0)
        frappe.set_user(GRC_AUDITOR)
        detail = api.organization_detail(ORG)
        self.assertFalse(detail["can_view_company_profile"])
        self.assertFalse(detail["can_manage"])
        self.assertNotIn(ORG, api.bootstrap()["managed_entities"])
        frappe.set_user(IA_AUDITOR)
        self.assertTrue(api.organization_detail(ORG)["can_view_company_profile"])
        self.assertIn(ORG, api.bootstrap()["managed_entities"])

    def test_followup_edit_capability_matches_existing_write_authorization(self):
        self.start("Internal Audit")
        frappe.set_user(IA_AUDITOR)
        result = api.save_followup(ORG, "Review the reserved demo follow-up")
        self.assertTrue(next(r for r in api.followups() if r.name == result["name"])["can_edit"])
        frappe.set_user("Administrator")
        reviewer = "demo-dept-followup-reviewer@example.test"
        with sec.service_write():
            frappe.get_doc({"doctype":"User", "email":reviewer, "first_name":"Followup reviewer",
                "send_welcome_email":0, "roles":[{"role":"GRC Reviewer"}]}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype":"GRC Department Staff", "user":reviewer,
                "department":"Internal Audit", "role":"Reviewer", "active":1}).insert(ignore_permissions=True)
            frappe.get_doc({"doctype":"Auditor Customer Assignment", "entity":ORG,
                "auditor":reviewer, "responsibility":"Reviewer", "active":1}).insert(ignore_permissions=True)
        frappe.set_user(reviewer)
        self.assertFalse(next(r for r in api.followups() if r.name == result["name"])["can_edit"])
        with self.assertRaises(frappe.PermissionError):
            api.save_followup(ORG, "Unauthorized edit", name=result["name"])
