"""Independent content, selected-scope and scoring acceptance for GRC46."""
from copy import deepcopy
from itertools import combinations
import unittest

import frappe
from ia_maturity.grc import scope, workbook
from ia_maturity.scoring import compute, band_for


class TestGRCInstrument(unittest.TestCase):
    def setUp(self):
        self.data = workbook.instrument()
        self.config = frappe._dict(workbook.published_policy())

    def answers(self, selected=None, letters="A"):
        rows = [q for q in self.data["questions"] if selected is None or q["section_code"] in selected]
        return [frappe._dict(**q, selected_option=letters[i % len(letters)]) for i, q in enumerate(rows)]

    def score(self, answers):
        included = {a.section_code for a in answers}
        return compute(answers, [s for s in self.data["sections"] if s["section_code"] in included], "Points (each question equal)", self.config)

    def test_exact_source_identity_content_and_topics(self):
        self.assertEqual(self.data["source"]["sha256"], workbook.SOURCE_HASH)
        self.assertEqual(set(self.data["source"]["sheets"]), set(workbook.REQUIRED_SHEETS))
        self.assertEqual(len(self.data["questions"]), 46)
        self.assertEqual(sum(bool(q["option_" + l]) for q in self.data["questions"] for l in "abcd"), 184)
        self.assertEqual(len({q["topic_code"] for q in self.data["questions"] if q["topic_code"]}), 13)
        self.assertEqual(self.data["questions"][0]["question_text"], "How confident is the organization in its understanding of its overall GRC maturity?")
        self.assertEqual(self.data["questions"][0]["source_ref"], "Questionnaire!A4:H4")
        self.assertEqual(self.data["questions"][-1]["source_ref"], "Questionnaire!A49:H49")
        self.assertFalse(self.data["arabic_content_approved"])

    def test_all_seven_scope_question_counts(self):
        expected = {frozenset(["Governance"]): 16, frozenset(["Risk"]): 19, frozenset(["Compliance"]): 15,
            frozenset(["Governance", "Risk"]): 33, frozenset(["Governance", "Compliance"]): 29,
            frozenset(["Risk", "Compliance"]): 32, frozenset(["Governance", "Risk", "Compliance"]): 46}
        for size in range(1, 4):
            for sections in combinations(("Governance", "Risk", "Compliance"), size):
                answers = self.answers(set(sections) | {"Awareness"}, "D")
                self.assertEqual(len(answers), expected[frozenset(sections)])
                self.assertEqual(self.score(answers).overall_score, 100)

    def test_independent_full_and_partial_scoring_examples(self):
        for letter, expected, level in [("A", 25, "Critical"), ("B", 50, "Low"), ("C", 75, "High"), ("D", 100, "Leading")]:
            result = self.score(self.answers(letters=letter))
            self.assertEqual(result.overall_score, expected)
            self.assertEqual(result.maturity_level, level)
        cycle = self.score(self.answers(letters="ABCD"))
        self.assertEqual(cycle.overall_points, 2825)
        self.assertEqual(cycle.max_points, 4600)
        self.assertEqual(cycle.overall_score, 61.4)
        self.assertEqual(cycle.maturity_level, "Medium")
        partial = self.answers({"Awareness", "Compliance"}, "D")
        partial[0].selected_option, partial[1].selected_option = "A", "B"
        result = self.score(partial)
        self.assertEqual((result.overall_points, result.max_points, result.overall_score), (1375, 1500, 91.7))
        self.assertEqual({s.section_code for s in result.sections}, {"Awareness", "Compliance"})

    def test_na_counts_as_answer_and_only_excludes_its_denominator(self):
        rows = self.answers({"Awareness", "Risk"}, "C")
        rows[0].selected_option = rows[1].selected_option = "N/A"
        result = self.score(rows)
        self.assertEqual((result.overall_points, result.max_points, result.overall_score), (1275, 1700, 75))
        self.assertEqual((result.answered_count, result.question_count, result.na_count), (19, 19, 2))
        self.assertEqual(result.sections[0].answered, 2)
        self.assertEqual(result.sections[0].max_points, 0)
        rows[0].selected_option = ""
        result = self.score(rows)
        self.assertEqual((result.answered_count, result.max_points, result.overall_score), (18, 1800, 70.8))
        for row in rows:
            row.selected_option = "N/A"
        result = self.score(rows)
        self.assertEqual((result.answered_count, result.max_points, result.overall_score), (19, 0, 0))

    def test_gating_is_disabled_and_topic_results_follow_chosen_sections(self):
        rows = self.answers({"Awareness", "Risk"}, "D")
        rows[0].update(selected_option="A", is_gating=1, gate_cap_level="Critical")
        result = self.score(rows)
        self.assertEqual(result.maturity_level, "Leading")
        self.assertFalse(result.gating_note)
        self.assertEqual({t["section_code"] for t in result.topics}, {"Risk"})
        self.assertEqual(sum(t["question_count"] for t in result.topics), 17)
        for score, level in [(34.99, "Critical"), (35, "Low"), (54.99, "Low"), (55, "Medium"), (74.99, "Medium"), (75, "High"), (89.99, "High"), (90, "Leading")]:
            self.assertEqual(band_for(score, self.config.bands)["level_name"], level)

    def test_invalid_content_is_rejected_before_publication(self):
        for mutate in [lambda d: d["questions"].pop(), lambda d: d["questions"][1].update(question_code="Q1"),
            lambda d: d["questions"][0].update(section_code="Risk"), lambda d: d["questions"][0].update(option_a=""),
            lambda d: d["bands"][1].update(min_score=30), lambda d: d["source"].update(sha256="")]:
            changed = deepcopy(self.data); mutate(changed)
            with self.assertRaises(ValueError):
                workbook.validate_instrument(changed)

    def scope_doc(self, invited=None):
        config = {"required_sections": ["Awareness"], "packages": [{"code": c, "sections": [c]} for c in ("Risk", "Compliance", "Governance")]}
        return frappe._dict(grc_assessment_type="GRC", grc_scope_snapshot=frappe.as_json(config),
            grc_invited_sections=frappe.as_json(invited or []), answers=self.answers(), grc_scope_sections='["Awareness","Risk"]', grc_scope_confirmed=1)

    def test_optional_minimum_and_invitation_minima_cannot_be_removed(self):
        doc = self.scope_doc(["Awareness", "Risk"])
        with self.assertRaises(frappe.ValidationError):
            scope.resolve(doc, [])
        with self.assertRaises(frappe.ValidationError):
            scope.resolve(doc, ["Compliance"])
        self.assertEqual(scope.resolve(doc, ["Risk", "Compliance"])[1], ["Awareness", "Compliance", "Risk"])
        with self.assertRaises(frappe.ValidationError):
            scope.resolve(doc, ["Fabricated"])

    def test_scope_lock_is_derived_from_saved_answers(self):
        doc = self.scope_doc()
        for row in doc.answers:
            row.selected_option = ""
        self.assertFalse(scope.has_saved_answers(doc))
        doc.answers[0].selected_option = "N/A"
        self.assertTrue(scope.has_saved_answers(doc))
        scope.lock_on_first_answer(doc)
