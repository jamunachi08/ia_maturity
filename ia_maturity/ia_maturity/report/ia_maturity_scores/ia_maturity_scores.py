# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT
"""Scores per assessment, or averaged by entity / respondent perspective (perception gap)."""

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

from ia_maturity.scoring import band_for, get_config


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = {"docstatus": 1}
	if filters.get("entity"):
		conditions["entity"] = filters.entity
	if filters.get("template"):
		conditions["template"] = filters.template
	if filters.get("respondent_role"):
		conditions["respondent_role"] = filters.respondent_role
	if filters.get("from_date") and filters.get("to_date"):
		conditions["assessment_date"] = ["between", [filters.from_date, filters.to_date]]
	if filters.get("include_drafts"):
		conditions["docstatus"] = ["<", 2]

	docs = frappe.get_list(
		"IA Maturity Assessment",
		filters=conditions,
		fields=["name", "entity", "assessment_date", "respondent_name", "respondent_role", "overall_score",
			"maturity_level", "review_status", "findings_count", "docstatus"],
		order_by="assessment_date desc",
		limit_page_length=0,
	)
	if not docs:
		return _columns(filters, []), [], None, None

	scores = frappe.get_all(
		"IA Maturity Section Score",
		filters={"parent": ["in", [d.name for d in docs]], "parenttype": "IA Maturity Assessment"},
		fields=["parent", "section_code", "section_title", "score_pct"],
		order_by="idx asc",
	)
	sections = OrderedDict()
	by_doc = {}
	for s in scores:
		sections.setdefault(s.section_code, s.section_title)
		by_doc.setdefault(s.parent, {})[s.section_code] = flt(s.score_pct)

	bands = get_config().bands
	group_by = filters.get("group_by")
	if group_by in ("Entity", "Respondent Perspective"):
		key = "entity" if group_by == "Entity" else "respondent_role"
		groups = OrderedDict()
		for d in docs:
			groups.setdefault(d.get(key) or _("Not specified"), []).append(d)
		data = []
		for g, items in groups.items():
			row = {"group": g, "count": len(items)}
			row["overall_score"] = round(sum(flt(i.overall_score) for i in items) / len(items), 1)
			row["maturity_level"] = band_for(row["overall_score"], bands)["level_name"]
			for code in sections:
				vals = [by_doc.get(i.name, {}).get(code) for i in items]
				vals = [v for v in vals if v is not None]
				row[code.lower()] = round(sum(vals) / len(vals), 1) if vals else None
			data.append(row)
	else:
		data = []
		for d in docs:
			row = dict(d)
			for code in sections:
				row[code.lower()] = by_doc.get(d.name, {}).get(code)
			data.append(row)

	columns = _columns(filters, sections)
	chart = _chart(data, sections, group_by)
	summary = [
		{"label": _("Assessments"), "value": len(docs), "indicator": "blue"},
		{"label": _("Average score"), "value": f"{round(sum(flt(d.overall_score) for d in docs) / len(docs), 1)}%",
		 "indicator": "green"},
		{"label": _("Findings raised"), "value": sum(d.findings_count or 0 for d in docs), "indicator": "orange"},
	]
	return columns, data, None, chart, summary


def _columns(filters, sections):
	group_by = filters.get("group_by")
	if group_by in ("Entity", "Respondent Perspective"):
		cols = [
			{"label": _(group_by), "fieldname": "group", "fieldtype": "Data", "width": 220},
			{"label": _("Assessments"), "fieldname": "count", "fieldtype": "Int", "width": 100},
		]
	else:
		cols = [
			{"label": _("Assessment"), "fieldname": "name", "fieldtype": "Link", "options": "IA Maturity Assessment", "width": 150},
			{"label": _("Entity"), "fieldname": "entity", "fieldtype": "Link", "options": "IA Maturity Entity", "width": 180},
			{"label": _("Date"), "fieldname": "assessment_date", "fieldtype": "Date", "width": 100},
			{"label": _("Respondent"), "fieldname": "respondent_name", "fieldtype": "Data", "width": 140},
			{"label": _("Perspective"), "fieldname": "respondent_role", "fieldtype": "Data", "width": 150},
		]
	cols += [
		{"label": _("Overall %"), "fieldname": "overall_score", "fieldtype": "Percent", "precision": 1, "width": 100},
		{"label": _("Maturity"), "fieldname": "maturity_level", "fieldtype": "Data", "width": 100},
	]
	for code, title in sections.items():
		cols.append({"label": f"{code} {title}", "fieldname": code.lower(), "fieldtype": "Percent", "precision": 1, "width": 130})
	if group_by not in ("Entity", "Respondent Perspective"):
		cols.append({"label": _("Review"), "fieldname": "review_status", "fieldtype": "Data", "width": 120})
	return cols


def _chart(data, sections, group_by):
	if not data or not sections:
		return None
	labels = list(sections.keys())
	if group_by in ("Entity", "Respondent Perspective"):
		datasets = [{"name": str(r["group"]), "values": [r.get(c.lower()) or 0 for c in labels]} for r in data[:6]]
	else:
		datasets = [{
			"name": _("Average"),
			"values": [round(sum((r.get(c.lower()) or 0) for r in data) / len(data), 1) for c in labels],
		}]
	return {
		"data": {"labels": [f"{c} {sections[c][:22]}" for c in labels], "datasets": datasets},
		"type": "bar",
		"barOptions": {"stacked": 0},
		"axisOptions": {"xIsSeries": 0},
		"fieldtype": "Percent",
		"height": 280,
	}
