# Copyright (c) 2026, OmniSync and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_first_day, getdate


class PettyCashWhish(Document):

    def autoname(self):
        if not self.month_and_year:
            frappe.throw("Month and Year is required.")

        self.month_and_year = get_first_day(self.month_and_year)
        value = getdate(self.month_and_year)
        self.name = f"WHISH-{value:%Y-%m}"

    def validate(self):
        if not self.month_and_year:
            frappe.throw("Month and Year is required.")
        self.month_and_year = get_first_day(self.month_and_year)
