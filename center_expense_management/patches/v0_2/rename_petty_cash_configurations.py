import frappe


def execute():
	configurations = frappe.get_all(
		"Petty Cash Configuration",
		fields=["name", "center_officer"],
		as_list=True,
	)
	for name, center_officer in configurations:
		new_name = f"PCC-{center_officer}"
		if name != new_name and not frappe.db.exists("Petty Cash Configuration", new_name):
			frappe.rename_doc("Petty Cash Configuration", name, new_name, force=True)
