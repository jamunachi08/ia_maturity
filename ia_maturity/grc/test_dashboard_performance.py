"""SQL dashboard equivalence, bounded previews and live authorization regressions.

Run serially on the isolated muted GRC test site. Fixtures are synthetic and
transactional; no customer history, passwords or outgoing mail are used.
"""
from collections import Counter
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, cint, getdate, today

from ia_maturity.grc import assessments as svc, dashboard as optimized, departments as dept, security as sec
from ia_maturity.grc.administration import assign_customer
from ia_maturity.install import SEED_TEMPLATE


OWNER = "grc-perf-dashboard-owner@example.test"
CONTRIBUTOR = "grc-perf-dashboard-contributor@example.test"
OTHER = "grc-perf-dashboard-other@example.test"
AUDITOR = "grc-perf-dashboard-auditor@example.test"
MANAGER = "grc-perf-dashboard-manager@example.test"
ADMIN = "grc-perf-dashboard-admin@example.test"
ORG = "_Test Performance Dashboard Alpha"
OTHER_ORG = "_Test Performance Dashboard Beta"
CHILD = "_Test Performance Dashboard Child"


class TestDashboardPerformance(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        assert sec.enabled() and frappe.conf.get("mute_emails"), "Use the isolated muted GRC test site"
        with sec.service_write():
            for user, role in [(OWNER, "GRC Customer"), (CONTRIBUTOR, "GRC Customer"), (OTHER, "GRC Customer"),
                (AUDITOR, "GRC Auditor"), (MANAGER, "GRC Manager"), (ADMIN, "GRC App Admin")]:
                if not frappe.db.exists("User", user):
                    frappe.get_doc({"doctype": "User", "email": user, "first_name": "Dashboard",
                        "send_welcome_email": 0, "roles": [{"role": role}]}).insert(ignore_permissions=True)
            for entity in (ORG, OTHER_ORG, CHILD):
                if not frappe.db.exists("IA Maturity Entity", entity):
                    frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": entity}).insert(ignore_permissions=True)
            for entity, user, role in [(ORG, OWNER, "Organization Admin"), (ORG, CONTRIBUTOR, "Contributor"),
                (OTHER_ORG, OTHER, "Organization Admin"), (CHILD, OTHER, "Organization Admin")]:
                if not frappe.db.exists("GRC Organization Membership", {"entity": entity, "user": user}):
                    frappe.get_doc({"doctype": "GRC Organization Membership", "entity": entity, "user": user,
                        "membership_role": role, "active": 1}).insert(ignore_permissions=True)
        for entity in (ORG, OTHER_ORG, CHILD):
            dept.grant(entity, "Internal Audit", "Synthetic dashboard regression")
        dept.save_department_staff(AUDITOR, "Internal Audit", "Consultant")
        dept.save_department_staff(MANAGER, "Internal Audit", "Manager")
        assign_customer(ORG, AUDITOR, "Consultant")
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("GRC Settings", "results_visibility", "Preliminary scorecard")
        frappe.db.set_single_value("GRC Settings", "report_access_timing", "After Audit")
        frappe.flags.in_test = True

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache()

    def make(self, entity=ORG, owner=OWNER):
        frappe.set_user(owner)
        return svc.new_assessment(entity, SEED_TEMPLATE)

    def assignment(self, doc, state="Draft", due=None, respondent=None, needs=0):
        with sec.service_write():
            row = frappe.get_doc({"doctype": "GRC Assessment Assignment", "entity": doc.entity,
                "template": doc.template, "respondent": respondent or doc.respondent,
                "assessment": doc.name, "grc_department": "Internal Audit", "workflow_state": state,
                "due_date": due or add_days(today(), 7), "needs_reassignment": needs})
            row.insert(ignore_permissions=True)
        return row

    def event(self, doc, action, internal=0, department="Internal Audit", details=None):
        with sec.service_write():
            return frappe.get_doc({"doctype": "GRC Activity", "entity": doc.entity,
                "assessment": doc.name, "assignment": doc.grc_assignment, "actor": OWNER,
                "action": action, "internal": internal, "grc_department": department,
                "details": frappe.as_json(details or {})}).insert(ignore_permissions=True)

    def reference_assignments(self, entity=None, search=None, state=None, page=1, scorecards=0, group=None):
        """Pre-optimization selection algorithm retained as a semantic oracle."""
        allowed = sec.entities()
        if entity:
            sec.require_entity(entity)
            allowed = [entity]
        rows = frappe.get_all("GRC Assessment Assignment", filters={"entity": ["in", allowed or ["__none__"]]},
            fields=["*"], order_by="modified desc")
        if sec.account_type() == "Customer":
            rows = [row for row in rows if sec.effective_membership(row.entity) in optimized.BROAD_MEMBERSHIPS
                or row.respondent == frappe.session.user]
        rows = [row for row in rows if dept.can_read(row)]
        counts = dict(Counter(row.workflow_state for row in rows))
        overdue = sum(bool(row.due_date and getdate(row.due_date) < getdate(today())
            and row.workflow_state != "Report Released") for row in rows)
        if search:
            rows = [row for row in rows if search.lower().strip() in
                (row.entity + " " + (row.assessment or "") + " " + row.template).lower()]
        if state:
            rows = [row for row in rows if row.workflow_state == state]
        groups = {"in_progress": {"Draft", "In Progress"}, "awaiting_review": {"Submitted", "Resubmitted", "Under Review"},
            "released": {"Report Released"}}
        if group == "overdue":
            rows = [row for row in rows if row.due_date and getdate(row.due_date) < getdate(today())
                and row.workflow_state != "Report Released"]
        elif group in groups:
            rows = [row for row in rows if row.workflow_state in groups[group]]
        if cint(scorecards):
            rows = [row for row in rows if row.assessment and frappe.db.get_value(svc.DOCTYPE, row.assessment, "docstatus") == 1
                and svc.visible_results(frappe.get_doc(svc.DOCTYPE, row.assessment))]
        actionable = {"Submitted", "Resubmitted", "Under Review"} if sec.account_type() == "Auditor" else {
            "Draft", "In Progress", "Clarification Required"}
        rows.sort(key=lambda row: (row.workflow_state not in actionable,
            str((row.review_due_date if sec.account_type() == "Auditor" else row.due_date) or row.due_date or "9999-12-31")))
        return {"total": len(rows), "counts": counts, "overdue": overdue,
            "needs_reassignment": sum(cint(row.needs_reassignment) for row in rows),
            "names": [row.assessment for row in rows[(page - 1) * 15:page * 15]]}

    def test_database_filters_pagination_and_metrics_match_reference(self):
        first = self.make()
        for i in range(22):
            self.assignment(first, ["Draft", "Submitted", "Under Review", "Report Released"][i % 4],
                due=add_days(today(), i % 6 - 3), needs=i % 2)
        self.make(OTHER_ORG, OTHER)
        for user in (OWNER, CONTRIBUTOR, AUDITOR, MANAGER, ADMIN):
            frappe.set_user(user)
            for args in ({}, {"page": 2}, {"search": "alpha"}, {"search": "%_"}, {"state": "Submitted"},
                {"group": "in_progress"}, {"group": "awaiting_review"}, {"group": "overdue"}, {"scorecards": 1}):
                with self.subTest(user=user, args=args):
                    expected = self.reference_assignments(**args)
                    actual = optimized.dashboard(**args)
                    for key in ("total", "counts", "overdue", "needs_reassignment"):
                        self.assertEqual(actual[key], expected[key])
                    self.assertEqual([row["name"] for row in actual["assessments"]], expected["names"])
                    self.assertEqual(actual["page_size"], 15)
        frappe.set_user(OWNER)
        with self.assertRaises(frappe.PermissionError):
            optimized.dashboard(entity=OTHER_ORG)
        with self.assertRaises(frappe.ValidationError):
            optimized.dashboard(group="invented")

    def test_activity_preview_sanitizes_and_rechecks_department_revocation(self):
        doc = self.make()
        for i in range(16):
            self.event(doc, "Submitted", internal=i % 3 == 0)
        self.event(doc, "Answers changed", details={"changes": [{"question": "Q1", "before": "secret", "after": "value"}]})
        self.event(doc, "Internal review", internal=1, details={"comment": "staff secret"})
        other = self.make(OTHER_ORG, OTHER)
        self.event(other, "Submitted")
        frappe.set_user(OWNER)
        result = optimized.dashboard()
        self.assertEqual(len(result["recent_activity"]), 5)
        self.assertTrue(all(row.entity == ORG and row.action in optimized.MILESTONES for row in result["recent_activity"]))
        activity = optimized.activity()
        self.assertNotIn("staff secret", frappe.as_json(activity))
        change = next(row for row in activity if row.action == "Answers changed")
        self.assertEqual(frappe.parse_json(change.details), {"questions": ["Q1"]})
        self.assertTrue(all("T" in row.creation for row in activity))
        frappe.set_user(AUDITOR)
        self.assertGreater(len(optimized.activity()), 0)
        frappe.set_user("Administrator")
        dept.grant(ORG, "Internal Audit", "Revoke full-profile grant", profile_access=0)
        frappe.set_user(AUDITOR)
        self.assertEqual(optimized.activity(), [])
        self.assertEqual(optimized.dashboard()["total"], 0)
        self.assertEqual(optimized.dashboard()["recent_activity"], [])

    def test_assigned_action_visibility_and_five_row_preview(self):
        doc = self.make()
        with sec.service_write():
            for i in range(8):
                frappe.get_doc({"doctype": "IA Maturity Action", "entity": ORG, "assessment": doc.name,
                    "question_code": "Q1", "finding_title": "Synthetic overdue action", "assigned_to": CONTRIBUTOR,
                    "due_date": add_days(today(), -i - 1), "status": "Open"}).insert(ignore_permissions=True)
        frappe.set_user(CONTRIBUTOR)
        self.assertEqual(optimized.dashboard()["overdue_actions_count"], 0)
        frappe.db.set_value(svc.DOCTYPE, doc.name, "docstatus", 1)
        visible = optimized.dashboard()
        self.assertEqual(visible["overdue_actions_count"], 8)
        self.assertEqual(len(visible["overdue_actions"]), 5)
        self.assertTrue(all(row.assigned_to == CONTRIBUTOR for row in visible["overdue_actions"]))
        frappe.db.set_single_value("GRC Settings", "results_visibility", "Status only")
        self.assertEqual(optimized.dashboard()["overdue_actions_count"], 0)

    def test_holding_membership_and_empty_department_staff_are_isolated(self):
        child_doc = self.make(CHILD, OTHER)
        frappe.set_user("Administrator")
        with sec.service_write():
            entity = frappe.get_doc("IA Maturity Entity", CHILD)
            entity.parent_organization = ORG
            entity.save(ignore_permissions=True)
        frappe.set_user(OWNER)
        self.assertIn(child_doc.name, [row["name"] for row in optimized.dashboard()["assessments"]])
        frappe.set_user(CONTRIBUTOR)
        self.assertNotIn(child_doc.name, [row["name"] for row in optimized.dashboard()["assessments"]])
        frappe.set_user("Administrator")
        staff = frappe.db.get_value("GRC Department Staff", {"user": AUDITOR, "department": "Internal Audit"}, "name")
        frappe.db.set_value("GRC Department Staff", staff, "active", 0)
        frappe.set_user(AUDITOR)
        self.assertEqual(optimized.dashboard()["total"], 0)

    def test_assignment_and_activity_materialization_is_bounded(self):
        doc = self.make()
        for i in range(45):
            self.assignment(doc)
            self.event(doc, "Submitted")
        frappe.set_user(OWNER)
        original_sql = frappe.db.sql
        materialized = []

        def tracked(query, *args, **kwargs):
            result = original_sql(query, *args, **kwargs)
            sql = str(query)
            if "SELECT a.name,a.assessment,a.needs_reassignment" in sql or "SELECT v.name,v.entity,v.action" in sql:
                materialized.append((sql, len(result)))
            return result

        with patch.object(frappe.db, "sql", side_effect=tracked):
            result = optimized.dashboard()
        self.assertGreaterEqual(result["total"], 46)
        self.assertEqual(len(result["assessments"]), 15)
        self.assertEqual([length for _, length in materialized], [15, 5])
        self.assertTrue(all("LIMIT" in sql for sql, _ in materialized))
