"""Scoring engine for the IA Maturity Assessment.

Pure functions (no database writes) so the same logic serves the desk form,
the portal API, the print format and the tests.

Default method mirrors the client's workbook:
    A=25, B=50, C=75, D=100 points
    Section %  = points / (applicable questions x max points)
    Overall %  = total points / total max points   ("Points" weighting)
             or  sum(section % x weight) / sum(weight)   ("Section Weights")
    Bands: Critical <35, Low <55, Medium <75, High <90, Leading >=90
Extensions over the workbook: N/A answers (excluded from the denominator) and
gating questions (a weak answer caps the overall maturity level).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

LETTERS = ("A", "B", "C", "D")
LEVEL_NAMES = {"A": "Ad hoc", "B": "Foundational", "C": "Established", "D": "Leading"}
NA = "N/A"

DEFAULT_POINTS = {"A": 25.0, "B": 50.0, "C": 75.0, "D": 100.0}

DEFAULT_BANDS = [
	{
		"level_name": "Critical",
		"min_score": 0,
		"max_score": 34.99,
		"color": "#B42318",
		"interpretation": "Significant gaps exist across the Internal Audit function. Immediate attention is "
		"required to establish foundational practices.",
	},
	{
		"level_name": "Low",
		"min_score": 35,
		"max_score": 54.99,
		"color": "#BF530B",
		"interpretation": "Foundational practices exist but are inconsistently applied. Significant improvement "
		"is needed to ensure effectiveness.",
	},
	{
		"level_name": "Medium",
		"min_score": 55,
		"max_score": 74.99,
		"color": "#9A6F00",
		"interpretation": "Core practices are in place and generally effective. Enhancements are needed to "
		"achieve best-in-class standards.",
	},
	{
		"level_name": "High",
		"min_score": 75,
		"max_score": 89.99,
		"color": "#2D7A33",
		"interpretation": "The Internal Audit function is robust and aligned with international best practices. "
		"Continuous improvement remains a focus.",
	},
	{
		"level_name": "Leading",
		"min_score": 90,
		"max_score": 100,
		"color": "#1C5CA3",
		"interpretation": "The function is a benchmark for excellence, with advanced practices and independent "
		"validation.",
	},
]

PRIORITY = {
	"A": ("Immediate", "0–3 months", 90),
	"B": ("High", "3–6 months", 180),
	"C": ("Medium", "6–12 months", 365),
}


def get_config():
	"""Return scoring configuration from IA Maturity Settings (with safe defaults)."""
	settings = frappe.get_cached_doc("IA Maturity Settings")
	points = {
		"A": flt(settings.points_a) if settings.points_a is not None else DEFAULT_POINTS["A"],
		"B": flt(settings.points_b) if settings.points_b is not None else DEFAULT_POINTS["B"],
		"C": flt(settings.points_c) if settings.points_c is not None else DEFAULT_POINTS["C"],
		"D": flt(settings.points_d) or DEFAULT_POINTS["D"],
	}
	bands = [
		{
			"level_name": b.level_name,
			"min_score": flt(b.min_score),
			"max_score": flt(b.max_score),
			"color": b.color or "#586976",
			"interpretation": b.interpretation or "",
		}
		for b in (settings.bands or [])
		if b.level_name
	]
	if not bands:
		bands = [dict(b) for b in DEFAULT_BANDS]
	bands.sort(key=lambda b: b["min_score"])
	return frappe._dict(
		points=points,
		max_points=max(points.values()),
		bands=bands,
		create_actions_for=settings.create_actions_for or "A and B",
		evidence_required_from=settings.evidence_required_from or "",
	)


def band_for(pct, bands):
	"""Highest band whose min_score <= pct."""
	chosen = bands[0]
	for band in bands:
		if flt(pct) + 1e-9 >= flt(band["min_score"]):
			chosen = band
	return chosen


def band_index(level_name, bands):
	for i, b in enumerate(bands):
		if (b["level_name"] or "").lower() == (level_name or "").strip().lower():
			return i
	return None


def gate_letters(trigger):
	return {"A", "B"} if (trigger or "A").strip() == "A or B" else {"A"}


def compute(answers, sections, weighting_method=None, config=None):
	"""Score a set of answers.

	answers:  iterable of dict-likes with section_code, question_code, selected_option and
	          (optionally) is_gating, gate_trigger, gate_cap_level, short_label
	sections: ordered iterable of dict-likes with section_code, section_title, weight, reference
	Returns a frappe._dict with section rows, overall figures and gating information.
	"""
	config = config or get_config()
	answers = list(answers)
	pts, max_pt, bands = config.points, config.max_points, config.bands

	sec_rows = []
	by_code = {}
	for s in sections:
		row = frappe._dict(
			section_code=s.get("section_code"),
			section_title=s.get("section_title"),
			reference=s.get("reference") or "",
			weight=flt(s.get("weight")) if s.get("weight") not in (None, "") else 1.0,
			answered=0,
			applicable=0,
			points=0.0,
			max_points=0.0,
			score_pct=0.0,
			maturity_level="",
			question_count=0,
		)
		sec_rows.append(row)
		by_code[row.section_code] = row

	answered = applicable = na = findings = immediate = 0
	total_pts = total_max = 0.0
	gate_hits = []

	for a in answers:
		sec = by_code.get(a.get("section_code"))
		opt = (a.get("selected_option") or "").strip()
		if sec is not None:
			sec.question_count += 1
		if not opt:
			# unanswered still counts in the denominator (same as the workbook) until submission
			if sec is not None:
				sec.applicable += 1
				sec.max_points += max_pt
			applicable += 1
			total_max += max_pt
			continue
		answered += 1
		if opt == NA:
			na += 1
			continue
		p = pts.get(opt, 0.0)
		applicable += 1
		total_pts += p
		total_max += max_pt
		if sec is not None:
			sec.answered += 1
			sec.applicable += 1
			sec.points += p
			sec.max_points += max_pt
		if opt in ("A", "B"):
			findings += 1
		if opt == "A":
			immediate += 1
		if cint(a.get("is_gating")) and opt in gate_letters(a.get("gate_trigger")) and a.get("gate_cap_level"):
			gate_hits.append((a.get("question_code"), a.get("short_label") or "", opt, a.get("gate_cap_level")))

	for sec in sec_rows:
		sec.score_pct = round(sec.points / sec.max_points * 100, 1) if sec.max_points else 0.0
		sec.maturity_level = band_for(sec.score_pct, bands)["level_name"] if sec.max_points else "N/A"

	if (weighting_method or "").startswith("Section"):
		scored = [s for s in sec_rows if s.max_points and s.weight > 0]
		wsum = sum(s.weight for s in scored)
		overall = round(sum(s.score_pct * s.weight for s in scored) / wsum, 1) if wsum else 0.0
	else:
		overall = round(total_pts / total_max * 100, 1) if total_max else 0.0

	score_band = band_for(overall, bands)
	final_band = score_band
	gating_note = ""
	if gate_hits:
		score_idx = band_index(score_band["level_name"], bands)
		cap_idx = None
		trigger = None
		for hit in gate_hits:
			idx = band_index(hit[3], bands)
			if idx is not None and (cap_idx is None or idx < cap_idx):
				cap_idx, trigger = idx, hit
		if cap_idx is not None and score_idx is not None and score_idx > cap_idx:
			final_band = bands[cap_idx]
			gating_note = _(
				"Overall level capped at {0} because gating question {1} ({2}) was answered {3}. "
				"The score alone would indicate {4}."
			).format(final_band["level_name"], trigger[0], trigger[1], trigger[2], score_band["level_name"])

	return frappe._dict(
		sections=sec_rows,
		overall_score=overall,
		overall_points=total_pts,
		max_points=total_max,
		score_level=score_band["level_name"],
		maturity_level=final_band["level_name"],
		interpretation=final_band["interpretation"],
		color=final_band["color"],
		gating_note=gating_note,
		answered_count=answered,
		question_count=len(answers),
		na_count=na,
		findings_count=findings,
		immediate_count=immediate,
		bands=bands,
		points=pts,
	)
