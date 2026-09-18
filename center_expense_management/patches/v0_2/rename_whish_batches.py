import frappe


def execute():
	batches = frappe.get_all(
		"Petty Cash Whish",
		fields=["name", "month_and_year"],
		as_list=True,
	)
	for name, month_and_year in batches:
		if not month_and_year:
			continue
		month = frappe.utils.getdate(month_and_year)
		new_name = f"WHISH-{month:%Y-%m}"
		if name != new_name and not frappe.db.exists("Petty Cash Whish", new_name):
			frappe.rename_doc("Petty Cash Whish", name, new_name, force=True)
