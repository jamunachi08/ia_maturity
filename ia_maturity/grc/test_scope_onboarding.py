"""Audit-scope and invitation ownership acceptance tests. Disposable GRC sites only."""
from unittest.mock import patch
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime
from ia_maturity.grc import assessments, scope, onboarding, ownership, operations, security as sec, auth, departments
from ia_maturity.grc.administration import assign_customer
from ia_maturity.install import SEED_TEMPLATE

CUSTOMER = "scope-customer@example.test"
AUDITOR = "scope-auditor@example.test"
OTHER = "scope-other@example.test"
MANAGER = "scope-manager@example.test"
REVIEWER = "scope-reviewer@example.test"
ADMIN = "scope-admin@example.test"
ORG = "_Test Scope Customer"


class ScopeOnboardingCase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.assertTrue(sec.enabled())
        frappe.flags.in_test = True
        with sec.service_write():
            for email, role in ((CUSTOMER, "GRC Customer"), (AUDITOR, "GRC Auditor"), (OTHER, "GRC Auditor"),
                    (MANAGER, "GRC Manager"), (REVIEWER, "GRC Reviewer"), (ADMIN, "GRC App Admin")):
                if not frappe.db.exists("User", email):
                    frappe.get_doc({"doctype": "User", "email": email, "first_name": "Scope", "last_name": "Tester",
                        "grc_email_verified": 1, "send_welcome_email": 0, "roles": [{"role": role}]}).insert(ignore_permissions=True)
            if not frappe.db.exists("IA Maturity Entity", ORG):
                frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": ORG}).insert(ignore_permissions=True)
            if not frappe.db.exists("GRC Organization Membership", {"entity": ORG, "user": CUSTOMER}):
                frappe.get_doc({"doctype": "GRC Organization Membership", "entity": ORG, "user": CUSTOMER,
                    "membership_role": "Organization Admin", "active": 1}).insert(ignore_permissions=True)
            for email, role in ((AUDITOR, "Consultant"), (OTHER, "Consultant"), (MANAGER, "Manager"), (REVIEWER, "Reviewer")):
                if not frappe.db.exists("GRC Department Staff", {"user": email, "department": "Internal Audit"}):
                    frappe.get_doc({"doctype": "GRC Department Staff", "user": email, "department": "Internal Audit", "role": role, "active": 1}).insert(ignore_permissions=True)
            departments.grant(ORG, "Internal Audit", "Reserved retained scope fixture")
        frappe.db.set_single_value("GRC Settings", "onboarding_auto_lock", 1)
        frappe.db.set_single_value("GRC Settings", "onboarding_attention_hours", 48)
        frappe.db.set_single_value("GRC Operations Policy", "policies", "{}")
        assign_customer(ORG, AUDITOR, "Consultant")
        assign_customer(ORG, MANAGER, "Manager")
        assign_customer(ORG, REVIEWER, "Reviewer")
        self.mail = patch("frappe.sendmail", return_value=frappe._dict(status="Sent", reload=lambda: None, send=lambda: None))
        self.mail.start()
        self.rate = patch("ia_maturity.grc.onboarding.limit")
        self.rate.start()
        self.auth_rate = patch("ia_maturity.grc.auth.limit")
        self.auth_rate.start()
        self.code_rate = patch("ia_maturity.grc.auth.code_request_limit")
        self.code_rate.start()
        self.addCleanup(self.mail.stop)
        self.addCleanup(self.rate.stop)
        self.addCleanup(self.auth_rate.stop)
        self.addCleanup(self.code_rate.stop)
        frappe.clear_cache()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def template(self, weighting="Points (equal question weight)", multi=False):
        frappe.set_user("Administrator")
        doc = frappe.copy_doc(frappe.get_doc("IA Maturity Template", SEED_TEMPLATE))
        doc.template_name = "_Test Scope Packages"
        doc.grc_published, doc.grc_policy = 0, ""
        # Use an actual allowed weighting value from this installed schema.
        options = frappe.get_meta(doc.doctype).get_field("weighting_method").options.splitlines()
        doc.weighting_method = next((v for v in options if v.startswith("Section" if weighting == "Section" else "Points")), options[0])
        doc.set("sections", [{"section_code": c, "section_title": c.upper(), "weight": i+1} for i,c in enumerate("abc")])
        rows = [q.as_dict() for q in doc.questions[:6]]
        for i,row in enumerate(rows):
            row.update(question_code=f"S{i+1}", section_code="abc"[i//2], auto_source="", is_gating=0, allow_na=1)
            if multi:
                row.update(selection_mode="Multi", multi_score_method="Average")
        doc.set("questions", rows)
        doc.insert(ignore_permissions=True)
        return assessments.publish(doc.name)

    def configuration(self, template):
        config = {"required_sections": ["a"], "packages": [
            {"code": "risk", "label": "Risk", "label_ar": "المخاطر", "description": "Assess risk", "description_ar": "تقييم المخاطر", "sections": ["b"]},
            {"code": "combined", "label": "Combined", "description": "Risk and compliance", "sections": ["b", "c"]}]}
        result = scope.save_scope_configuration(template.name, config)
        scope.publish_scope_configuration(result["name"], result["modified"])
        return result["name"]

    def assessment(self):
        template = self.template()
        self.configuration(template)
        frappe.set_user(CUSTOMER)
        return self.historical_assessment(template.name)

    def historical_assessment(self, template):
        """Replay a pre-journey IA scope snapshot, without changing new IA behavior.

        New IA drafts intentionally bypass package choice. These retained tests
        exercise the archived versioned scope and correction contract.
        """
        def historical_pin(doc):
            if not doc.is_new() or doc.get("grc_scope_snapshot") or doc.amended_from:
                return
            name = frappe.db.get_value(scope.CONFIG, {"template": doc.template, "published": 1}, "name", order_by="version desc")
            if name:
                config = frappe.get_doc(scope.CONFIG, name)
                doc.grc_scope_snapshot = frappe.as_json({**frappe.parse_json(config.configuration), "configuration": name, "version": config.version})
                doc.grc_scope_sections, doc.grc_selected_packages = "[]", "[]"
                doc.grc_scope_confirmed = 0
        with patch("ia_maturity.grc.scope.pin", side_effect=historical_pin):
            return assessments.new_assessment(ORG, template)

    def invite(self, email=CUSTOMER, company="_Test Invited Customer"):
        frappe.set_user(AUDITOR)
        token = "test-invitation-token-long-enough-123456"
        with patch("ia_maturity.grc.onboarding.secrets.token_urlsafe", return_value=token):
            result = onboarding.create_onboarding_invitation(email, company=company, assessment_type="Internal Audit")
        return result["name"], token

    def activate(self):
        name, token = self.invite()
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, "_Test Invited Customer", "Other")
        return name, result["entity"]


class TestAuditScope(ScopeOnboardingCase):
    def test_scoped_multiselect_na_and_all_na_denominators(self):
        template = self.template(multi=True)
        self.configuration(template)
        frappe.set_user(CUSTOMER)
        doc = self.historical_assessment(template.name)
        scope.confirm_assessment_scope(doc.name, [], doc.modified)
        assessments.save(doc.name, {"S1": {"selected_option": "A,D"}, "S2": {"selected_option": "N/A"}})
        doc.reload()
        self.assertEqual(doc.overall_score, 62.5)
        self.assertEqual(doc.max_points, 100)
        self.assertEqual(doc.na_count, 1)
        assessments.save(doc.name, {"S1": {"selected_option": "N/A"}})
        doc.reload()
        self.assertEqual(doc.overall_score, 0)
        self.assertEqual(doc.max_points, 0)
        self.assertEqual(doc.question_count, 2)
        assessments.submit(doc.name)
        self.assertEqual(frappe.db.count("IA Maturity Action", {"assessment": doc.name}), 0)

    def test_empty_required_scope_and_customer_only_initial_confirmation(self):
        template = self.template()
        config = {"required_sections": [], "packages": [{"code": "risk", "label": "Risk", "description": "Risk assessment", "sections": ["b"]}]}
        row = scope.save_scope_configuration(template.name, config)
        scope.publish_scope_configuration(row["name"], row["modified"])
        frappe.set_user(CUSTOMER)
        doc = self.historical_assessment(template.name)
        with self.assertRaises(frappe.ValidationError):
            scope.confirm_assessment_scope(doc.name, [], doc.modified)
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.PermissionError):
            scope.confirm_assessment_scope(doc.name, ["risk"], doc.modified)
        frappe.set_user(CUSTOMER)
        result = scope.confirm_assessment_scope(doc.name, ["risk"], doc.modified)
        self.assertEqual(result["question_count"], 2)

    def test_scope_is_retained_through_clarification_and_released_report(self):
        from ia_maturity.grc.administration import assign_assessment
        doc = self.assessment()
        scope.confirm_assessment_scope(doc.name, [], doc.modified)
        assessments.save(doc.name, {"S1": {"selected_option": "C"}, "S2": {"selected_option": "D"}})
        frappe.set_user(ADMIN)
        assign_assessment(doc.grc_assignment, consultant=AUDITOR, reviewer=REVIEWER)
        frappe.set_user(CUSTOMER)
        assessments.submit(doc.name)
        frappe.set_user(REVIEWER)
        assessments.transition(doc.name, "start_review")
        revision = assessments.transition(doc.name, "clarify", "Please confirm the governance responses")
        self.assertEqual(revision["scope"]["selected_sections"], ["a"])
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.PermissionError):
            scope.confirm_assessment_scope(revision["name"], ["risk"], revision["modified"], "Change coverage")
        frappe.set_user(CUSTOMER)
        assessments.submit(revision["name"])
        frappe.set_user(REVIEWER)
        assessments.transition(revision["name"], "start_review")
        assessments.transition(revision["name"], "approve")
        result = assessments.transition(revision["name"], "release")
        self.assertEqual(result["overall_score"], 87.5)
        release = frappe.get_doc("GRC Report Release", {"assessment": revision["name"]})
        context = frappe.parse_json(release.report_context)
        self.assertEqual(context["overall"], result["overall_score"])
        self.assertEqual(context["audit_scope"]["selected_sections"], ["a"])
        self.assertTrue(frappe.get_doc("File", release.pdf_file).get_content().startswith(b"%PDF"))

    def test_manager_can_publish_only_scope_and_versions_are_pinned(self):
        template = self.template()
        frappe.set_user(MANAGER)
        config = self.configuration(template)
        from ia_maturity.grc.administration import save_template
        with self.assertRaises(frappe.PermissionError):
            save_template({"template_name": "Unauthorized"}, template.name)
        doc = frappe.get_doc(scope.CONFIG, config)
        with scope.writing(), self.assertRaises(frappe.ValidationError):
            doc.configuration = "{}"
            doc.save(ignore_permissions=True)
        frappe.set_user(CUSTOMER)
        assessment = self.historical_assessment(template.name)
        frappe.set_user(MANAGER)
        saved = scope.save_scope_configuration(template.name, {"required_sections": ["b"], "packages": []})
        scope.publish_scope_configuration(saved["name"], saved["modified"])
        self.assertEqual(frappe.parse_json(assessment.grc_scope_snapshot)["configuration"], config)
        frappe.set_user(OTHER)
        with self.assertRaises(frappe.PermissionError):
            scope.scope_configurations(template.name)

    def test_confirmation_overlap_required_scope_and_write_boundaries(self):
        doc = self.assessment()
        self.assertEqual(doc.question_count, 0)
        with self.assertRaises(frappe.ValidationError):
            assessments.save(doc.name, {"S1": {"selected_option": "D"}})
        result = scope.confirm_assessment_scope(doc.name, ["risk", "combined"], doc.modified)
        self.assertEqual(result["question_count"], 6)
        result = assessments.save(doc.name, {"S1": {"selected_option": "D"}}, result["modified"])
        with self.assertRaises(frappe.PermissionError):
            scope.confirm_assessment_scope(doc.name, [], result["modified"])
        second = self.historical_assessment(doc.template)
        result = scope.confirm_assessment_scope(second.name, [], second.modified)
        self.assertEqual(result["question_count"], 2)
        with self.assertRaises(frappe.ValidationError):
            assessments.save(second.name, {"S3": {"selected_option": "A"}})
        result = assessments.save(second.name, {"S1": {"selected_option": "D"}, "S2": {"selected_option": "N/A"}})
        second.reload()
        self.assertEqual(second.overall_score, 100)
        self.assertEqual(second.max_points, 100)
        self.assertEqual(second.answered_count, 2)
        assessments.submit(second.name)
        self.assertEqual(frappe.db.count("IA Maturity Action", {"assessment": second.name}), 0)
        second.reload()
        from ia_maturity.report_data import get_report_context
        frappe.set_user(ADMIN)
        report = get_report_context(second, audience="internal")
        self.assertEqual(len(report["answers"]), 2)
        self.assertEqual([s["code"] for s in report["sections"]], ["a"])
        self.assertEqual([s["code"] for s in report["audit_scope"]["sections"] if not s["included"]], ["b", "c"])

    def test_admin_correction_preserves_answers_and_requires_customer_acknowledgement(self):
        doc = self.assessment()
        result = scope.confirm_assessment_scope(doc.name, ["risk"], doc.modified)
        result = assessments.save(doc.name, {"S3": {"selected_option": "A"}})
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.ValidationError):
            scope.confirm_assessment_scope(doc.name, [], result["modified"])
        result = scope.correct_assessment_scope(doc.name, [], result["modified"], "Customer requested baseline only")
        self.assertTrue(result["scope"]["acknowledgement_required"])
        doc.reload()
        self.assertEqual(next(a.selected_option for a in doc.answers if a.question_code == "S3"), "A")
        self.assertEqual(doc.findings_count, 0)
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.ValidationError):
            assessments.save(doc.name, {"S1": {"selected_option": "D"}})
        with self.assertRaises(frappe.PermissionError):
            scope.confirm_assessment_scope(doc.name, ["risk"], result["modified"])
        result = scope.confirm_assessment_scope(doc.name, [], result["modified"])
        self.assertTrue(result["editable"])
        frappe.set_user(ADMIN)
        result = scope.confirm_assessment_scope(doc.name, ["risk"], result["modified"], "Restore risk coverage")
        self.assertEqual(next(a["selected_option"] for a in result["questions"] if a["question_code"] == "S3"), "A")

    def test_invalid_scope_stale_save_and_legacy_compatibility(self):
        doc = self.assessment()
        with self.assertRaises(frappe.ValidationError):
            scope.confirm_assessment_scope(doc.name, ["forged"], doc.modified)
        with self.assertRaises(frappe.TimestampMismatchError):
            scope.confirm_assessment_scope(doc.name, [], "stale")
        legacy = assessments.new_assessment(ORG, SEED_TEMPLATE)
        self.assertFalse(legacy.grc_scope_snapshot)
        self.assertEqual(len(scope.answers(legacy)), len(legacy.answers))

    def test_section_weights_only_include_active_questions_and_gates(self):
        from ia_maturity.scoring import compute, get_config
        template = self.template("Section")
        self.configuration(template)
        frappe.set_user(CUSTOMER)
        doc = self.historical_assessment(template.name)
        scope.confirm_assessment_scope(doc.name, ["risk"], doc.modified)
        result = assessments.save(doc.name, {"S1": {"selected_option": "D"}, "S2": {"selected_option": "D"},
            "S3": {"selected_option": "B"}, "S4": {"selected_option": "B"}})
        doc.reload()
        self.assertEqual(doc.overall_score, 66.7)
        self.assertEqual(result["scoring"]["sections"], [{"code": "a", "weight": 1.0}, {"code": "b", "weight": 2.0}])
        doc.answers[4].update(dict(selected_option="A", is_gating=1, gate_trigger="A", gate_cap_level="Critical"))
        result = compute([a.as_dict() for a in scope.answers(doc)], scope.sections(doc, frappe.parse_json(doc.grc_sections_snapshot)), template.weighting_method, get_config(doc))
        self.assertFalse(result.gating_note)


class TestInvitedOnboarding(ScopeOnboardingCase):
    def test_new_customer_verification_retains_inviter_and_avoids_public_signup_bypass(self):
        email = "scope-new-recipient@example.test"
        name, token = self.invite(email)
        frappe.set_user("Guest")
        with patch("ia_maturity.grc.auth.secrets.randbelow", return_value=123456):
            auth.request_code(email, "Start", "New Recipient", consent=1, onboarding_token=token)
        reg = frappe.get_doc(auth.REG, {"email": email, "status": "Pending"})
        with patch("ia_maturity.grc.mfa.required", return_value=True):
            auth.consume(reg.name, code="123456")
        self.assertFalse(frappe.db.exists("GRC Organization Membership", {"user": email}))
        from ia_maturity.grc.organizations import create_verified_signup_organization
        create_verified_signup_organization(frappe._dict(grc_organization_signup=1, entity_name="_Test Bypass", grc_organization_sector="Other"), email)
        self.assertFalse(frappe.db.exists("IA Maturity Entity", "_Test Bypass"))
        frappe.set_user(email)
        result = onboarding.complete_onboarding(name, "_Test New Invited Recipient", "Other")
        self.assertEqual(frappe.db.get_value("IA Maturity Entity", result["entity"], "grc_auditor_owner"), AUDITOR)

    def test_native_mail_queue_failure_is_recorded_without_customer_progress(self):
        self.mail.stop()
        account = frappe.get_doc({"doctype": "Email Account", "name": "_Test Invitation Sender", "email_id": "invites@example.test", "enable_outgoing": 1, "default_outgoing": 1})
        with patch("frappe.email.doctype.email_account.email_account.EmailAccount.find_outgoing", return_value=account), patch("frappe.email.email_body.inline_style_in_html", side_effect=lambda html, **_kw: html), patch("frappe.email.doctype.email_queue.email_queue.EmailQueue.send", side_effect=AssertionError("No SMTP in tests")):
            name, token = self.invite()
            doc = frappe.get_doc(onboarding.DOCTYPE, name)
            self.assertEqual(onboarding.onboarding_detail(name)["delivery_status"], "Queued")
            queue = frappe.get_doc("Email Queue", doc.email_queue)
            queue.db_set("status", "Error")
            doc.reload()
            self.assertEqual(doc.delivery_status, "Failed")
            self.assertTrue(doc.unread_owner_event)
            self.assertFalse(doc.started_on)
            self.assertEqual(doc.status, "Invited")

    def test_pending_recipient_constraint_and_revoked_approval_cannot_activate(self):
        name, token = self.invite(company="_Test Revoked Activation")
        doc = frappe.copy_doc(frappe.get_doc(onboarding.DOCTYPE, name))
        doc.invited_by = OTHER
        with onboarding.writing(), self.assertRaises(frappe.UniqueValidationError):
            doc.insert(ignore_permissions=True)
        frappe.set_user(ADMIN)
        operations.operations_configure({"onboarding": True, "assignments": False, "stages": ["GRC App Admin"], "allow_self": False})
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        onboarding.complete_onboarding(name, "_Test Revoked Activation", "Other")
        request = frappe.db.get_value(onboarding.DOCTYPE, name, "approval_request")
        frappe.set_user(AUDITOR)
        onboarding.onboarding_invitation_action(name, "revoke", "Customer cancelled")
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.PermissionError):
            operations.operations_decide(request, "Approve")
        self.assertFalse(frappe.db.exists("IA Maturity Entity", "_Test Revoked Activation"))

    def test_creation_is_private_and_get_does_not_start_onboarding(self):
        name, token = self.invite()
        frappe.set_user("Guest")
        info = onboarding.onboarding_link(token)
        self.assertEqual(info["email"], CUSTOMER)
        self.assertFalse(frappe.db.get_value(onboarding.DOCTYPE, name, "started_on"))
        frappe.set_user(OTHER)
        self.assertEqual(onboarding.onboarding_invitations(), [])
        with self.assertRaises(frappe.PermissionError):
            onboarding.onboarding_detail(name)
        with self.assertRaises(frappe.ValidationError):
            onboarding.create_onboarding_invitation(CUSTOMER, company="_Test Invited Customer", assessment_type="Internal Audit")
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.PermissionError):
            onboarding.create_onboarding_invitation("forged@example.test")

    def test_atomic_activation_original_owner_and_access_lock(self):
        name, entity = self.activate()
        self.assertEqual(frappe.db.get_value("IA Maturity Entity", entity, "grc_auditor_owner"), AUDITOR)
        self.assertTrue(sec.can_access(entity, AUDITOR))
        self.assertTrue(sec.can_access(entity, ADMIN))
        # Department managers now retain their department queue/customer access.
        self.assertTrue(sec.can_access(entity, MANAGER))
        self.assertFalse(sec.can_access(entity, OTHER))
        self.assertEqual(onboarding.complete_onboarding(name, "Ignored", "Other")["entity"], entity)
        assessment = assessments.new_assessment(entity, SEED_TEMPLATE)
        self.assertEqual(frappe.db.get_value("GRC Assessment Assignment", assessment.grc_assignment, "consultant"), AUDITOR)
        frappe.set_user(MANAGER)
        self.assertIn(entity, sec.entities())
        from ia_maturity.grc import api
        self.assertEqual(api.assessment(assessment.name)["name"], assessment.name)
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.ValidationError):
            assign_customer(entity, MANAGER, "Manager")

    def test_admin_transfer_exceptions_and_revocation(self):
        name, entity = self.activate()
        assessment = assessments.new_assessment(entity, SEED_TEMPLATE)
        from frappe.utils.file_manager import save_file
        with sec.service_write():
            file = save_file("scope-private.txt", b"private scope evidence", assessment.doctype, assessment.name, is_private=1)
        frappe.set_user(ADMIN)
        current = ownership.customer_ownership(entity)
        ownership.set_customer_ownership(entity, AUDITOR, 1, [{"auditor": REVIEWER, "responsibility": "Reviewer"}], "Review requested", current["modified"])
        self.assertTrue(sec.can_access(entity, REVIEWER))
        current = ownership.customer_ownership(entity)
        ownership.set_customer_ownership(entity, OTHER, 1, [], "Auditor transfer", current["modified"])
        self.assertFalse(sec.can_access(entity, AUDITOR))
        self.assertFalse(sec.can_access(entity, REVIEWER))
        self.assertTrue(sec.can_access(entity, OTHER))
        self.assertEqual(frappe.db.get_value(onboarding.DOCTYPE, name, "invited_by"), AUDITOR)
        self.assertEqual(frappe.db.get_value("GRC Assessment Assignment", assessment.grc_assignment, "consultant"), OTHER)
        frappe.set_user(AUDITOR)
        with self.assertRaises(frappe.PermissionError):
            sec.check_file_url(file.file_url)
        with self.assertRaises(frappe.PermissionError):
            onboarding.onboarding_detail(name)
        self.assertNotIn(name, [row["name"] for row in onboarding.onboarding_invitations()])
        self.assertEqual(onboarding.owner_alert_count(), 0)

    def test_both_approval_stages_preserve_inviter(self):
        operations.operations_configure({"onboarding": True, "assignments": False, "stages": ["GRC App Admin"], "allow_self": False})
        name, token = self.invite(company="_Test Approved Invited Customer")
        self.assertEqual(frappe.db.get_value(onboarding.DOCTYPE, name, "status"), "Pending Invitation Approval")
        frappe.set_user(ADMIN)
        request = frappe.db.get_value(onboarding.DOCTYPE, name, "approval_request")
        operations.operations_decide(request, "Approve")
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, "_Test Approved Invited Customer", "Other")
        self.assertEqual(result["status"], "Awaiting Approval")
        self.assertFalse(frappe.db.exists("IA Maturity Entity", "_Test Approved Invited Customer"))
        frappe.set_user(ADMIN)
        request = frappe.db.get_value(onboarding.DOCTYPE, name, "approval_request")
        operations.operations_decide(request, "Approve")
        self.assertEqual(frappe.db.get_value("IA Maturity Entity", "_Test Approved Invited Customer", "grc_auditor_owner"), AUDITOR)

    def test_token_expiry_rotation_and_wrong_recipient(self):
        name, token = self.invite()
        with self.assertRaises(frappe.PermissionError):
            onboarding.registration_invitation("wrong@example.test", token)
        with patch("ia_maturity.grc.onboarding.secrets.token_urlsafe", return_value="replacement-long-token-1234567890"):
            onboarding.onboarding_invitation_action(name, "resend")
        with self.assertRaises(frappe.ValidationError):
            onboarding.from_token(token)
        frappe.db.set_value(onboarding.DOCTYPE, name, "expires_on", add_days(now_datetime(), -1))
        frappe.set_user(CUSTOMER)
        with self.assertRaises(frappe.ValidationError):
            onboarding.resume_onboarding(name)
        frappe.set_user(AUDITOR)
        self.assertEqual(onboarding.onboarding_detail(name)["status"], "Expired")
        onboarding.onboarding_invitation_action(name, "revoke", "Customer cancelled")
        with self.assertRaises(frappe.ValidationError):
            onboarding.onboarding_invitation_action(name, "resend")

    def test_verification_binding_survives_mfa_without_creating_an_unowned_organization(self):
        name, token = self.invite()
        frappe.set_user("Guest")
        with patch("ia_maturity.grc.auth.secrets.randbelow", return_value=123456):
            auth.request_code(CUSTOMER, "Start", "Scope Tester", consent=1, onboarding_token=token)
        reg = frappe.get_doc(auth.REG, frappe.db.get_value(auth.REG, {"email": CUSTOMER, "status": "Pending"}, "name"))
        self.assertEqual(reg.grc_onboarding_invitation, name)
        with patch("ia_maturity.grc.mfa.required", return_value=True):
            result = auth.consume(reg.name, code="123456")
        self.assertFalse(result.get("requires_mfa"))
        self.assertEqual(result["redirect"], "/grc/customer/onboarding")
        self.assertEqual(frappe.db.get_value(onboarding.DOCTYPE, name, "status"), "Email Verified")
        frappe.set_user(CUSTOMER)
        self.assertIn(name, [r["name"] for r in onboarding.customer_onboarding()])
        result = onboarding.complete_onboarding(name, "_Test MFA Invited Customer", "Other")
        self.assertEqual(frappe.db.get_value("IA Maturity Entity", result["entity"], "grc_auditor_owner"), AUDITOR)

    def test_tracker_blockers_and_saved_details_privacy(self):
        # The company is now pinned. Use a genuine nonmember-company blocker
        # instead of asking the customer to supply an empty company name.
        foreign = "_Test Unowned Tracker Company"
        with sec.service_write():
            frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": foreign}).insert(ignore_permissions=True)
        name, token = self.invite(company=foreign)
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, "", "")
        self.assertIn("validation_error", result)
        frappe.set_user(AUDITOR)
        detail = onboarding.onboarding_detail(name)
        self.assertTrue(detail["unread_owner_event"])
        self.assertTrue(detail["blocker"])
        self.assertNotIn("token_hash", detail)
        self.assertNotIn("data", detail)
        frappe.db.set_value(onboarding.DOCTYPE, name, {"last_activity_on": add_days(now_datetime(), -3), "blocker": ""})
        self.assertTrue(onboarding.onboarding_detail(name)["needs_attention"])

    def test_disabled_inviter_and_existing_organization_never_claim_customer(self):
        foreign = "_Test Existing Nonmember Invited Company"
        with sec.service_write():
            frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": foreign}).insert(ignore_permissions=True)
        name, token = self.invite(company=foreign)
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, ORG, "Other")
        self.assertIn("validation_error", result)
        self.assertFalse(frappe.db.get_value("IA Maturity Entity", ORG, "grc_auditor_owner"))
        frappe.db.set_value("User", AUDITOR, "enabled", 0)
        with self.assertRaises(frappe.ValidationError):
            onboarding.complete_onboarding(name, "_Test Disabled Inviter", "Other")

    def test_default_auto_lock_is_snapshotted(self):
        name, token = self.invite()
        frappe.set_user(ADMIN)
        ownership.save_ownership_settings(0, 72, "Future invitations can use shared assignments")
        self.assertEqual(frappe.db.get_value(onboarding.DOCTYPE, name, "auto_lock"), 1)
        frappe.set_user(CUSTOMER)
        onboarding.resume_onboarding(name)
        result = onboarding.complete_onboarding(name, "_Test Snapshot Lock", "Other")
        self.assertEqual(frappe.db.get_value("IA Maturity Entity", result["entity"], "grc_ownership_locked"), 1)
