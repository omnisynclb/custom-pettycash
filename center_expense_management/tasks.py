from io import BytesIO

import frappe
from frappe.utils import cint, get_first_day, getdate, now_datetime, today
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def create_monthly_petty_cash_whish():
    get_or_create_monthly_petty_cash_whish(get_first_day(today()))


def get_or_create_monthly_petty_cash_whish(month):
    month = get_first_day(month)

    existing = frappe.db.exists(
        "Petty Cash Whish",
        {
            "month_and_year": month
        }
    )

    if existing:
        return existing

    whish = frappe.get_doc({
        "doctype": "Petty Cash Whish",
        "month_and_year": month
    })

    try:
        whish.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # Another worker created the same uniquely named monthly record.
        return frappe.db.get_value(
            "Petty Cash Whish", {"month_and_year": month}, "name"
        )

    return whish.name


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


def generate_whish_excel_attachment(payment_date=None, whish_name=None):
    if not whish_name and payment_date:
        whish_month = get_first_day(payment_date)
        whish_name = frappe.db.get_value(
            "Petty Cash Whish", {"month_and_year": whish_month}, "name"
        )
    if not whish_name:
        frappe.throw("The monthly Petty Cash Whish document does not exist.")

    whish = frappe.get_doc("Petty Cash Whish", whish_name)
    rows = [[
        "Number",
        "NAME",
        "Phone Number",
        "Whish ID",
        "Salary received by the employee ( NET)",
        "Currency",
    ]]
    for number, row in enumerate(whish.employees, start=1):
        rows.append([
            number,
            _safe_excel_value(row.employee_name),
            _safe_excel_value(row.phone_number),
            _safe_excel_value(row.whish_id),
            row.salary_received_net,
            _safe_excel_value(row.currency),
        ])

    content = _make_whish_excel(rows)
    file_version = now_datetime().strftime("%Y%m%d-%H%M%S-%f")
    attachment_name = f"{whish.name}-v{file_version}.xlsx"
    old_files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Petty Cash Whish",
            "attached_to_name": whish.name,
            "file_name": ["like", "%.xlsx"],
        },
        pluck="name",
    )
    for old_file in old_files:
        frappe.delete_doc("File", old_file, ignore_permissions=True)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": attachment_name,
        "content": content,
        "is_private": 1,
        "attached_to_doctype": "Petty Cash Whish",
        "attached_to_name": whish.name,
    })
    file_doc.save(ignore_permissions=True)
    whish.db_set("excel_file", file_doc.file_url)
    return file_doc.name


# Backward-compatible target for jobs queued before this change. It deliberately
# refreshes the attachment only and never sends an email.
def generate_and_email_whish_excel(payment_date):
    return generate_whish_excel_attachment(payment_date=payment_date)


@frappe.whitelist()
def send_whish_excel_now(whish_name):
    if not ({"LSA Finance Approver", "System Manager"} & set(frappe.get_roles())):
        frappe.throw("Only Finance or System Manager may send the Whish Excel.", frappe.PermissionError)
    return _send_whish_excel(whish_name)


def send_scheduled_whish_excel():
    settings = frappe.get_single("Petty Cash Settings")
    current_date = getdate(today())
    if (
        not settings.enable_automatic_whish_email
        or current_date.day != cint(settings.whish_send_day)
    ):
        return

    whish_name = frappe.db.get_value(
        "Petty Cash Whish",
        {"month_and_year": get_first_day(current_date)},
        "name",
    )
    if not whish_name:
        return

    sent_on = frappe.db.get_value("Petty Cash Whish", whish_name, "excel_email_sent_on")
    if sent_on:
        return

    return _send_whish_excel(whish_name)


def _send_whish_excel(whish_name):
    file_name = generate_whish_excel_attachment(whish_name=whish_name)
    file_doc = frappe.get_doc("File", file_name)
    content = file_doc.get_content()
    whish = frappe.get_doc("Petty Cash Whish", whish_name)

    settings = frappe.get_single("Petty Cash Settings")
    if not settings.whish_email:
        frappe.throw("Whish Email must be configured in Petty Cash Settings.")

    frappe.sendmail(
        recipients=[settings.whish_email],
        subject=f"Petty Cash Whish - {whish.name}",
        message=f"<p>Attached is the current Whish payment file for {frappe.utils.escape_html(whish.name)}.</p>",
        attachments=[{"fname": file_doc.file_name, "fcontent": content}],
    )
    whish.db_set("excel_email_sent_on", now_datetime())
    return file_name


def _safe_excel_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value or ""


def _make_whish_excel(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Whish"

    for row in rows:
        sheet.append(row)

    header_fill = PatternFill("solid", fgColor="9DC3E6")
    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in sheet.iter_rows():
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    for cell in sheet["E"][1:]:
        cell.number_format = "#,##0.00"

    widths = {"A": 12, "B": 30, "C": 18, "D": 18, "E": 38, "F": 14}
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width

    sheet.freeze_panes = "A2"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
