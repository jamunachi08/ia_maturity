# Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate


class IAAuditIssue(Document):
	def validate(self):
		if self.status != "Closed":
			self.closed_on = None
		if self.closed_on and self.raised_on and getdate(self.closed_on) < getdate(self.raised_on):
			frappe.throw(_("Closed On cannot be earlier than Raised On."))
		self.days_to_close = date_diff(self.closed_on, self.raised_on) if self.closed_on else None
