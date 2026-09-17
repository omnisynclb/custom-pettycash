import frappe
from frappe.utils import get_first_day, today


def create_monthly_petty_cash_whish():
    month = get_first_day(today())

    existing = frappe.db.exists(
        "Petty Cash Whish",
        {
            "month_and_year": month
        }
    )

    if existing:
        return

    whish = frappe.get_doc({
        "doctype": "Petty Cash Whish",
        "month_and_year": month
    })

    try:
        whish.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # Another worker created the same uniquely named monthly record.
        return


def generate_and_email_settlement_report(settlement_name):
    settlement = frappe.get_doc("Petty Cash Settlement", settlement_name)
    if settlement.docstatus != 1 or settlement.payment_status != "Paid":
        frappe.throw("Only a paid, submitted settlement can be reported.")

    file_name = settlement.generate_pdf_report()
    settlement.send_pdf_report_by_email(file_name)
    settlement.db_set("report_delivery_status", "Sent")
