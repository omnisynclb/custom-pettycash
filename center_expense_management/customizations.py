import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission


def sync_supplier_permissions():
	"""Allow LSA Accountants to maintain suppliers without broad purchasing roles."""
	filters = {
		"parent": "Supplier",
		"role": "LSA Accountant",
		"permlevel": 0,
		"if_owner": 0,
	}
	permission_name = frappe.db.get_value("Custom DocPerm", filters, "name")
	if not permission_name:
		add_permission("Supplier", "LSA Accountant", permlevel=0, ptype="read")
		permission_name = frappe.db.get_value("Custom DocPerm", filters, "name")

	frappe.db.set_value(
		"Custom DocPerm",
		permission_name,
		{
			"select": 1,
			"read": 1,
			"write": 1,
			"create": 1,
			"report": 1,
			"print": 1,
			"email": 1,
			"delete": 0,
		},
		update_modified=False,
	)
	frappe.clear_cache(doctype="Supplier")


def sync_journal_entry_fields():
	create_custom_fields(
		{
			"Journal Entry": [
				{
					"fieldname": "petty_cash_reference_section",
					"fieldtype": "Section Break",
					"label": "Petty Cash Reference",
					"insert_after": "posting_date",
					"depends_on": "eval:doc.petty_cash_settlement",
				},
				{
					"fieldname": "petty_cash_settlement",
					"fieldtype": "Link",
					"label": "Petty Cash Settlement",
					"options": "Petty Cash Settlement",
					"insert_after": "petty_cash_reference_section",
					"read_only": 1,
				},
				{
					"fieldname": "petty_cash_center_officer",
					"fieldtype": "Link",
					"label": "Center Officer",
					"options": "Employee",
					"insert_after": "petty_cash_settlement",
					"read_only": 1,
				},
				{
					"fieldname": "petty_cash_reference_column",
					"fieldtype": "Column Break",
					"insert_after": "petty_cash_center_officer",
				},
				{
					"fieldname": "petty_cash_center_officer_name",
					"fieldtype": "Data",
					"label": "Center Officer Name",
					"insert_after": "petty_cash_reference_column",
					"read_only": 1,
				},
			],
		},
		update=True,
	)

	for settlement in frappe.get_all(
		"Petty Cash Settlement",
		filters={"journal_entry": ["is", "set"]},
		fields=["name", "journal_entry", "center_officer"],
	):
		frappe.db.set_value(
			"Journal Entry",
			settlement.journal_entry,
			{
				"petty_cash_settlement": settlement.name,
				"petty_cash_center_officer": settlement.center_officer,
				"petty_cash_center_officer_name": frappe.db.get_value(
					"Employee", settlement.center_officer, "employee_name"
				),
			},
			update_modified=False,
		)


def close_petty_cash_payment(doc, method=None):
	if not doc.get("petty_cash_settlement"):
		return
	frappe.db.set_value(
		"Petty Cash Settlement",
		doc.petty_cash_settlement,
		{
			"workflow_state": "Completed",
			"payment_status": "Paid",
			"payment_date": doc.posting_date,
		},
		update_modified=False,
	)


def reopen_petty_cash_payment(doc, method=None):
	if not doc.get("petty_cash_settlement"):
		return
	frappe.db.set_value(
		"Petty Cash Settlement",
		doc.petty_cash_settlement,
		{
			"workflow_state": "Approved for Whish Payment",
			"payment_status": "Pending Journal Entry",
			"payment_date": None,
		},
		update_modified=False,
	)
