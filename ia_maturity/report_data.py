"""Builds the data behind the results report (print format, portal and desk)."""

import frappe
from frappe.utils import escape_html, flt, formatdate

from ia_maturity.scoring import LETTERS, LEVEL_NAMES, NA, PRIORITY, get_config

OPTION_FIELDS = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}


def _doc(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("IA Maturity Assessment", doc)
	return doc


def get_report_context(doc):
	"""Everything the report needs, as plain dicts (JSON-serialisable)."""
	doc = _doc(doc)
	config = get_config()
	bands = config.bands
	color_of = {b["level_name"]: b["color"] for b in bands}
	owners = {}
	if doc.template and frappe.db.exists("IA Maturity Template", doc.template):
		for s in frappe.get_cached_doc("IA Maturity Template", doc.template).sections:
			owners[s.section_code] = s.owner_role

	sections = [
		{
			"code": s.section_code,
			"title": s.section_title,
			"reference": s.reference or "",
			"points": flt(s.points),
			"max_points": flt(s.max_points),
			"pct": flt(s.score_pct),
			"level": s.maturity_level,
			"color": color_of.get(s.maturity_level, "#586976"),
			"answered": s.answered,
		}
		for s in doc.section_scores
	]
	scored = [s for s in sections if s["max_points"]]
	ranked = sorted(scored, key=lambda s: s["pct"], reverse=True)

	findings, actions, answers = [], [], []
	action_letters = {"A", "B", "C"} if config.create_actions_for == "A, B and C" else {"A", "B"}
	for a in doc.answers:
		opt = a.selected_option or ""
		row = {
			"code": a.question_code,
			"section": a.section_code,
			"section_title": a.section_title,
			"label": a.short_label or a.question_code,
			"question": a.question_text,
			"answer": opt,
			"answer_level": LEVEL_NAMES.get(opt, "Not applicable" if opt == NA else ""),
			"statement": a.selected_description or "",
			"points": flt(a.points),
			"comment": a.comment or "",
			"evidence": a.evidence or "",
		}
		answers.append(row)
		if opt in LETTERS and opt != "D":
			nxt_letter = LETTERS[LETTERS.index(opt) + 1]
			pr = PRIORITY[opt]
			item = dict(
				row,
				priority=pr[0],
				timeframe=pr[1],
				target=nxt_letter,
				target_level=LEVEL_NAMES[nxt_letter],
				next_statement=a.get(OPTION_FIELDS[nxt_letter]) or "",
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
		for t in tracked:
			t["due_date"] = str(t["due_date"]) if t.get("due_date") else ""

	scale = []
	for i, b in enumerate(bands):
		upper = bands[i + 1]["min_score"] if i + 1 < len(bands) else 100
		scale.append(
			{
				"level": b["level_name"],
				"from": b["min_score"],
				"to": upper,
				"width": max(0, upper - b["min_score"]),
				"color": b["color"],
				"interpretation": b["interpretation"],
			}
		)

	return {
		"name": doc.name,
		"entity": doc.entity,
		"date": formatdate(doc.assessment_date) if doc.assessment_date else "",
		"respondent": doc.respondent_name or doc.respondent or "",
		"job_title": doc.job_title or "",
		"respondent_role": doc.respondent_role or "",
		"template": doc.template,
		"overall": flt(doc.overall_score),
		"level": doc.maturity_level,
		"score_level": doc.score_level,
		"level_color": color_of.get(doc.maturity_level, "#586976"),
		"points": flt(doc.overall_points),
		"max_points": flt(doc.max_points),
		"interpretation": doc.interpretation or "",
		"gating_note": doc.gating_note or "",
		"question_count": doc.question_count,
		"section_count": len(sections),
		"na_count": doc.na_count,
		"findings_count": doc.findings_count,
		"immediate_count": doc.immediate_count,
		"strongest": ranked[0] if ranked else None,
		"weakest": ranked[-1] if ranked else None,
		"sections": sections,
		"findings": findings,
		"actions": actions,
		"tracked_actions": tracked,
		"answers": answers,
		"scale": scale,
		"points_map": config.points,
		"docstatus": doc.docstatus,
		"review_status": doc.review_status or "",
		"reviewer_comments": doc.reviewer_comments or "",
	}


def section_bar_svg(doc, width=640):
	"""Server-side SVG bar chart (renders in wkhtmltopdf, unlike JS charts)."""
	ctx = doc if isinstance(doc, dict) else get_report_context(doc)
	secs = ctx["sections"]
	if not secs:
		return ""
	row_h, top, left, right = 34, 8, 250, 50
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
			f'<text x="{left - 10}" y="{y + row_h / 2 + 4}" font-size="11.5" fill="#13232F" '
			f'text-anchor="end">{escape_html(name)}</text>'
			f'<rect x="{left}" y="{y + 8}" width="{bar_w:.1f}" height="{row_h - 16}" rx="2" fill="{s["color"]}"/>'
			f'<text x="{left + bar_w + 6:.1f}" y="{y + row_h / 2 + 4}" font-size="11" fill="#13232F">'
			f'{s["pct"]:g}%</text>'
		)
	parts.append("</svg>")
	return "".join(parts)
