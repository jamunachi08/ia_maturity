"""Scoring engine for the IA Maturity Assessment.

Pure functions (no database writes) so the same logic serves the desk form,
the portal API, the print format and the tests.

Default method mirrors the client's workbook:
    A=25, B=50, C=75, D=100 points
    Section %  = points / (applicable questions x max points)
    Overall %  = total points / total max points   ("Points" weighting)
             or  sum(section % x weight) / sum(weight)   ("Section Weights")
    Bands (suggested score-to-maturity mapping):
        Critical 0–29, Low 30–49, Medium 50–69, High 70–84, Leading 85–100
    The executive-summary narrative is the conclusion for that overall mark.
Extensions over the workbook: N/A answers (excluded from the denominator) and
gating questions (a weak answer caps the overall maturity level).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

LETTERS = ("A", "B", "C", "D")
LETTER_AR = {"A": "أ", "B": "ب", "C": "ج", "D": "د", "N/A": "لا ينطبق"}
LEVEL_NAMES = {"A": "Ad hoc", "B": "Foundational", "C": "Established", "D": "Leading"}
NA = "N/A"

DEFAULT_POINTS = {"A": 25.0, "B": 50.0, "C": 75.0, "D": 100.0}

# Suggested score-to-maturity mapping. min_score is the inclusive lower bound.
# max_score is the inclusive integer top of the written range (29, 49, 69, 84, 100).
# A score belongs to the highest band whose min_score is less than or equal to it,
# so 29.9 is Critical, 30 is Low, 84.9 is High and 85 is Leading.
DEFAULT_BANDS = [
	{
		"level_name": "Critical",
		"level_name_ar": "حرج",
		"interpretation_ar": "لدى وظيفة التدقيق الداخلي أوجه قصور جوهرية تؤثر مادياً في قدرتها على العمل بفاعلية. قد تكون الضوابط الرئيسية أو الاستقلالية أو المنهجية أو التغطية أو تأكيد الجودة غائبة أو غير فعّالة. ويلزم التصعيد الفوري إلى لجنة المراجعة أو مجلس الإدارة ووضع خارطة طريق رسمية للمعالجة.",
		"min_score": 0,
		"max_score": 29,
		"color": "#B42318",
		"interpretation": "The internal audit function has fundamental deficiencies that materially affect its ability "
		"to operate effectively. Key controls, independence, methodology, coverage or quality assurance may be "
		"absent or ineffective. Immediate escalation to the Audit Committee/Board and a formal remediation "
		"roadmap are required.",
	},
	{
		"level_name": "Low",
		"level_name_ar": "منخفض",
		"interpretation_ar": "لدى وظيفة التدقيق الداخلي فجوات نضج كبيرة. الممارسات في معظمها تفاعلية أو غير رسمية، وتوجد نقاط ضعف في الحوكمة أو التخطيط المبني على المخاطر أو المنهجية أو الموارد أو تأكيد الجودة أو المتابعة. وتحد هذه الفجوات من قدرة الوظيفة على تقديم تأكيد فعّال. ويلزم معالجة ذات أولوية واهتمام من الإدارة.",
		"min_score": 30,
		"max_score": 49,
		"color": "#BF530B",
		"interpretation": "The internal audit function has significant maturity gaps. Practices are largely reactive "
		"or informal, and there are weaknesses in governance, risk-based planning, methodology, resourcing, "
		"quality assurance or follow-up. These gaps limit the function’s ability to provide effective assurance. "
		"Priority remediation and management attention are required.",
	},
	{
		"level_name": "Medium",
		"level_name_ar": "متوسط",
		"interpretation_ar": "تتمتع وظيفة التدقيق الداخلي بمستوى نضج كافٍ لكنه غير متساوٍ. تُنفَّذ أنشطة التدقيق الأساسية، لكن الممارسات لا تُطبَّق باتساق في جميع المجالات. توجد فجوات في التغطية المبنية على المخاطر أو منهجية التدقيق أو تأكيد الجودة أو المتابعة أو استخدام التقنية. ويلزم وضع خطة تحسين منظمة لرفع مستوى النضج وضمان تقديم تأكيد متسق.",
		"min_score": 50,
		"max_score": 69,
		"color": "#9A6F00",
		"interpretation": "The internal audit function has an adequate but uneven maturity level. Core audit "
		"activities are performed, but practices are not consistently applied across all areas. Gaps exist in "
		"risk-based coverage, audit methodology, quality assurance, follow-up or use of technology. A structured "
		"improvement plan is required to raise maturity and ensure consistent delivery of assurance.",
	},
	{
		"level_name": "High",
		"level_name_ar": "مرتفع",
		"interpretation_ar": "تعمل وظيفة التدقيق الداخلي بمستوى نضج مرتفع وبممارسات متسقة في العموم. العناصر الأساسية لمنهجية التدقيق والتغطية المبنية على المخاطر وتأكيد الجودة قائمة. غير أن بعض المجالات تحتاج إلى تحسين موجّه للوصول إلى الممارسة الرائدة، ولا سيما تحليلات البيانات ومرونة الموارد وقياس الأداء أو المراقبة المستمرة.",
		"min_score": 70,
		"max_score": 84,
		"color": "#2D7A33",
		"interpretation": "The internal audit function operates at a high level of maturity with generally consistent "
		"practices. Key elements of the audit methodology, risk-based coverage and quality assurance are in "
		"place. However, some areas require targeted improvement to reach leading practice, particularly in "
		"areas such as data analytics, resource flexibility, performance measurement or continuous monitoring.",
	},
	{
		"level_name": "Leading",
		"level_name_ar": "رائد",
		"interpretation_ar": "تُظهر وظيفة التدقيق الداخلي مستوى ناضجاً واستباقياً. الحوكمة، والتخطيط المبني على المخاطر، والمنهجية، وإعداد التقارير، وتأكيد الجودة، والمتابعة مطبّقة عموماً بقوة واتساق. والوظيفة في وضع جيد لتقديم التأكيد والرؤى لمجلس الإدارة والإدارة. وتقتصر الإجراءات المتبقية في الغالب على تحسينات تدريجية، مثل مزيد من الأتمتة والتحليلات المتقدمة والمرونة والتحسين المستمر.",
		"min_score": 85,
		"max_score": 100,
		"color": "#1C5CA3",
		"interpretation": "The internal audit function demonstrates a mature and proactive level of maturity. "
		"Governance, risk-based planning, methodology, reporting, quality assurance and follow-up are generally "
		"strong and consistently applied. The function is well positioned to provide assurance and insight to "
		"the board and management. Remaining actions are mainly incremental enhancements, such as further "
		"automation, advanced analytics, agility and continuous improvement.",
	},
]

PRIORITY = {
	"A": ("Immediate", "0–3 months", 90),
	"B": ("High", "3–6 months", 180),
	"C": ("Medium", "6–12 months", 365),
}

# Multi-select scoring (docs do not define multi-select; Excel/HTML are single A–D only).
# Default Highest keeps ordinal maturity semantics if Multi is enabled on A–D levels.
MULTI_SCORE_HIGHEST = "Highest"
MULTI_SCORE_AVERAGE = "Average"
MULTI_SCORE_SUM = "Sum (capped)"
DEFAULT_MULTI_SCORE_METHOD = MULTI_SCORE_HIGHEST


def is_multi(answer):
	return (answer.get("selection_mode") or "Single").strip() == "Multi"


def parse_selected(raw):
	"""Normalize a stored answer into (kind, letters).

	kind: '' (unanswered), 'N/A', or 'letters'.
	letters: ordered unique A–D (empty when kind is not 'letters').
	"""
	text = (raw or "").strip().upper().replace(" ", "")
	if not text:
		return "", []
	if text in (NA, "NA", "N.A.", "N.A"):
		return NA, []
	parts = [p for p in text.replace(";", ",").split(",") if p]
	letters = []
	seen = set()
	for part in parts:
		if part not in LETTERS:
			return "invalid", []
		if part not in seen:
			seen.add(part)
			letters.append(part)
	letters.sort(key=LETTERS.index)
	return ("letters", letters) if letters else ("", [])


def normalize_selected(raw, multi=False):
	"""Canonical storage: '', 'N/A', 'A', or 'A,C' (sorted). Rejects invalid input."""
	kind, letters = parse_selected(raw)
	if kind == "invalid":
		return None
	if kind == NA:
		return NA
	if not letters:
		return ""
	if not multi and len(letters) > 1:
		return None
	return ",".join(letters) if multi else letters[0]


def multi_score_method(answer):
	method = (answer.get("multi_score_method") or DEFAULT_MULTI_SCORE_METHOD).strip()
	if method not in (MULTI_SCORE_HIGHEST, MULTI_SCORE_AVERAGE, MULTI_SCORE_SUM):
		return DEFAULT_MULTI_SCORE_METHOD
	return method


def answer_points(answer, points, max_points):
	"""Points earned for one answer row (0 for unanswered / N/A)."""
	kind, letters = parse_selected(answer.get("selected_option"))
	if kind != "letters" or not letters:
		return 0.0
	values = [flt(points.get(letter, 0.0)) for letter in letters]
	if not is_multi(answer) or len(values) == 1:
		return values[0]
	method = multi_score_method(answer)
	if method == MULTI_SCORE_AVERAGE:
		return round(sum(values) / len(values), 4)
	if method == MULTI_SCORE_SUM:
		return min(sum(values), flt(max_points))
	return max(values)


def worst_letter(answer):
	"""Lowest maturity letter among selections (for gating / findings / actions)."""
	kind, letters = parse_selected(answer.get("selected_option"))
	if kind != "letters" or not letters:
		return ""
	return min(letters, key=LETTERS.index)


def selected_statements(answer):
	"""Human-readable statement(s) for the chosen option(s)."""
	kind, letters = parse_selected(answer.get("selected_option"))
	if kind == NA:
		return "Not applicable"
	if kind != "letters":
		return ""
	fields = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}
	parts = []
	for letter in letters:
		text = (answer.get(fields[letter]) or "").strip()
		parts.append(f"{letter}: {text}" if text else letter)
	return " | ".join(parts)


def get_config(doc=None):
	"""Return scoring configuration from IA Maturity Settings (with safe defaults)."""
	if doc and doc.get("grc_policy_snapshot"):
		return frappe._dict(frappe.parse_json(doc.grc_policy_snapshot))
	if doc and doc.get("grc_assessment_type") == "GRC":
		from ia_maturity.grc.workbook import published_policy
		return frappe._dict(published_policy())
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
			"level_name_ar": b.get("level_name_ar") or "",
			"interpretation_ar": b.get("interpretation_ar") or "",
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
	          (optionally) selection_mode, multi_score_method, is_gating, gate_trigger,
	          gate_cap_level, short_label
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
			section_title_ar=s.get("section_title_ar") or "",
			reference_ar=s.get("reference_ar") or "",
			owner_role=s.get("owner_role") or "",
			owner_role_ar=s.get("owner_role_ar") or "",
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
		kind, letters = parse_selected(a.get("selected_option"))
		if sec is not None:
			sec.question_count += 1
		if not kind or kind == "invalid":
			# unanswered still counts in the denominator (same as the workbook) until submission
			if sec is not None:
				sec.applicable += 1
				sec.max_points += max_pt
			applicable += 1
			total_max += max_pt
			continue
		answered += 1
		if sec is not None:
			sec.answered += 1
		if kind == NA:
			na += 1
			continue
		p = answer_points(a, pts, max_pt)
		applicable += 1
		total_pts += p
		total_max += max_pt
		if sec is not None:
			sec.applicable += 1
			sec.points += p
			sec.max_points += max_pt
		worst = worst_letter(a)
		if worst in ("A", "B"):
			findings += 1
		if worst == "A":
			immediate += 1
		if (
			config.get("gating_enabled", True)
			and cint(a.get("is_gating"))
			and worst
			and worst in gate_letters(a.get("gate_trigger"))
			and a.get("gate_cap_level")
		):
			gate_hits.append(
				(a.get("question_code"), a.get("short_label") or "", worst, a.get("gate_cap_level"), a.get("short_label_ar") or "")
			)

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
	gating_note = gating_note_ar = ""
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
			gating_note_ar = (
				"تم تحديد المستوى العام عند «{0}» لأن السؤال الحاكم {1} ({2}) أُجيب عنه بالمستوى ({3}). "
				"ولولا ذلك لأشارت النتيجة إلى المستوى «{4}»."
			).format(
				final_band.get("level_name_ar") or final_band["level_name"],
				trigger[0],
				trigger[4] or trigger[1],
				LETTER_AR.get(trigger[2], trigger[2]),
				score_band.get("level_name_ar") or score_band["level_name"],
			)

	topics = []
	for key in dict.fromkeys((a.get("section_code"), a.get("topic_code")) for a in answers if a.get("topic_code")):
		rows = [a for a in answers if (a.get("section_code"), a.get("topic_code")) == key]
		counted = [a for a in rows if parse_selected(a.get("selected_option"))[0] != NA]
		possible = len(counted) * max_pt
		earned = sum(answer_points(a, pts, max_pt) for a in counted)
		percentage = round(earned / possible * 100, 1) if possible else 0.0
		topics.append({"section_code": key[0], "topic_code": key[1], "topic_title": rows[0].get("topic_title") or "",
			"topic_title_ar": rows[0].get("topic_title_ar") or "", "question_count": len(rows),
			"answered": sum(parse_selected(a.get("selected_option"))[0] in ("letters", NA) for a in rows),
			"applicable": len(counted), "points": earned, "max_points": possible, "score_pct": percentage,
			"maturity_level": band_for(percentage, bands)["level_name"] if possible else "N/A"})
	return frappe._dict(
		sections=sec_rows,
		topics=topics,
		overall_score=overall,
		overall_points=total_pts,
		max_points=total_max,
		score_level=score_band["level_name"],
		maturity_level=final_band["level_name"],
		interpretation=final_band["interpretation"],
		interpretation_ar=final_band.get("interpretation_ar") or "",
		gating_note_ar=gating_note_ar,
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
