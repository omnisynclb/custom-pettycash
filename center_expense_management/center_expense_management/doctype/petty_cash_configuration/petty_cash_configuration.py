# Copyright (c) 2026, OmniSync and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PettyCashConfiguration(Document):
	def validate(self):
		if flt(self.petty_cash_limit) <= 0:
			frappe.throw("Petty Cash Limit must be greater than zero.")

		duplicate = frappe.db.exists(
			"Petty Cash Configuration",
			{"center_officer": self.center_officer, "name": ["!=", self.name]},
		)
		if duplicate:
			frappe.throw("Only one Petty Cash Configuration is allowed per Center Officer.")

		companies = {
			frappe.db.get_value("Cost Center", self.cost_center, "company"),
			frappe.db.get_value("Account", self.petty_cash_account, "company"),
			frappe.db.get_value("Account", self.payment_account, "company"),
		}
		if None in companies or len(companies) != 1:
			frappe.throw("Cost Center, Petty Cash Account, and Payment Account must belong to one company.")

		for fieldname in ("petty_cash_account", "payment_account"):
			account = frappe.get_cached_doc("Account", self.get(fieldname))
			if account.is_group or account.disabled:
				frappe.throw(f"{self.meta.get_label(fieldname)} must be an enabled ledger account.")

		payment_account = frappe.get_cached_doc("Account", self.payment_account)
		if payment_account.root_type != "Asset":
			frappe.throw("Payment Account must be an Asset ledger account.")

		company = companies.pop()
		company_currency = frappe.db.get_value("Company", company, "default_currency")
		if payment_account.account_currency != company_currency:
			frappe.throw("Payment Account must use the company currency.")
		if self.currency != company_currency:
			frappe.throw("Whish Currency must match the company currency.")
