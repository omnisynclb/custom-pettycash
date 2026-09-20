import frappe


DOCTYPE = "Petty Cash Configuration"


def execute():
	# Replace Customize Form layout-only fields with the standard Column Break
	# shipped in the DocType JSON. Business fields and their values are untouched.
	custom_column_breaks = frappe.get_all(
		"Custom Field",
		filters={"dt": DOCTYPE, "fieldtype": "Column Break"},
		pluck="name",
	)
	for name in custom_column_breaks:
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)

	frappe.db.delete(
		"Property Setter",
		{"doc_type": DOCTYPE, "property": "idx"},
	)
	frappe.clear_cache(doctype=DOCTYPE)
