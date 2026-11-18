"""Default-off response policy and report rendering regression tests."""
import unittest
from unittest.mock import patch
import frappe
from ia_maturity.grc.response_policy import flags_for_answer

class TestPresentation(unittest.TestCase):
    def test_default_off_overrides_existing_answer_flags(self):
        for value in (None, 0, "0"):
            with patch("frappe.get_cached_doc", return_value=frappe._dict(question_extras_enabled=value)):
                self.assertEqual(flags_for_answer({"allow_comment":1,"allow_attachment":1}), {"allow_comment":0,"allow_attachment":0})

    def test_admin_opt_in_retains_question_restrictions(self):
        with patch("frappe.get_cached_doc", return_value=frappe._dict(question_extras_enabled=1)):
            self.assertEqual(flags_for_answer({"allow_comment":0,"allow_attachment":1}), {"allow_comment":0,"allow_attachment":1})
            self.assertEqual(flags_for_answer({"allow_comment":1,"allow_attachment":0}), {"allow_comment":1,"allow_attachment":0})

    def test_report_a4_first_page_sections_and_escaping(self):
        from pathlib import Path
        from jinja2 import Environment
        from pypdf import PdfReader
        from io import BytesIO
        from ia_maturity.grc.pdf import render_html
        from ia_maturity.grc.report_fonts import report_font_css
        template = Path(__file__).parents[1] / "templates" / "grc_report.html"
        section = dict(title="Governance",pct=75,points=225,max_points=300,color="#287d32",level_label="High")
        context = dict(lang="en",dir="ltr",t=dict(results_report="RESULTS REPORT",title="Internal Audit Function Maturity Assessment",assessment_date="Assessment date",assessed_by="Assessed by",framework="Framework",framework_value="IIA Global Internal Audit Standards",exec_summary="Executive summary",strongest="Strongest section",weakest="Weakest section",results_by_section="Results by section",section="Section",points="Points",score="Score",maturity="Maturity",overall="Overall",scoring_method="Scoring method"),entity="<script>alert(1)</script>",date="21 Oct 2026",respondent="QA Auditor",questions_text="20 across 6 sections",show=dict(summary=True,sections=True,scoring_method=True),overall=75,level_label="High",level_color="#287d32",points_text="1500 of 2000 points",interpretation="Core practices are in place but require improvements to governance, methodology, reporting, assurance and technology. "*3,strongest=section,weakest=section,findings_text="No immediate findings.",sections=[section]*6,points=1500,max_points=2000,scoring_text="Answers score A = 25, B = 50, C = 75, D = 100. Section score divides awarded points by applicable maximum points. Gating questions cap the overall maturity at the trigger level. "*3)
        html=Environment().from_string(template.read_text()).render(r=context,font_css=report_font_css())
        self.assertNotIn("<script>",html)
        pdf=PdfReader(BytesIO(render_html(html)))
        self.assertEqual(len(pdf.pages),1)
        self.assertAlmostEqual(float(pdf.pages[0].mediabox.width),595.28,delta=1)
        self.assertAlmostEqual(float(pdf.pages[0].mediabox.height),841.89,delta=1)
        self.assertIn("Executive summary",pdf.pages[0].extract_text())
        self.assertIn("Results by section",pdf.pages[0].extract_text())
        self.assertIn("Scoring method",pdf.pages[0].extract_text())

    def test_report_palette_matches_grc_reference_without_mutating_scores(self):
        from ia_maturity.grc.report_style import report_context, PALETTE
        source={"overall":73.8,"level":"Medium","level_color":"#123456","sections":[{"level":level,"color":"#111111","pct":50} for level in PALETTE],"scale":[{"level":"Leading","color":"#111111","from":85}]}
        result=report_context(source)
        self.assertEqual(result["level_color"],"#9A6F00")
        self.assertEqual([s["color"] for s in result["sections"]],[PALETTE["Low"]]*len(PALETTE))
        self.assertEqual(result["scale"][0]["color"],"#1C5CA3")
        self.assertEqual(result["ticks"],[0,85,100])
        self.assertEqual(result["overall"],source["overall"])
        self.assertEqual(source["level_color"],"#123456")

    def test_missing_template_flags_default_to_disabled(self):
        from ia_maturity.grc.response_policy import resolve_flag
        for field in ("allow_comment","allow_attachment"):
            self.assertFalse(resolve_flag(None,None,{},field))
            self.assertTrue(resolve_flag({},None,{field:"Enabled"},field))

    def test_section_percentage_color_boundaries_ignore_maturity_labels(self):
        from ia_maturity.grc.report_style import report_context, section_score_color, SECTION_COLORS
        for score,key in [(0,"red"),(49.999,"red"),(50,"orange"),(74.999,"orange"),(75,"green"),(99.999,"green"),(100,"blue")]:
            with self.subTest(score=score):
                self.assertEqual(section_score_color(score),SECTION_COLORS[key])
                row=report_context({"sections":[{"pct":score,"level":"Medium"}]})["sections"][0]
                self.assertEqual(row["color"],SECTION_COLORS[key])
                self.assertEqual(row["level"],"Medium")

    def test_ten_custom_ranges_match_pdf_colors_at_every_boundary(self):
        from ia_maturity.grc.report_style import section_score_color,report_context
        ranges=[{"min_score":i*10,"color":"#%02X%02X%02X"%(i*20,50,100)} for i in range(10)]
        for i in range(10):
            for score in [i*10,i*10+9.99]:
                self.assertEqual(section_score_color(score,ranges),ranges[i]["color"])
        self.assertEqual(section_score_color(100,ranges),ranges[-1]["color"])
        frozen={"section_color_ranges":ranges,"sections":[{"pct":55}]}
        self.assertEqual(report_context(frozen,[{"min_score":0,"color":"#FFFFFF"}])["sections"][0]["color"],ranges[5]["color"])
