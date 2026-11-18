# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime, today

from ia_maturity.compat import in_test
from ia_maturity.issues import apply_auto_answers
from ia_maturity.grc import scope
from ia_maturity.scoring import (
	LETTERS,
	LEVEL_NAMES,
	NA,
	PRIORITY,
	answer_points,
	compute,
	get_config,
	normalize_selected,
	parse_selected,
	selected_statements,
	worst_letter,
)

OPTION_FIELDS = {"A": "option_a", "B": "option_b", "C": "option_c", "D": "option_d"}
SNAPSHOT_FIELDS = (
	"question_code",
	"topic_code",
	"topic_title",
	"topic_title_ar",
	"source_ref",
	"section_code",
	"short_label",
	"question_text",
	"guidance",
	"option_a",
	"option_b",
	"option_c",
	"option_d",
	"allow_na",
	"selection_mode",
	"multi_score_method",
	"is_gating",
	"gate_trigger",
	"gate_cap_level",
	"auto_source",
	"short_label_ar",
	"question_text_ar",
	"guidance_ar",
	"option_a_ar",
	"option_b_ar",
	"option_c_ar",
	"option_d_ar",
)
# allow_comment / allow_attachment are resolved (not copied raw) in load_questions.


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
		if self.language not in ("en", "ar"):
			self.language = "en"
		# GRC is a self-reported instrument. IA issue-register rules never answer it.
		kind = self.get("grc_assessment_type") or frappe.db.get_value("IA Maturity Template", self.template, "assessment_type")
		from ia_maturity.grc.assessment_types import behaves_like_grc
		if not behaves_like_grc(kind):
			apply_auto_answers(self)
		self.validate_answers()
		self.calculate()

	def before_submit(self):
		from ia_maturity.grc.organization_profile import prepare_submission
		prepare_submission(self)
		scope.require_ready(self)
		missing = [a.question_code for a in scope.answers(self) if not a.selected_option]
		if missing:
			frappe.throw(
				_("Answer every question before submitting. Unanswered: {0}").format(", ".join(missing)),
				title=_("Incomplete Assessment"),
			)
		self.validate_evidence()
		self.review_status = "Pending Review"

	def on_submit(self):
		self.create_actions()
		from ia_maturity.grc.security import enabled
		if enabled():
			return
		frappe.enqueue(
			"ia_maturity.notifications.send_submission_email",
			assessment=self.name,
			enqueue_after_commit=True,
			now=in_test(),
		)

	def on_cancel(self):
		for name in frappe.get_all(
			"IA Maturity Action",
			filters={"assessment": self.name, "status": ["in", ["Open", "In Progress", "Pending Verification"]]},
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
		from ia_maturity.grc.response_policy import resolve_for_question
		template = frappe.get_doc("IA Maturity Template", self.template)
		titles = {s.section_code: s.section_title for s in template.sections}
		titles_ar = {s.section_code: s.section_title_ar for s in template.sections}
		previous = {a.question_code: a for a in self.answers}
		self.set("answers", [])
		for q in template.questions:
			row = {f: q.get(f) for f in SNAPSHOT_FIELDS}
			row["selection_mode"] = (row.get("selection_mode") or "Single").strip() or "Single"
			row["multi_score_method"] = (row.get("multi_score_method") or "Highest").strip() or "Highest"
			row["section_title"] = titles.get(q.section_code, q.section_code)
			row["section_title_ar"] = titles_ar.get(q.section_code) or ""
			# Snapshot resolved flags (question → section → questionnaire).
			row.update(resolve_for_question(template, q))
			old = previous.get(q.question_code)
			if old:
				row.update(
					selected_option=old.selected_option,
					comment=old.comment,
					evidence=old.evidence,
					auto_calculated=old.auto_calculated,
				)
			self.append("answers", row)
		return self.answers

	def template_sections(self):
		if self.get("grc_sections_snapshot"):
			policy = get_config(self)
			return frappe._dict(weighting_method=policy.weighting_method), frappe.parse_json(self.grc_sections_snapshot)
		template = frappe.get_cached_doc("IA Maturity Template", self.template)
		return template, [s.as_dict() for s in template.sections]

	def validate_answers(self):
		for a in scope.answers(self):
			multi = (a.selection_mode or "Single") == "Multi"
			normalized = normalize_selected(a.selected_option, multi=multi)
			if normalized is None:
				frappe.throw(_("Row {0}: invalid answer {1}.").format(a.idx, a.selected_option))
			a.selected_option = normalized
			if normalized == NA and not a.allow_na:
				frappe.throw(
					_("Row {0}: 'Not applicable' is not allowed for question {1}.").format(a.idx, a.question_code)
				)

	def validate_evidence(self):
		from ia_maturity.grc.response_policy import flags_for_answer
		rule = get_config(self).evidence_required_from or ""
		if not rule:
			return
		needs = {"C", "D"} if rule.startswith("C") else {"D"}
		missing = []
		for a in scope.answers(self):
			kind, letters = parse_selected(a.selected_option)
			# Evidence when any selected letter meets the threshold (multi) or the single letter does.
			if kind != "letters" or not (set(letters) & needs):
				continue
			flags = flags_for_answer(a)
			if not flags["allow_comment"] and not flags["allow_attachment"]:
				continue
			has_file = flags["allow_attachment"] and a.evidence
			has_comment = flags["allow_comment"] and (a.comment or "").strip()
			if not (has_file or has_comment):
				missing.append(a.question_code)
		if missing:
			frappe.throw(
				_("Evidence (a file or a comment) is required for answers at level {0}. Missing for: {1}").format(
					" / ".join(sorted(needs)), ", ".join(missing)
				),
				title=_("Evidence Required"),
			)

	def calculate(self):
		config = get_config(self)
		for a in scope.answers(self):
			a.points = answer_points(a, config.points, config.max_points)
			a.selected_description = selected_statements(a)
		template, sections = self.template_sections()
		result = compute([a.as_dict() for a in scope.answers(self)], scope.sections(self, sections), template.weighting_method, config)
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
					"section_title_ar": s.section_title_ar,
					"reference_ar": s.reference_ar,
					"owner_role": s.owner_role,
					"owner_role_ar": s.owner_role_ar,
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
			"interpretation_ar",
			"gating_note_ar",
			"answered_count",
			"question_count",
			"na_count",
			"findings_count",
			"immediate_count",
		):
			self.set(field, result.get(field))
		return result

	def create_actions(self):
		config = get_config(self)
		letters = {"A", "B", "C"} if config.create_actions_for == "A, B and C" else {"A", "B"}
		template = frappe.get_cached_doc("IA Maturity Template", self.template)
		owners = {s.section_code: s.owner_role for s in template.sections}
		base = getdate(self.assessment_date or today())
		for a in scope.answers(self):
			opt = worst_letter(a)
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


REVIEW_ROLES = {"IA Maturity Reviewer", "IA Maturity Manager", "System Manager"}


@frappe.whitelist(methods=["POST"])
def update_review(name, status, comments=None):
	"""Set the review status of a submitted assessment.

	Reviewers have read-only access to the assessment itself (they must not change answers), so
	the review fields are updated here after an explicit role check instead of via a form save.
	"""
	if frappe.session.user != "Administrator" and not (REVIEW_ROLES & set(frappe.get_roles())):
		frappe.throw(_("Only reviewers can update the review status."), frappe.PermissionError)
	if status not in ("Reviewed", "Approved"):
		frappe.throw(_("Invalid review status {0}. Use Return to Respondent to send it back.").format(status))
	doc = frappe.get_doc("IA Maturity Assessment", name)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted assessments can be reviewed."))
	doc.review_status = status
	if comments is not None and comments.strip():
		doc.reviewer_comments = comments.strip()
	doc.flags.ignore_permissions = True
	doc.save()
	return {"review_status": doc.review_status, "reviewer": doc.reviewer, "reviewed_on": str(doc.reviewed_on)}
