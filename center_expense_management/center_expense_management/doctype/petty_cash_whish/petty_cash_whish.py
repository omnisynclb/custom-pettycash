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

    def on_update(self):
        before = self.get_doc_before_save()
        if not before or not self.has_value_changed("employees"):
            return

        frappe.enqueue(
            "center_expense_management.tasks.generate_whish_excel_attachment",
            queue="short",
            enqueue_after_commit=True,
            deduplicate=True,
            job_id=f"petty-cash-whish-refresh-{self.name}",
            whish_name=self.name,
        )
