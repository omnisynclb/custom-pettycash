import frappe


def execute():
	frappe.db.sql(
		"""update `tabPetty Cash Settlement`
		set settlement_month = date_format(month, '%%Y-%%m'),
		active_month_key = case when docstatus < 2
			then concat(center_officer, ':', date_format(month, '%%Y-%%m')) else null end
		where month is not null"""
	)
	duplicate_settlement = frappe.db.sql(
		"""select active_month_key
		from `tabPetty Cash Settlement`
		where active_month_key is not null
		group by active_month_key having count(*) > 1 limit 1"""
	)
	if duplicate_settlement:
		frappe.throw("Resolve duplicate monthly Petty Cash Settlements before migrating.")
	_assert_no_duplicates(
		"Petty Cash Configuration",
		"center_officer",
		"Resolve duplicate Petty Cash Configurations before migrating.",
	)
	_assert_no_duplicates(
		"Petty Cash Whish",
		"month_and_year",
		"Resolve duplicate monthly Petty Cash Whish documents before migrating.",
	)

	frappe.db.add_unique("Petty Cash Configuration", ["center_officer"])
	frappe.db.add_unique("Petty Cash Whish", ["month_and_year"])
	frappe.db.add_unique("Petty Cash Settlement", ["active_month_key"])


def _assert_no_duplicates(doctype, fieldname, message):
	duplicate = frappe.db.sql(
		f"""select `{fieldname}`
		from `tab{doctype}`
		where `{fieldname}` is not null and `{fieldname}` != ''
		group by `{fieldname}` having count(*) > 1 limit 1"""
	)
	if duplicate:
		frappe.throw(message)
