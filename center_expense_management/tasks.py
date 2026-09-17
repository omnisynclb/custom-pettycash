import frappe
from frappe.utils import cint, get_first_day, getdate, now_datetime, today
from frappe.utils.xlsxutils import make_xlsx


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


@frappe.whitelist()
def send_monthly_reminders(force=0):
    force = cint(force)
    if force and not ({"LSA Finance Approver", "System Manager"} & set(frappe.get_roles())):
        frappe.throw("Only Finance or System Manager may send reminders.", frappe.PermissionError)

    settings = frappe.get_single("Petty Cash Settings")
    current_date = getdate(today())
    month_key = current_date.strftime("%Y-%m")

    if not force:
        if not settings.enable_monthly_reminders or current_date.day != cint(settings.reminder_day):
            return 0

    sent = 0
    configurations = frappe.get_all(
        "Petty Cash Configuration",
        fields=["name", "center_officer", "reminder_email", "last_reminder_month"],
    )
    for config in configurations:
        if not force and config.last_reminder_month == month_key:
            continue
        if frappe.db.exists(
            "Petty Cash Settlement",
            {"center_officer": config.center_officer, "settlement_month": month_key, "docstatus": ["<", 2]},
        ):
            continue

        recipient = config.reminder_email or _employee_email(config.center_officer)
        if not recipient:
            frappe.log_error(
                f"No reminder email is configured for Employee {config.center_officer}",
                "Petty Cash Reminder Skipped",
            )
            continue

        frappe.sendmail(
            recipients=[recipient],
            subject=settings.reminder_subject,
            message=f"<p>{frappe.utils.escape_html(settings.reminder_message)}</p>",
        )
        frappe.db.set_value(
            "Petty Cash Configuration",
            config.name,
            {"last_reminder_month": month_key, "reminder_sent_on": now_datetime()},
            update_modified=False,
        )
        sent += 1

    return sent


def _employee_email(employee):
    user = frappe.db.get_value("Employee", employee, "user_id")
    if not user:
        return None
    return frappe.db.get_value("User", user, "email") or user


def generate_and_email_whish_excel(payment_date):
    whish_month = get_first_day(payment_date)
    whish_name = frappe.db.get_value("Petty Cash Whish", {"month_and_year": whish_month}, "name")
    if not whish_name:
        frappe.throw("The monthly Petty Cash Whish document does not exist.")

    settings = frappe.get_single("Petty Cash Settings")
    if not settings.whish_email:
        frappe.throw("Whish Email must be configured in Petty Cash Settings.")

    whish = frappe.get_doc("Petty Cash Whish", whish_name)
    rows = [["Employee ID", "Name", "Phone Number", "Whish ID", "Amount", "Currency", "Settlement"]]
    for row in whish.employees:
        rows.append([
            _safe_excel_value(row.employee),
            _safe_excel_value(row.employee_name),
            _safe_excel_value(row.phone_number),
            _safe_excel_value(row.whish_id),
            row.salary_received_net,
            _safe_excel_value(row.currency),
            _safe_excel_value(row.settlement),
        ])

    content = make_xlsx(rows, "Petty Cash Whish").getvalue()
    old_file = frappe.db.get_value(
        "File",
        {"attached_to_doctype": "Petty Cash Whish", "attached_to_name": whish.name, "file_name": f"{whish.name}.xlsx"},
        "name",
    )
    if old_file:
        frappe.delete_doc("File", old_file, ignore_permissions=True)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"{whish.name}.xlsx",
        "content": content,
        "is_private": 1,
        "attached_to_doctype": "Petty Cash Whish",
        "attached_to_name": whish.name,
    })
    file_doc.save(ignore_permissions=True)
    whish.db_set("excel_file", file_doc.file_url)

    frappe.sendmail(
        recipients=[settings.whish_email],
        subject=f"Petty Cash Whish - {whish.name}",
        message=f"<p>Attached is the current Whish payment file for {frappe.utils.escape_html(whish.name)}.</p>",
        attachments=[{"fname": file_doc.file_name, "fcontent": content}],
    )
    whish.db_set("excel_email_sent_on", now_datetime())
    return file_doc.name


def _safe_excel_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value or ""
