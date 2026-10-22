# Copyright (c) 2026, IA Maturity Contributors
# License: MIT

from frappe.model.document import Document
from frappe.utils import today


class IAMaturityAction(Document):
	def validate(self):
		if not self.entity and self.assessment:
			import frappe

			self.entity = frappe.db.get_value("IA Maturity Assessment", self.assessment, "entity")
		if self.status == "Completed" and not self.completed_on:
			self.completed_on = today()
		if self.status != "Completed":
			self.completed_on = None
