# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class IAMaturityTemplate(Document):
	def validate(self):
		codes = [s.section_code.strip() for s in self.sections]
		dupes = {c for c in codes if codes.count(c) > 1}
		if dupes:
			frappe.throw(_("Duplicate section codes: {0}").format(", ".join(sorted(dupes))))
		qcodes = [q.question_code.strip() for q in self.questions]
		dupes = {c for c in qcodes if qcodes.count(c) > 1}
		if dupes:
			frappe.throw(_("Duplicate question codes: {0}").format(", ".join(sorted(dupes))))
		bands = {b.level_name.lower() for b in frappe.get_single("IA Maturity Settings").bands if b.level_name}
		for q in self.questions:
			q.section_code = q.section_code.strip()
			if q.section_code not in codes:
				frappe.throw(
					_("Question {0}: section code {1} is not defined in the Sections table.").format(
						q.question_code, q.section_code
					)
				)
			if q.is_gating:
				if not q.gate_cap_level:
					frappe.throw(_("Question {0}: set 'Cap Overall Level At' for a gating question.").format(q.question_code))
				if bands and q.gate_cap_level.lower() not in bands:
					frappe.throw(
						_("Question {0}: cap level {1} does not match any maturity band in IA Maturity Settings.").format(
							q.question_code, q.gate_cap_level
						)
					)
		for s in self.sections:
			if not any(q.section_code == s.section_code for q in self.questions):
				frappe.msgprint(_("Section {0} has no questions.").format(s.section_code), indicator="orange")

	def on_update(self):
		frappe.clear_document_cache(self.doctype, self.name)
