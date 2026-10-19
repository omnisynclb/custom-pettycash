import frappe


def execute():
	"""Move open settlements from retired approval stages into the new closing flow."""
	if not frappe.db.table_exists("Petty Cash Settlement"):
		return

	state_map = {
		"Pending Treasurer Approval": "Pending Final Finance Review",
		"Pending President Approval": "Pending Accountant Closing",
	}
	for old_state, new_state in state_map.items():
		frappe.db.set_value(
			"Petty Cash Settlement",
			{"workflow_state": old_state, "docstatus": 0},
			"workflow_state",
			new_state,
			update_modified=False,
		)
