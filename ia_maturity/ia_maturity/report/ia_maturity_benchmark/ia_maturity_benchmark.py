# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT
"""Peer distribution per section: the latest submitted assessment of each entity, aggregated."""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import flt

from ia_maturity.benchmark import _quartiles, latest_peer_assessments, section_scores_for


def execute(filters=None):
	filters = frappe._dict(filters or {})
	template = filters.get("template") or frappe.db.get_single_value("IA Maturity Settings", "default_template")
	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 320},
		{"label": _("Entities"), "fieldname": "entities", "fieldtype": "Int", "width": 90},
		{"label": _("Lower quartile %"), "fieldname": "p25", "fieldtype": "Percent", "precision": 1, "width": 130},
		{"label": _("Median %"), "fieldname": "median", "fieldtype": "Percent", "precision": 1, "width": 110},
		{"label": _("Upper quartile %"), "fieldname": "p75", "fieldtype": "Percent", "precision": 1, "width": 130},
		{"label": _("Average %"), "fieldname": "average", "fieldtype": "Percent", "precision": 1, "width": 110},
	]
	if not template:
		return columns, []
	peers = latest_peer_assessments(template, sector=filters.get("sector") or None)
	if not peers:
		return columns, [], _("No submitted assessments for this template yet.")

	tmpl = frappe.get_cached_doc("IA Maturity Template", template)
	scores = section_scores_for([p.name for p in peers])
	data = []
	for s in tmpl.sections:
		vals = scores.get(s.section_code, [])
		if not vals:
			continue
		q1, med, q3 = _quartiles(vals)
		data.append(
			{
				"section": f"{s.section_code} {s.section_title}",
				"entities": len(vals),
				"p25": q1,
				"median": med,
				"p75": q3,
				"average": round(sum(vals) / len(vals), 1),
			}
		)
	overall = [flt(p.overall_score) for p in peers]
	q1, med, q3 = _quartiles(overall)
	data.append(
		{
			"section": _("Overall"),
			"entities": len(overall),
			"p25": q1,
			"median": med,
			"p75": q3,
			"average": round(sum(overall) / len(overall), 1),
			"bold": 1,
		}
	)
	levels = Counter(
		frappe.db.get_value("IA Maturity Assessment", p.name, "maturity_level") or _("Not set") for p in peers
	)
	summary = [{"label": _("Entities compared"), "value": len(peers), "indicator": "blue"}] + [
		{"label": lvl, "value": n, "indicator": "gray"} for lvl, n in sorted(levels.items())
	]
	rows = [r for r in data if not r.get("bold")]
	chart = {
		"data": {
			"labels": [r["section"][:28] for r in rows],
			"datasets": [
				{"name": _("Lower quartile"), "values": [r["p25"] for r in rows]},
				{"name": _("Median"), "values": [r["median"] for r in rows]},
				{"name": _("Upper quartile"), "values": [r["p75"] for r in rows]},
			],
		},
		"type": "bar",
		"height": 280,
		"fieldtype": "Percent",
	}
	return columns, data, None, chart, summary
