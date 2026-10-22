import frappe


def execute():
	"""Move unfinished legacy settlements to the manual Whish payment stage."""
	frappe.db.set_single_value(
		"Petty Cash Settings", "enable_automatic_whish_email", 0, update_modified=False
	)

	legacy_states = ("Pending Final Finance Review", "Pending Accountant Closing")
	settlements = frappe.get_all(
		"Petty Cash Settlement",
		filters={"workflow_state": ["in", legacy_states], "docstatus": ["<", 2]},
		pluck="name",
	)

	for name in settlements:
		frappe.db.set_value(
			"Petty Cash Settlement",
			name,
			{"workflow_state": "Approved for Whish Payment", "docstatus": 1},
			update_modified=False,
		)
		frappe.db.set_value(
			"Petty Cash Expense",
			{"parent": name, "parenttype": "Petty Cash Settlement"},
			"docstatus",
			1,
			update_modified=False,
		)
		frappe.get_doc("Petty Cash Settlement", name).update_petty_cash_whish()
