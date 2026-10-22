# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT

import frappe
from frappe.tests.utils import FrappeTestCase

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


class TestIAMaturityAssessment(FrappeTestCase):
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
