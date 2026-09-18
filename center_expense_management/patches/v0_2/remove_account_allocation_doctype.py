import frappe


def execute():
	if frappe.db.exists("DocType", "Petty Cash Account Allocation"):
		frappe.delete_doc(
			"DocType",
			"Petty Cash Account Allocation",
			force=True,
			ignore_permissions=True,
		)
