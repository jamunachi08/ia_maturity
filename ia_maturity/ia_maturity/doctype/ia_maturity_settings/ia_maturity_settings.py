# Copyright (c) 2026, IA Maturity Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class IAMaturitySettings(Document):
	def validate(self):
		pts = [flt(self.points_a), flt(self.points_b), flt(self.points_c), flt(self.points_d)]
		if not flt(self.points_d):
			frappe.throw(_("Points for D must be greater than zero."))
		if pts != sorted(pts):
			frappe.throw(_("Points must increase from A to D."))
		names = [b.level_name.strip().lower() for b in self.bands if b.level_name]
		if len(names) != len(set(names)):
			frappe.throw(_("Maturity band names must be unique."))
		self.bands.sort(key=lambda b: flt(b.min_score))
		for i, b in enumerate(self.bands, start=1):
			b.idx = i
		if self.bands and flt(self.bands[0].min_score) > 0:
			frappe.throw(_("The lowest maturity band must start at 0%."))

	def on_update(self):
		frappe.clear_document_cache(self.doctype, self.name)
