# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT

import frappe
try:  # Frappe v16+
	from frappe.tests import IntegrationTestCase as BaseTestCase
except ImportError:  # Frappe v15
	from frappe.tests.utils import FrappeTestCase as BaseTestCase

from ia_maturity.install import SEED_TEMPLATE, after_install

ENTITY = "_Test IA Entity"


def make_assessment(answers, submit=False, **kw):
	"""answers: str of 20 letters (e.g. 'C'*20) or dict {code: letter}."""
	doc = frappe.get_doc(
		{
			"doctype": "IA Maturity Assessment",
			"entity": ENTITY,
			"template": SEED_TEMPLATE,
			"assessment_date": "2026-10-01",
			**kw,
		}
	)
	doc.load_questions()
	if isinstance(answers, str):
		answers = {row.question_code: answers[i] for i, row in enumerate(doc.answers) if i < len(answers)}
	for row in doc.answers:
		if row.question_code in answers:
			row.selected_option = answers[row.question_code]
	doc.insert()
	if submit:
		doc.submit()
	return doc


class TestIAMaturityAssessment(BaseTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("IA Maturity Template", SEED_TEMPLATE):
			after_install()
		if not frappe.db.exists("IA Maturity Entity", ENTITY):
			frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": ENTITY}).insert()

	def test_seed_matches_workbook(self):
		t = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
		self.assertEqual(len(t.sections), 6)
		self.assertEqual(len(t.questions), 20)
		per_section = [sum(1 for q in t.questions if q.section_code == s.section_code) for s in t.sections]
		self.assertEqual(per_section, [3, 3, 3, 4, 4, 3])

	def test_all_c_is_75_high(self):
		doc = make_assessment("C" * 20)
		self.assertEqual(doc.overall_score, 75.0)
		self.assertEqual(doc.maturity_level, "High")
		self.assertEqual(doc.overall_points, 1500)
		self.assertEqual(doc.max_points, 2000)

	def test_all_a_is_25_critical(self):
		doc = make_assessment("A" * 20)
		self.assertEqual(doc.overall_score, 25.0)
		self.assertEqual(doc.maturity_level, "Critical")
		self.assertEqual(doc.findings_count, 20)
		self.assertEqual(doc.immediate_count, 20)

	def test_mixed_matches_excel_formula(self):
		pattern = "BACD" * 5  # Q1 must not be A (gating question)
		doc = make_assessment(pattern)
		pts = {"A": 25, "B": 50, "C": 75, "D": 100}
		expected = round(sum(pts[c] for c in pattern) / 2000 * 100, 1)
		self.assertEqual(doc.overall_score, expected)  # 62.5 -> Medium
		self.assertEqual(doc.maturity_level, "Medium")
		s1 = next(s for s in doc.section_scores if s.section_code == "S1")
		self.assertEqual(s1.points, 50 + 25 + 75)
		self.assertAlmostEqual(s1.score_pct, 50.0)

	def test_gating_caps_level(self):
		answers = "A" + "D" * 19  # (25 + 1900) / 2000 = 96.25% -> Leading by score
		doc = make_assessment(answers)
		self.assertEqual(doc.score_level, "Leading")
		self.assertEqual(doc.maturity_level, "Low")
		self.assertIn("Q1", doc.gating_note)

	def test_not_applicable_excluded(self):
		doc = make_assessment({**{f"Q{i}": "C" for i in range(1, 20)}, "Q20": "N/A"})
		self.assertEqual(doc.na_count, 1)
		self.assertEqual(doc.max_points, 1900)
		self.assertEqual(doc.overall_score, 75.0)
		s6 = next(s for s in doc.section_scores if s.section_code == "S6")
		self.assertEqual(s6.max_points, 200)

	def test_na_not_allowed_on_other_questions(self):
		with self.assertRaises(frappe.ValidationError):
			make_assessment({"Q1": "N/A"})

	def test_incomplete_cannot_submit(self):
		doc = make_assessment("C" * 19)
		with self.assertRaises(frappe.ValidationError):
			doc.submit()

	def test_submit_creates_actions_and_review_status(self):
		doc = make_assessment("AB" + "C" * 18, submit=True)
		self.assertEqual(doc.review_status, "Pending Review")
		actions = frappe.get_all(
			"IA Maturity Action", filters={"assessment": doc.name}, fields=["question_code", "priority", "due_date"]
		)
		self.assertEqual({a.question_code: a.priority for a in actions}, {"Q1": "Immediate", "Q2": "High"})
		doc.cancel()
		self.assertEqual(
			set(frappe.get_all("IA Maturity Action", filters={"assessment": doc.name}, pluck="status")), {"Cancelled"}
		)

	def test_section_weighting(self):
		t = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
		t.weighting_method = "Section Weights"
		t.save()
		try:
			# S1 all D (100%), everything else A (25%): equal section weights -> (100 + 5*25) / 6 = 37.5
			answers = {q.question_code: ("D" if q.section_code == "S1" else "A") for q in t.questions}
			answers["Q1"] = "D"
			doc = make_assessment(answers)
			self.assertEqual(doc.overall_score, 37.5)
		finally:
			t.reload()
			t.weighting_method = "Points (each question equal)"
			t.save()

	def test_print_format_renders(self):
		doc = make_assessment("BC" * 10, submit=True)
		html = frappe.get_print("IA Maturity Assessment", doc.name, print_format="IA Maturity Report", doc=doc)
		self.assertIn("Executive summary", html)
		self.assertIn("<svg", html)
		self.assertIn(ENTITY, html)

	def test_return_to_respondent(self):
		from ia_maturity.ia_maturity.doctype.ia_maturity_assessment.ia_maturity_assessment import (
			return_to_respondent,
		)

		doc = make_assessment("C" * 20, submit=True, respondent="test@example.com")
		new_name = return_to_respondent(doc.name, "Please attach evidence for Q4")
		doc.reload()
		self.assertEqual(doc.docstatus, 2)
		self.assertEqual(doc.review_status, "Returned")
		new = frappe.get_doc("IA Maturity Assessment", new_name)
		self.assertEqual(new.docstatus, 0)
		self.assertEqual(new.amended_from, doc.name)
		self.assertEqual(new.owner, "test@example.com")
		self.assertEqual(new.answered_count, 20)

	def test_respondent_role_only_for_self_signup(self):
		frappe.db.set_single_value("IA Maturity Settings", "auto_assign_respondent_role", 1)

		def new_user(email):
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=True)
			user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "T", "send_welcome_email": 0})
			user.flags.ignore_permissions = True
			user.insert()
			return frappe.get_roles(email)

		self.assertNotIn("IA Assessment Respondent", new_user("_staff_made@example.com"))
		frappe.set_user("Guest")
		try:
			roles = new_user("_self_signup@example.com")
		finally:
			frappe.set_user("Administrator")
		self.assertIn("IA Assessment Respondent", roles)

	def test_reviewer_can_review_but_not_edit(self):
		from ia_maturity.ia_maturity.doctype.ia_maturity_assessment.ia_maturity_assessment import update_review

		email = "_ia_reviewer@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Rev", "send_welcome_email": 0})
			user.flags.ignore_permissions = True
			user.insert()
			user.add_roles("IA Maturity Reviewer")
		doc = make_assessment("C" * 20, submit=True)
		frappe.set_user(email)
		try:
			self.assertFalse(frappe.has_permission("IA Maturity Assessment", "write", doc.name))
			result = update_review(doc.name, "Approved", "Looks good")
		finally:
			frappe.set_user("Administrator")
		doc.reload()
		self.assertEqual(result["review_status"], "Approved")
		self.assertEqual(doc.review_status, "Approved")
		self.assertEqual(doc.reviewer, email)
		self.assertEqual(doc.reviewer_comments, "Looks good")

	# ------------------------------------------------------------------ Arabic / RTL
	def test_arabic_seed_and_report(self):
		t = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
		q1 = next(q for q in t.questions if q.question_code == "Q1")
		self.assertTrue(q1.question_text_ar and q1.option_d_ar)
		self.assertTrue(all(s.section_title_ar for s in t.sections))
		bands = frappe.get_single("IA Maturity Settings").bands
		self.assertEqual({b.level_name: b.level_name_ar for b in bands}["High"], "مرتفع")

		from ia_maturity.report_data import get_report_context

		doc = make_assessment("A" + "D" * 19, submit=True, language="ar")
		ctx = get_report_context(doc)
		self.assertEqual(ctx["dir"], "rtl")
		self.assertEqual(ctx["level_label"], "منخفض")  # gated to Low
		self.assertIn("السؤال الحاكم", ctx["gating_note"])
		self.assertEqual(ctx["sections"][0]["title"], "الحوكمة والاستقلالية والأخلاقيات")
		self.assertEqual(ctx["t"]["exec_summary"], "الملخص التنفيذي")
		self.assertEqual(get_report_context(doc, "en")["level_label"], "Low")

		html = frappe.get_print("IA Maturity Assessment", doc.name, print_format="IA Maturity Report", doc=doc)
		self.assertIn('dir="rtl"', html)
		self.assertIn("تقييم نضج وظيفة التدقيق الداخلي", html)
		self.assertIn("IAM Arabic", html)

	# ------------------------------------------------------------------ Q13 from the issue register
	def _make_issues(self, entity, count, months_to_close):
		from frappe.utils import add_days, add_months, today

		for i in range(count):
			closed = add_days(today(), -10 - i)
			frappe.get_doc(
				{
					"doctype": "IA Audit Issue",
					"title": f"Issue {i}",
					"entity": entity,
					"raised_on": add_months(closed, -months_to_close),
					"status": "Closed",
					"closed_on": closed,
				}
			).insert()

	def _entity(self, name, sector=None):
		if not frappe.db.exists("IA Maturity Entity", name):
			frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": name, "sector": sector}).insert()
		return name

	def test_q13_calculated_from_issue_register(self):
		from frappe.utils import today

		entity = self._entity("_Test Issue Entity A")
		self._make_issues(entity, 6, 7)  # ~7 months to close -> C (above 6, not above 9)
		doc = make_assessment("C" * 20, entity=entity, assessment_date=today())
		q13 = next(a for a in doc.answers if a.question_code == "Q13")
		self.assertEqual(q13.auto_source, "Issue Closure Time")
		self.assertTrue(q13.auto_calculated)
		self.assertEqual(q13.selected_option, "C")
		self.assertIn("6 issues closed", q13.auto_note)
		self.assertIn("محسوبة من سجل الملاحظات", q13.auto_note_ar)

		# respondents cannot override a locked, calculated answer through the portal API
		from ia_maturity.api import save_assessment

		res = save_assessment({"name": doc.name, "answers": {"Q13": {"selected": "D"}}})
		self.assertEqual(next(q for q in res["questions"] if q["code"] == "Q13")["selected"], "C")
		self.assertTrue(next(q for q in res["questions"] if q["code"] == "Q13")["locked"])

	def test_q13_manual_when_too_few_issues(self):
		from frappe.utils import today

		entity = self._entity("_Test Issue Entity B")
		self._make_issues(entity, 3, 14)
		doc = make_assessment({}, entity=entity, assessment_date=today())
		q13 = next(a for a in doc.answers if a.question_code == "Q13")
		self.assertFalse(q13.auto_calculated)
		self.assertFalse(q13.selected_option)
		self.assertIn("answered manually", q13.auto_note)

	def test_issue_closure_thresholds(self):
		from ia_maturity.issues import letter_for

		self.assertEqual(
			[letter_for(m) for m in (13, 12, 10, 9, 7, 6, 2)], ["A", "B", "B", "C", "C", "D", "D"]
		)

	# ------------------------------------------------------------------ benchmarking
	def test_peer_benchmark_respects_minimum_and_ranks(self):
		from ia_maturity.benchmark import peer_benchmark
		from ia_maturity.report_data import get_report_context

		base = frappe.get_doc("IA Maturity Template", SEED_TEMPLATE)
		tmpl_name = "_Test Benchmark Template"
		if not frappe.db.exists("IA Maturity Template", tmpl_name):
			tmpl = frappe.copy_doc(base)
			tmpl.template_name = tmpl_name
			for q in tmpl.questions:
				q.auto_source = None
			tmpl.insert()

		def submitted(entity, letters):
			return make_assessment(letters, submit=True, entity=self._entity(entity), template=tmpl_name)

		mine = submitted("_Test Bench Me", "C" * 20)  # 75 %
		for i, letters in enumerate(["B" * 20, "B" * 20, "C" * 20, "D" * 20]):
			submitted(f"_Test Bench Peer {i}", letters)
		bm = peer_benchmark(mine)
		self.assertEqual(bm.peer_count, 4)
		self.assertFalse(bm.available)  # 4 peers < minimum of 5
		self.assertIn("5", get_report_context(mine, "en")["benchmark"]["message"])

		submitted("_Test Bench Peer 4", "A" * 20)
		bm = peer_benchmark(mine)
		self.assertTrue(bm.available)
		# peers: 50, 50, 75, 100, 25 -> median 50; 3 below, 1 equal -> (3 + 0.5) / 5 = 70th percentile
		self.assertEqual(bm.overall.median, 50)
		self.assertEqual(bm.overall.percentile, 70)
		self.assertEqual(len(bm.sections), 6)
		self.assertNotIn("min", bm.overall)
		self.assertNotIn("max", bm.overall)

		# only the latest submission per entity counts
		submitted("_Test Bench Peer 4", "D" * 20)
		self.assertEqual(peer_benchmark(mine).overall.median, 75)

	# ------------------------------------------------------------------ client vs internal report
	def test_client_report_shows_only_enabled_sections(self):
		from ia_maturity.report_data import get_report_context

		doc = make_assessment("AB" + "C" * 18, submit=True)
		client = get_report_context(doc, "en", audience="client")
		self.assertEqual(
			client["show"],
			{
				"summary": True,
				"sections": True,
				"benchmark": True,
				"findings": False,
				"roadmap": False,
				"responses": False,
				"reviewer_comments": False,
				"scoring_method": False,
			},
		)
		# hidden sections' data is not sent at all
		self.assertEqual(client["findings"], [])
		self.assertEqual(client["actions"], [])
		self.assertEqual(client["answers"], [])
		self.assertEqual(client["scoring_text"], "")
		self.assertEqual(client["internal_banner"], "")

		internal = get_report_context(doc, "en", audience="internal")
		self.assertTrue(all(internal["show"].values()))
		self.assertEqual(len(internal["findings"]), 2)
		self.assertEqual(len(internal["answers"]), 20)
		self.assertIn("INTERNAL", internal["internal_banner"])

		frappe.db.set_single_value("IA Maturity Settings", "client_show_findings", 1)
		try:
			self.assertEqual(len(get_report_context(doc, "en", audience="client")["findings"]), 2)
		finally:
			frappe.db.set_single_value("IA Maturity Settings", "client_show_findings", 0)

	def test_print_formats_client_and_internal(self):
		doc = make_assessment("AB" + "C" * 18, submit=True)
		client = frappe.get_print("IA Maturity Assessment", doc.name, print_format="IA Maturity Report", doc=doc)
		self.assertIn("Executive summary", client)
		self.assertIn("Results by section", client)
		for hidden in ("Key findings", "Improvement roadmap", "Detailed responses", "Scoring method", "INTERNAL"):
			self.assertNotIn(hidden, client)

		internal = frappe.get_print(
			"IA Maturity Assessment", doc.name, print_format="IA Maturity Internal Report", doc=doc
		)
		for shown in ("INTERNAL", "Key findings", "Improvement roadmap", "Detailed responses", "Scoring method"):
			self.assertIn(shown, internal)

	def test_respondent_cannot_render_internal_report(self):
		email = "_ia_respondent@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Resp", "send_welcome_email": 0, "user_type": "Website User"}
			)
			user.flags.ignore_permissions = True
			user.insert()
			user.add_roles("IA Assessment Respondent")
		doc = make_assessment("C" * 20, submit=True)
		frappe.set_user(email)
		try:
			with self.assertRaises((frappe.PermissionError, frappe.PrintFormatError)):
				frappe.get_print("IA Maturity Assessment", doc.name, print_format="IA Maturity Internal Report", doc=doc)
		finally:
			frappe.set_user("Administrator")
