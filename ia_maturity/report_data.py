"""Builds the data behind the results report (print format, portal and desk), in English or Arabic."""

import base64
import os
from functools import lru_cache

import frappe
from frappe.utils import cint, escape_html, flt, formatdate

from ia_maturity import i18n
from ia_maturity.branding import get_brand
from ia_maturity.scoring import LETTERS, NA, PRIORITY, get_config

OPTION_FIELDS = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}


def _doc(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("IA Maturity Assessment", doc)
	return doc


def report_language(doc, lang=None):
	"""Explicit lang > `language` request parameter (PDF download) > the assessment's Report Language."""
	if lang:
		return i18n.norm_lang(lang)
	requested = (getattr(frappe.local, "form_dict", None) or {}).get("language")
	if requested and str(requested)[:2].lower() in i18n.LANGS:
		return i18n.norm_lang(requested)
	return i18n.norm_lang(doc.get("language"))


def _pick(row, field, lang):
	"""Arabic value when available, otherwise the English one."""
	if lang == "ar":
		return row.get(f"{field}_ar") or row.get(field) or ""
	return row.get(field) or ""


# report section -> IA Maturity Settings checkbox that controls it in the client report
CLIENT_SECTION_FIELDS = {
	"summary": "client_show_summary",
	"sections": "client_show_sections",
	"benchmark": "show_benchmark_to_respondents",
	"findings": "client_show_findings",
	"roadmap": "client_show_roadmap",
	"responses": "client_show_responses",
	"reviewer_comments": "client_show_reviewer_comments",
	"scoring_method": "client_show_scoring_method",
}
AUDIENCES = ("client", "internal")


def visible_sections(audience="client"):
	"""Which report sections an audience gets. The internal report always has everything."""
	if audience == "internal":
		return {key: True for key in CLIENT_SECTION_FIELDS}
	settings = frappe.get_cached_doc("IA Maturity Settings")
	return {key: bool(cint(settings.get(field))) for key, field in CLIENT_SECTION_FIELDS.items()}


def ia_report_guard(audience="client"):
	"""Called at the top of the print formats: only IA Maturity staff may render the internal report."""
	from ia_maturity.permissions import is_staff

	if audience == "internal" and not is_staff():
		frappe.throw(
			frappe._("The internal report is only available to IA Maturity staff."), frappe.PermissionError
		)
	return ""


def get_report_context(doc, lang=None, include_benchmark=True, audience="client"):
	"""Everything the report needs, as plain dicts (JSON-serialisable), in the report language.

	audience="client" includes only the sections enabled in IA Maturity Settings > Client Report Content
	and leaves the data of the other sections out altogether (so it never reaches the client's browser);
	audience="internal" includes everything.
	"""
	doc = _doc(doc)
	audience = audience if audience in AUDIENCES else "client"
	show = visible_sections(audience)
	lang = report_language(doc, lang)
	t = i18n.strings(lang)
	level_names = i18n.LEVEL_NAMES[lang]
	letters = i18n.LETTERS[lang]
	config = get_config()
	bands = config.bands
	color_of = {b["level_name"]: b["color"] for b in bands}
	band_label = {b["level_name"]: (b.get("level_name_ar") if lang == "ar" else None) or b["level_name"] for b in bands}

	def level_label(name):
		return band_label.get(name, name or "")

	sections = [
		{
			"code": s.section_code,
			"title": _pick(s, "section_title", lang),
			"reference": _pick(s, "reference", lang),
			"points": flt(s.points),
			"max_points": flt(s.max_points),
			"pct": flt(s.score_pct),
			"level": s.maturity_level,
			"level_label": level_label(s.maturity_level),
			"color": color_of.get(s.maturity_level, "#586976"),
			"answered": s.answered,
		}
		for s in doc.section_scores
	]
	owners = {s.section_code: _pick(s, "owner_role", lang) for s in doc.section_scores}
	if doc.template and not any(owners.values()) and frappe.db.exists("IA Maturity Template", doc.template):
		owners = {
			s.section_code: _pick(s, "owner_role", lang)
			for s in frappe.get_cached_doc("IA Maturity Template", doc.template).sections
		}
	scored = [s for s in sections if s["max_points"]]
	ranked = sorted(scored, key=lambda s: s["pct"], reverse=True)

	findings, actions, answers = [], [], []
	action_letters = {"A", "B", "C"} if config.create_actions_for == "A, B and C" else {"A", "B"}
	for a in doc.answers:
		opt = a.selected_option or ""
		statement = _pick(a, OPTION_FIELDS[opt], lang) if opt in LETTERS else (level_names["N/A"] if opt == NA else "")
		row = {
			"code": a.question_code,
			"section": a.section_code,
			"section_title": _pick(a, "section_title", lang),
			"label": _pick(a, "short_label", lang) or a.question_code,
			"question": _pick(a, "question_text", lang),
			"answer": opt,
			"answer_letter": letters.get(opt, opt),
			"answer_level": level_names.get(opt, ""),
			"statement": statement,
			"points": flt(a.points),
			"comment": i18n.bidi(a.comment or "", lang),
			"evidence": a.evidence or "",
			"auto_calculated": bool(a.get("auto_calculated")),
			"auto_note": _pick(a, "auto_note", lang) if a.get("auto_calculated") else "",
		}
		answers.append(row)
		if opt in LETTERS and opt != "D":
			nxt_letter = LETTERS[LETTERS.index(opt) + 1]
			priority_key = PRIORITY[opt][0]
			pr_label, pr_time = i18n.PRIORITY[lang][priority_key]
			item = dict(
				row,
				priority=priority_key,
				priority_label=pr_label,
				timeframe=pr_time,
				target=nxt_letter,
				target_letter=letters[nxt_letter],
				target_level=level_names[nxt_letter],
				next_statement=_pick(a, OPTION_FIELDS[nxt_letter], lang),
				owner=owners.get(a.section_code, ""),
			)
			if opt in ("A", "B"):
				findings.append(item)
			if opt in action_letters:
				actions.append(item)

	def qnum(r):
		digits = "".join(c for c in r["code"] if c.isdigit())
		return int(digits) if digits else 0

	findings.sort(key=lambda r: (r["answer"], qnum(r)))
	actions.sort(key=lambda r: (r["answer"], qnum(r)))

	tracked = []
	if doc.docstatus == 1:
		tracked = frappe.get_all(
			"IA Maturity Action",
			filters={"assessment": doc.name},
			fields=["name", "question_code", "status", "due_date", "assigned_to", "priority"],
			order_by="question_code asc",
		)
		for tr in tracked:
			tr["due_date"] = str(tr["due_date"]) if tr.get("due_date") else ""

	scale = []
	for i, b in enumerate(bands):
		upper = bands[i + 1]["min_score"] if i + 1 < len(bands) else 100
		scale.append(
			{
				"level": b["level_name"],
				"label": level_label(b["level_name"]),
				"from": b["min_score"],
				"to": upper,
				"width": max(0, upper - b["min_score"]),
				"color": b["color"],
			}
		)
	pts = config.points
	scoring_text = t["scoring_text"].format(
		a=f"{pts['A']:g}",
		b=f"{pts['B']:g}",
		c=f"{pts['C']:g}",
		d=f"{pts['D']:g}",
		bands=("، " if lang == "ar" else ", ").join(f"{b['label']} {b['from']:g}–{b['to']:g}%" for b in scale),
	)

	interpretation = (doc.get("interpretation_ar") if lang == "ar" else None) or doc.interpretation or ""
	gating_note = (doc.get("gating_note_ar") if lang == "ar" else None) or doc.gating_note or ""
	summary_bits = []
	if ranked:
		summary_bits.append(
			{"label": t["strongest"], "title": ranked[0]["title"], "pct": ranked[0]["pct"]},
		)
		summary_bits.append({"label": t["weakest"], "title": ranked[-1]["title"], "pct": ranked[-1]["pct"]})

	ctx = {
		"lang": lang,
		"dir": "rtl" if lang == "ar" else "ltr",
		"t": t,
		"name": doc.name,
		"entity": i18n.bidi(doc.entity, lang),
		"date": formatdate(doc.assessment_date) if doc.assessment_date else "",
		"respondent": i18n.bidi(doc.respondent_name or doc.respondent or "", lang),
		"job_title": i18n.bidi(doc.job_title or "", lang),
		"respondent_role": (
			i18n.RESPONDENT_ROLES_AR.get(doc.respondent_role, doc.respondent_role) if lang == "ar" else doc.respondent_role
		)
		or "",
		"template": doc.template,
		"overall": flt(doc.overall_score),
		"level": doc.maturity_level,
		"level_label": level_label(doc.maturity_level),
		"score_level": doc.score_level,
		"level_color": color_of.get(doc.maturity_level, "#586976"),
		"points": flt(doc.overall_points),
		"max_points": flt(doc.max_points),
		"points_text": t["points_of"].format(f"{flt(doc.overall_points):g}", f"{flt(doc.max_points):g}"),
		"interpretation": interpretation,
		"gating_note": gating_note,
		"question_count": doc.question_count,
		"section_count": len(sections),
		"questions_text": t["questions_value"].format(doc.question_count, len(sections)),
		"na_count": doc.na_count,
		"findings_count": doc.findings_count,
		"immediate_count": doc.immediate_count,
		"findings_text": t["findings_raised"].format(doc.findings_count or 0, doc.immediate_count or 0),
		"na_text": t["na_marked"].format(doc.na_count) if doc.na_count else "",
		"strongest": ranked[0] if ranked else None,
		"weakest": ranked[-1] if ranked else None,
		"sections": sections,
		"findings": findings,
		"actions": actions,
		"tracked_actions": tracked,
		"answers": answers,
		"scale": scale,
		"scoring_text": scoring_text,
		"points_map": config.points,
		"docstatus": doc.docstatus,
		"review_status": doc.review_status or "",
		"review_status_label": (
			i18n.REVIEW_STATUS_AR.get(doc.review_status, doc.review_status) if lang == "ar" else doc.review_status
		)
		or "",
		"reviewer_comments": i18n.bidi(doc.reviewer_comments or "", lang),
		"benchmark": None,
	}
	ctx["audience"] = audience
	ctx["show"] = show
	ctx["internal_banner"] = t["internal_banner"].format(get_brand().company) if audience == "internal" else ""
	if include_benchmark and show["benchmark"]:
		ctx["benchmark"] = benchmark_context(doc, lang, t, level_label)
	if audience == "client":
		# drop the data of hidden sections, not just their headings
		if not show["findings"]:
			ctx["findings"] = []
		if not show["roadmap"]:
			ctx["actions"] = []
		if not show["responses"]:
			ctx["answers"] = []
		if not show["reviewer_comments"]:
			ctx["reviewer_comments"] = ""
		if not show["scoring_method"]:
			ctx["scoring_text"] = ""
		ctx["tracked_actions"] = []
	return ctx


def benchmark_context(doc, lang, t, level_label=None):
	from ia_maturity.benchmark import peer_benchmark

	settings = frappe.get_cached_doc("IA Maturity Settings")
	if doc.docstatus != 1 or not settings.enable_benchmarking:
		return None
	bm = peer_benchmark(doc)
	if not bm.enabled:
		return None
	if not bm.available:
		msg = t["benchmark_no_sector"] if bm.get("reason") == "no_sector" else t["benchmark_unavailable"].format(bm.min_peers)
		return {"available": False, "message": msg}
	group = t["peer_sector"].format(bm.sector) if bm.peer_group == "Same sector" else t["peer_all"]
	sections = [
		{
			"code": s.code,
			"title": (s.title_ar if lang == "ar" and s.title_ar else s.title),
			"value": s.value,
			"p25": s.p25,
			"median": s.median,
			"p75": s.p75,
			"delta": s.delta,
			"percentile": s.percentile,
		}
		for s in bm.sections
	]
	return {
		"available": True,
		"note": t["benchmark_note"].format(bm.peer_count, group, formatdate(bm.as_of)),
		"overall": dict(bm.overall),
		"percentile_text": t["percentile_text"].format(bm.overall.percentile),
		"sections": sections,
	}


FONT_DIR = os.path.join(os.path.dirname(__file__), "public", "fonts")


def arabic_font_css():
	"""@font-face rules with the bundled Noto Sans Arabic embedded (works without network or system fonts).

	A plain function (not functools-wrapped): Frappe only registers plain functions as Jinja helpers.
	"""
	return _arabic_font_css()


@lru_cache(maxsize=1)
def _arabic_font_css():
	rules = []
	for weight, fname in ((400, "NotoSansArabic-Regular.ttf"), (700, "NotoSansArabic-Bold.ttf")):
		with open(os.path.join(FONT_DIR, fname), "rb") as fh:
			data = base64.b64encode(fh.read()).decode()
		rules.append(
			"@font-face{font-family:'IAM Arabic';font-style:normal;font-weight:%d;"
			"src:url(data:font/truetype;charset=utf-8;base64,%s) format('truetype');}" % (weight, data)
		)
	return "\n".join(rules)


def section_bar_svg(doc, width=640):
	"""Server-side SVG bar chart (renders in wkhtmltopdf, unlike JS charts)."""
	ctx = doc if isinstance(doc, dict) else get_report_context(doc)
	secs = ctx["sections"]
	if not secs:
		return ""
	row_h, top, left, right = 26, 6, 250, 50
	plot = width - left - right
	height = top + len(secs) * row_h + 26

	def x(v):
		return left + flt(v) / 100 * plot

	parts = [
		f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
		f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">'
	]
	for band in ctx["scale"]:
		parts.append(
			f'<rect x="{x(band["from"]):.1f}" y="{top}" width="{x(band["to"]) - x(band["from"]):.1f}" '
			f'height="{len(secs) * row_h}" fill="{band["color"]}" fill-opacity="0.08"/>'
		)
	ticks = sorted({0, 100} | {b["from"] for b in ctx["scale"]})
	for t in ticks:
		parts.append(
			f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{top + len(secs) * row_h}" '
			f'stroke="#D7E0E5" stroke-width="1"/>'
			f'<text x="{x(t):.1f}" y="{height - 8}" font-size="10" fill="#586976" text-anchor="middle">'
			f"{t:g}%</text>"
		)
	for i, s in enumerate(secs):
		y = top + i * row_h
		name = s["title"] if len(s["title"]) <= 38 else s["title"][:36] + "…"
		bar_w = max(2, x(s["pct"]) - left)
		parts.append(
			f'<text x="{left - 10}" y="{y + row_h / 2 + 4}" font-size="11.5" fill="#181818" '
			f'text-anchor="end">{escape_html(name)}</text>'
			f'<rect x="{left}" y="{y + 5}" width="{bar_w:.1f}" height="{row_h - 10}" rx="2" fill="{s["color"]}"/>'
			f'<text x="{left + bar_w + 6:.1f}" y="{y + row_h / 2 + 4}" font-size="11" fill="#181818">'
			f'{s["pct"]:g}%</text>'
		)
	parts.append("</svg>")
	return "".join(parts)
