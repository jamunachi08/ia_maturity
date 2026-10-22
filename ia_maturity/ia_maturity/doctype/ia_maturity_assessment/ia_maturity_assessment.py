# Copyright (c) 2026, IA Maturity Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime, today

from ia_maturity.scoring import LETTERS, LEVEL_NAMES, NA, PRIORITY, compute, get_config

OPTION_FIELDS = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}
SNAPSHOT_FIELDS = (
	"question_code",
	"section_code",
	"short_label",
	"question_text",
	"guidance",
	"option_a",
	"option_b",
	"option_c",
	"option_d",
	"allow_na",
	"is_gating",
	"gate_trigger",
	"gate_cap_level",
)


class IAMaturityAssessment(Document):
	# ------------------------------------------------------------------ lifecycle
	def before_insert(self):
		if not self.respondent:
			self.respondent = frappe.session.user
		if not self.template:
			self.template = frappe.db.get_single_value("IA Maturity Settings", "default_template")

	def validate(self):
		self.set_respondent_details()
		if not self.fiscal_year and self.assessment_date:
			self.fiscal_year = str(getdate(self.assessment_date).year)
		if not self.answers and self.template:
			self.load_questions()
		self.validate_answers()
		self.calculate()

	def before_submit(self):
		missing = [a.question_code for a in self.answers if not a.selected_option]
		if missing:
			frappe.throw(
				_("Answer every question before submitting. Unanswered: {0}").format(", ".join(missing)),
				title=_("Incomplete Assessment"),
			)
		self.validate_evidence()
		self.review_status = "Pending Review"

	def on_submit(self):
		self.create_actions()
		frappe.enqueue(
			"ia_maturity.notifications.send_submission_email",
			assessment=self.name,
			enqueue_after_commit=True,
			now=bool(frappe.flags.in_test),
		)

	def on_cancel(self):
		for name in frappe.get_all(
			"IA Maturity Action",
			filters={"assessment": self.name, "status": ["in", ["Open", "In Progress"]]},
			pluck="name",
		):
			frappe.db.set_value("IA Maturity Action", name, "status", "Cancelled")

	def after_insert(self):
		# An amendment created by staff (e.g. "Return to Respondent") belongs to the original respondent,
		# so they can correct it from the portal.
		if self.amended_from and self.respondent and self.owner != self.respondent:
			frappe.db.set_value(self.doctype, self.name, "owner", self.respondent, update_modified=False)
			self.owner = self.respondent

	def before_update_after_submit(self):
		before = self.get_doc_before_save()
		if before and before.review_status != self.review_status:
			self.reviewer = frappe.session.user
			self.reviewed_on = now_datetime()

	# ------------------------------------------------------------------ helpers
	def set_respondent_details(self):
		if self.respondent and (not self.respondent_name or not self.respondent_email):
			full_name, email = frappe.db.get_value("User", self.respondent, ["full_name", "email"]) or ("", "")
			self.respondent_name = self.respondent_name or full_name
			self.respondent_email = self.respondent_email or email

	@frappe.whitelist()
	def load_questions(self):
		"""(Re)build the answer rows from the template, keeping any answers already given."""
		if not self.template:
			frappe.throw(_("Select a questionnaire template first."))
		template = frappe.get_doc("IA Maturity Template", self.template)
		titles = {s.section_code: s.section_title for s in template.sections}
		previous = {a.question_code: a for a in self.answers}
		self.set("answers", [])
		for q in template.questions:
			row = {f: q.get(f) for f in SNAPSHOT_FIELDS}
			row["section_title"] = titles.get(q.section_code, q.section_code)
			old = previous.get(q.question_code)
			if old:
				row.update(selected_option=old.selected_option, comment=old.comment, evidence=old.evidence)
			self.append("answers", row)
		return self.answers

	def template_sections(self):
		template = frappe.get_cached_doc("IA Maturity Template", self.template)
		return template, [s.as_dict() for s in template.sections]

	def validate_answers(self):
		for a in self.answers:
			opt = (a.selected_option or "").strip()
			if opt == NA and not a.allow_na:
				frappe.throw(
					_("Row {0}: 'Not applicable' is not allowed for question {1}.").format(a.idx, a.question_code)
				)
			if opt and opt not in LETTERS and opt != NA:
				frappe.throw(_("Row {0}: invalid answer {1}.").format(a.idx, opt))

	def validate_evidence(self):
		rule = frappe.db.get_single_value("IA Maturity Settings", "evidence_required_from") or ""
		if not rule:
			return
		needs = {"C", "D"} if rule.startswith("C") else {"D"}
		missing = [
			a.question_code
			for a in self.answers
			if a.selected_option in needs and not (a.evidence or (a.comment or "").strip())
		]
		if missing:
			frappe.throw(
				_("Evidence (a file or a comment) is required for answers at level {0}. Missing for: {1}").format(
					" / ".join(sorted(needs)), ", ".join(missing)
				),
				title=_("Evidence Required"),
			)

	def calculate(self):
		config = get_config()
		for a in self.answers:
			opt = a.selected_option or ""
			a.points = config.points.get(opt, 0) if opt in LETTERS else 0
			a.selected_description = a.get(OPTION_FIELDS[opt]) if opt in LETTERS else ("Not applicable" if opt == NA else "")
		template, sections = self.template_sections()
		result = compute([a.as_dict() for a in self.answers], sections, template.weighting_method, config)
		self.set(
			"section_scores",
			[
				{
					"section_code": s.section_code,
					"section_title": s.section_title,
					"answered": s.answered,
					"applicable": s.applicable,
					"points": s.points,
					"max_points": s.max_points,
					"weight": s.weight,
					"score_pct": s.score_pct,
					"maturity_level": s.maturity_level,
					"reference": s.reference,
				}
				for s in result.sections
			],
		)
		for field in (
			"overall_score",
			"overall_points",
			"max_points",
			"maturity_level",
			"score_level",
			"interpretation",
			"gating_note",
			"answered_count",
			"question_count",
			"na_count",
			"findings_count",
			"immediate_count",
		):
			self.set(field, result.get(field))
		return result

	def create_actions(self):
		config = get_config()
		letters = {"A", "B", "C"} if config.create_actions_for == "A, B and C" else {"A", "B"}
		template = frappe.get_cached_doc("IA Maturity Template", self.template)
		owners = {s.section_code: s.owner_role for s in template.sections}
		base = getdate(self.assessment_date or today())
		for a in self.answers:
			opt = a.selected_option
			if opt not in letters:
				continue
			if frappe.db.exists("IA Maturity Action", {"assessment": self.name, "question_code": a.question_code}):
				continue
			nxt = LETTERS[LETTERS.index(opt) + 1]
			priority, timeframe, days = PRIORITY[opt]
			frappe.get_doc(
				{
					"doctype": "IA Maturity Action",
					"assessment": self.name,
					"entity": self.entity,
					"question_code": a.question_code,
					"section_title": a.section_title,
					"finding_title": f"{a.question_code} – {a.short_label or a.question_text}"[:140],
					"priority": priority,
					"timeframe": timeframe,
					"due_date": add_days(base, days),
					"action_owner": owners.get(a.section_code, ""),
					"current_level": f"{opt} – {LEVEL_NAMES[opt]}",
					"current_state": a.get(OPTION_FIELDS[opt]),
					"target_level": f"{nxt} – {LEVEL_NAMES[nxt]}",
					"recommended_action": a.get(OPTION_FIELDS[nxt]),
					"status": "Open",
				}
			).insert(ignore_permissions=True)


@frappe.whitelist()
def return_to_respondent(name, comments=None):
	"""Cancel a submitted assessment and give an amended draft back to the respondent."""
	if not frappe.has_permission("IA Maturity Assessment", "cancel", name):
		frappe.throw(_("Only an IA Maturity Manager can return an assessment."), frappe.PermissionError)
	doc = frappe.get_doc("IA Maturity Assessment", name)
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted assessments can be returned."))
	doc.review_status = "Returned"
	doc.reviewer_comments = comments or doc.reviewer_comments
	doc.save()  # update-after-submit records reviewer and timestamp
	doc.cancel()
	new = frappe.copy_doc(doc)
	new.amended_from = doc.name
	for field in ("review_status", "reviewer", "reviewed_on", "reviewer_comments"):
		new.set(field, None)
	new.docstatus = 0
	new.insert()
	return new.name
