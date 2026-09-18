import frappe


def execute():
	frappe.db.sql(
		"""update `tabPetty Cash Settlement`
		set month_name = case month(month)
			when 1 then 'January'
			when 2 then 'February'
			when 3 then 'March'
			when 4 then 'April'
			when 5 then 'May'
			when 6 then 'June'
			when 7 then 'July'
			when 8 then 'August'
			when 9 then 'September'
			when 10 then 'October'
			when 11 then 'November'
			when 12 then 'December'
		end,
		settlement_year = year(month)
		where month is not null"""
	)
