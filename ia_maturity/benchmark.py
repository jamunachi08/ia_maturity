"""Anonymous peer benchmarking.

Peers are the latest submitted assessment of every *other* entity on the same questionnaire
template (optionally limited to the same sector). Results are only shown when at least
`benchmark_min_peers` peer entities exist, and only aggregate statistics (quartiles, median,
average, percentile rank) are ever returned — never minimum/maximum values or peer names — so no
individual entity can be identified.
"""

import statistics

import frappe
from frappe.utils import cint, flt, nowdate


def _quartiles(values):
	values = sorted(values)
	if len(values) < 2:
		v = values[0] if values else 0
		return v, v, v
	q = statistics.quantiles(values, n=4, method="inclusive")
	return round(q[0], 1), round(q[1], 1), round(q[2], 1)


def percentile_rank(value, values):
	"""Share of peers scoring below `value` (ties count half), 0–100."""
	if not values:
		return None
	below = sum(1 for v in values if v < value)
	equal = sum(1 for v in values if v == value)
	return round((below + 0.5 * equal) / len(values) * 100)


def latest_peer_assessments(template, exclude_entity=None, sector=None):
	filters = {"docstatus": 1, "template": template}
	if exclude_entity:
		filters["entity"] = ["!=", exclude_entity]
	rows = frappe.get_all(
		"IA Maturity Assessment",
		filters=filters,
		fields=["name", "entity", "overall_score", "assessment_date", "creation"],
		order_by="assessment_date desc, creation desc",
		limit_page_length=0,
	)
	if sector:
		in_sector = set(frappe.get_all("IA Maturity Entity", filters={"sector": sector}, pluck="name"))
		rows = [r for r in rows if r.entity in in_sector]
	latest = {}
	for r in rows:
		latest.setdefault(r.entity, r)
	return list(latest.values())


def section_scores_for(assessment_names):
	if not assessment_names:
		return {}
	out = {}
	for s in frappe.get_all(
		"IA Maturity Section Score",
		filters={"parenttype": "IA Maturity Assessment", "parent": ["in", assessment_names]},
		fields=["parent", "section_code", "score_pct", "max_points"],
		limit_page_length=0,
	):
		if flt(s.max_points):
			out.setdefault(s.section_code, []).append(flt(s.score_pct))
	return out


def peer_benchmark(doc):
	"""Benchmark for one assessment. Always returns a dict with `available` True/False."""
	settings = frappe.get_cached_doc("IA Maturity Settings")
	min_peers = cint(settings.benchmark_min_peers) or 5
	result = frappe._dict(enabled=bool(cint(settings.enable_benchmarking)), available=False, min_peers=min_peers)
	if not result.enabled or not doc.template:
		return result

	sector = None
	if settings.benchmark_peer_group == "Same sector":
		sector = frappe.db.get_value("IA Maturity Entity", doc.entity, "sector")
		result.peer_group = "Same sector"
		result.sector = sector or ""
		if not sector:
			result.reason = "no_sector"
			return result
	else:
		result.peer_group = "All entities"

	peers = latest_peer_assessments(doc.template, doc.entity, sector)
	result.peer_count = len(peers)
	if len(peers) < min_peers:
		result.reason = "too_few_peers"
		return result

	overall = [flt(p.overall_score) for p in peers]
	q1, med, q3 = _quartiles(overall)
	result.update(
		available=True,
		as_of=nowdate(),
		overall=frappe._dict(
			value=flt(doc.overall_score),
			p25=q1,
			median=med,
			p75=q3,
			average=round(sum(overall) / len(overall), 1),
			percentile=percentile_rank(flt(doc.overall_score), overall),
		),
	)
	peer_sections = section_scores_for([p.name for p in peers])
	sections = []
	for s in doc.section_scores:
		vals = peer_sections.get(s.section_code, [])
		if len(vals) < min_peers or not flt(s.max_points):
			continue
		sq1, smed, sq3 = _quartiles(vals)
		sections.append(
			frappe._dict(
				code=s.section_code,
				title=s.section_title,
				title_ar=s.get("section_title_ar") or "",
				value=flt(s.score_pct),
				p25=sq1,
				median=smed,
				p75=sq3,
				average=round(sum(vals) / len(vals), 1),
				delta=round(flt(s.score_pct) - smed, 1),
				percentile=percentile_rank(flt(s.score_pct), vals),
			)
		)
	result.sections = sections
	return result
