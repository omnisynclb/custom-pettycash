import frappe
from frappe.model.document import Document
from frappe.utils import cint


class PettyCashSettings(Document):
	def validate(self):
		if not 1 <= cint(self.reminder_day) <= 28:
			frappe.throw("Reminder Day must be between 1 and 28.")
		if not 1 <= cint(self.whish_send_day) <= 28:
			frappe.throw("Whish Send Day must be between 1 and 28.")
