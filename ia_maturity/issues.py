"""Auto-calculated answers from an audit-issue register (Q13 "average time to close audit issues").

The register is configurable in IA Maturity Settings: by default the app's own *IA Audit Issue*
DocType, but any DocType with an entity field, a raised-on date and a closed-on date can be used
(for example a custom issue tracker already kept in ERPNext).
"""

import statistics

import frappe
from frappe.utils import add_months, cint, date_diff, flt, formatdate, getdate, today

ISSUE_CLOSURE = "Issue Closure Time"
DAYS_PER_MONTH = 30.4375


def _settings():
	return frappe.get_cached_doc("IA Maturity Settings")


def register_config(settings=None):
	s = settings or _settings()
	return frappe._dict(
		doctype=s.issue_doctype or "IA Audit Issue",
		entity_field=s.issue_entity_field or "entity",
		opened_field=s.issue_opened_field or "raised_on",
		closed_field=s.issue_closed_field or "closed_on",
		lookback=cint(s.issue_lookback_months) or 24,
		min_sample=cint(s.issue_min_sample) if s.issue_min_sample is not None else 5,
		a_above=flt(s.closure_a_above) if s.closure_a_above is not None else 12,
		b_above=flt(s.closure_b_above) if s.closure_b_above is not None else 9,
		c_above=flt(s.closure_c_above) if s.closure_c_above is not None else 6,
		lock=cint(s.lock_auto_answers),
	)


def closure_stats(entity, as_of=None, settings=None):
	"""Closure statistics for one entity, or None when the register is unusable."""
	cfg = register_config(settings)
	if not entity or not frappe.db.exists("DocType", cfg.doctype):
		return None
	meta = frappe.get_meta(cfg.doctype)
	for f in (cfg.entity_field, cfg.opened_field, cfg.closed_field):
		if not meta.has_field(f):
			frappe.log_error(
				title="IA Maturity: issue register misconfigured",
				message=f"Field {f} not found on {cfg.doctype}. Check IA Maturity Settings > Issue Register.",
			)
			return None

	as_of = getdate(as_of or today())
	since = getdate(add_months(as_of, -cfg.lookback))
	closed = frappe.get_all(
		cfg.doctype,
		filters={
			cfg.entity_field: entity,
			cfg.closed_field: ["between", [since, as_of]],
			cfg.opened_field: ["is", "set"],
		},
		fields=[f"{cfg.opened_field} as opened", f"{cfg.closed_field} as closed"],
		limit_page_length=0,
	)
	months = [max(0, date_diff(r.closed, r.opened)) / DAYS_PER_MONTH for r in closed]
	open_over_12 = frappe.db.count(
		cfg.doctype,
		{
			cfg.entity_field: entity,
			cfg.closed_field: ["is", "not set"],
			cfg.opened_field: ["<=", add_months(as_of, -12)],
		},
	)
	return frappe._dict(
		count=len(months),
		avg_months=round(sum(months) / len(months), 1) if months else None,
		median_months=round(statistics.median(months), 1) if months else None,
		open_over_12=open_over_12,
		since=since,
		as_of=as_of,
		min_sample=cfg.min_sample,
	)


def letter_for(avg_months, settings=None):
	cfg = register_config(settings)
	if avg_months > cfg.a_above:
		return "A"
	if avg_months > cfg.b_above:
		return "B"
	if avg_months > cfg.c_above:
		return "C"
	return "D"


def describe(stats, letter=None):
	"""English and Arabic explanation of how the answer was (or was not) derived."""
	if stats is None:
		return (
			"The issue register is not available, so this question is answered manually.",
			"سجل الملاحظات غير متاح، لذا يُجاب عن هذا السؤال يدوياً.",
		)
	since, as_of = formatdate(stats.since), formatdate(stats.as_of)
	if stats.count < stats.min_sample:
		return (
			f"Only {stats.count} issue(s) closed between {since} and {as_of} in the issue register "
			f"(at least {stats.min_sample} are needed), so this question is answered manually.",
			f"أُغلقت {stats.count} ملاحظة فقط بين {since} و{as_of} في سجل الملاحظات "
			f"(يلزم {stats.min_sample} على الأقل)، لذا يُجاب عن هذا السؤال يدوياً.",
		)
	open_en = (
		f" {stats.open_over_12} issue(s) have been open for more than 12 months." if stats.open_over_12 else ""
	)
	open_ar = f" وتوجد {stats.open_over_12} ملاحظة مفتوحة منذ أكثر من 12 شهراً." if stats.open_over_12 else ""
	return (
		f"Calculated from the issue register: {stats.count} issues closed between {since} and {as_of}, "
		f"average {stats.avg_months} months to close (median {stats.median_months}).{open_en}",
		f"محسوبة من سجل الملاحظات: أُغلقت {stats.count} ملاحظة بين {since} و{as_of}، "
		f"بمتوسط {stats.avg_months} شهراً للإغلاق (الوسيط {stats.median_months}).{open_ar}",
	)


def apply_auto_answers(doc):
	"""Fill auto-calculated answers on a draft assessment."""
	rows = [a for a in doc.answers if a.auto_source == ISSUE_CLOSURE]
	if not rows or doc.docstatus != 0:
		return
	settings = _settings()
	cfg = register_config(settings)
	stats = closure_stats(doc.entity, doc.assessment_date, settings)
	usable = stats is not None and stats.count >= stats.min_sample
	letter = letter_for(stats.avg_months, settings) if usable else None
	note_en, note_ar = describe(stats, letter)
	for row in rows:
		row.auto_note, row.auto_note_ar = note_en, note_ar
		if usable:
			if cfg.lock or not row.selected_option or row.auto_calculated:
				row.selected_option = letter
				row.auto_calculated = 1
		else:
			if row.auto_calculated:
				# previously calculated, register no longer qualifies: hand the question back
				row.selected_option = None
			row.auto_calculated = 0


def is_locked(row):
	return bool(row.auto_calculated and register_config().lock)
