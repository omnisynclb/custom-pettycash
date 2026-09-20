import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


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
