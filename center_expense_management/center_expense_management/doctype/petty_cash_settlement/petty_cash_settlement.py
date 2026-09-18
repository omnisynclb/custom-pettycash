# Copyright (c) 2026, OmniSync and contributors
# For license information, please see license.txt..

import re

import frappe

from frappe import _
from erpnext.accounts.utils import get_balance_on
from frappe.model.document import Document
from frappe.utils import cint, escape_html, flt, formatdate, validate_email_address
from frappe.utils.pdf import get_pdf

from center_expense_management.permissions import can_review_all, employee_for_user


BUSINESS_FIELDS = {
    "center_officer",
    "month",
    "month_name",
    "settlement_year",
    "settlement_month",
    "expenses",
    "account",
    "payment_method",
    "report_email",
}

EXPENSE_BUSINESS_FIELDS = (
    "name",
    "expense_item",
    "expense_date",
    "invoice_number",
    "supplier",
    "related_details",
    "amount",
    "receipt",
)

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


class PettyCashSettlement(Document):

    def validate(self):
        self.bind_center_officer_to_user()
        self.protect_initial_finance_fields()
        self.set_settlement_month()
        self.validate_stage_changes()
        self.validate_center_officer_and_month()
        self.load_petty_cash_configuration()
        self.validate_expenses()
        self.calculate_totals()
        self.validate_finance_account()

        self.amount = self.total_expenses

        if self.workflow_state == "Completed":
            if self.payment_method != "Whish":
                frappe.throw("Payment Method must be Whish before completion.")
            if not self.report_email:
                frappe.throw("Report Email is required before completion.")
            validate_email_address(self.report_email, throw=True)

    def protect_initial_finance_fields(self):
        if not self.is_new() or frappe.session.user == "Administrator":
            return
        if "LSA Finance Approver" not in frappe.get_roles():
            self.account = None
            self.report_email = None
            self.payment_method = "Whish"

    def set_settlement_month(self):
        value = None
        if self.month_name and self.settlement_year:
            if self.month_name not in MONTH_NAMES:
                frappe.throw("Select a valid settlement month.")
            year = cint(self.settlement_year)
            if not 2000 <= year <= 2100:
                frappe.throw("Settlement Year must be between 2000 and 2100.")
            value = f"{year:04d}-{MONTH_NAMES.index(self.month_name) + 1:02d}"
        elif self.settlement_month:
            value = self.settlement_month.strip()
        elif self.month:
            value = frappe.utils.getdate(self.month).strftime("%Y-%m")

        if not value or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            frappe.throw("Month and Year are required.")

        self.settlement_month = value
        self.month = frappe.utils.get_first_day(f"{value}-01")
        selected = frappe.utils.getdate(self.month)
        self.month_name = MONTH_NAMES[selected.month - 1]
        self.settlement_year = selected.year
        self.active_month_key = (
            f"{self.center_officer}:{self.settlement_month}" if self.docstatus != 2 else None
        )

    def on_update(self):
        if (
            self.workflow_state == "Completed"
            and self.has_value_changed("workflow_state")
        ):
            self.create_whish_journal_entry()
            self.db_set("report_delivery_status", "Queued")
            frappe.enqueue(
                "center_expense_management.tasks.generate_and_email_settlement_report",
                queue="short",
                enqueue_after_commit=True,
                deduplicate=True,
                job_id=f"petty-cash-report-{self.name}",
                settlement_name=self.name,
            )
            frappe.enqueue(
                "center_expense_management.tasks.generate_and_email_whish_excel",
                queue="short",
                enqueue_after_commit=True,
                deduplicate=True,
                job_id=f"petty-cash-whish-{self.name}",
                payment_date=self.payment_date,
            )

    def on_cancel(self):
        self.cancel_payment_artifacts()
        self.db_set("active_month_key", None)

    def bind_center_officer_to_user(self):
        if can_review_all():
            return

        employee = employee_for_user()
        if not employee:
            frappe.throw("Your user must be linked to an active Employee record.", frappe.PermissionError)

        if self.is_new():
            self.center_officer = employee
        elif self.center_officer != employee:
            frappe.throw("Center Officers may only maintain their own settlements.", frappe.PermissionError)

    def validate_stage_changes(self):
        before = self.get_doc_before_save()
        if not before:
            return

        previous_state = before.workflow_state or "Draft"
        allowed = (
            BUSINESS_FIELDS - {"account", "payment_method", "report_email"}
            if previous_state == "Draft"
            else set()
        )
        if previous_state == "Pending Finance Review":
            allowed = {"account", "payment_method", "report_email"}

        changed = {
            field
            for field in BUSINESS_FIELDS - {"expenses"}
            if self.has_value_changed(field)
        }
        if self.expenses_have_business_changes(before):
            changed.add("expenses")

        forbidden = changed - allowed
        if forbidden:
            labels = ", ".join(sorted(self.meta.get_label(field) for field in forbidden))
            frappe.throw(f"These fields cannot be changed during {previous_state}: {labels}.")

    def expenses_have_business_changes(self, before):
        """Ignore retired child fields while protecting submitted expense details."""
        if len(self.expenses) != len(before.expenses):
            return True

        current_rows = [
            tuple(row.get(field) for field in EXPENSE_BUSINESS_FIELDS)
            for row in self.expenses
        ]
        previous_rows = [
            tuple(row.get(field) for field in EXPENSE_BUSINESS_FIELDS)
            for row in before.expenses
        ]
        return current_rows != previous_rows

    def validate_finance_account(self):
        if self.account:
            account = frappe.get_cached_doc("Account", self.account)
            if (
                account.is_group
                or account.disabled
                or account.root_type != "Expense"
                or account.company != self.company
            ):
                frappe.throw("Finance Account must be an enabled Expense ledger account for this company.")

        if not self._doc_before_save:
            return

        previous_state = self._doc_before_save.get("workflow_state")

        if (
            previous_state == "Pending Finance Review"
            and self.workflow_state == "Pending Operations Approval"
        ):
            if not self.account:
                frappe.throw("Finance must select an Account before approving the settlement.")
            if self.payment_method != "Whish":
                frappe.throw("Payment Method must be Whish before Finance approval.")
            if not self.report_email:
                frappe.throw("Report Email is required before Finance approval.")
            validate_email_address(self.report_email, throw=True)

    def validate_center_officer_and_month(self):
        if not self.center_officer or not self.month:
            return

        existing = frappe.db.exists(
            "Petty Cash Settlement",
            {
                "center_officer": self.center_officer,
                "settlement_month": self.settlement_month,
                "name": ["!=", self.name]
            }
        )

        if existing:
            frappe.throw(
                "A Petty Cash Settlement already exists for this Center Officer and month."
            )
    def update_petty_cash_whish(self):
        if not self.payment_date:
            return

        # Convert payment date to the first day of that month.
        # Example: 2026-09-16 -> 2026-09-01
        whish_month = frappe.utils.get_first_day(self.payment_date)

        # Find the Petty Cash Whish for the payment month.
        whish_name = frappe.db.get_value(
            "Petty Cash Whish",
            {"month_and_year": whish_month},
            "name"
        )

        if not whish_name:
            frappe.throw(
                _(
                    "No Petty Cash Whish was found for {0}."
                ).format(
                    frappe.utils.formatdate(
                        whish_month,
                        "MMMM yyyy"
                    )
                )
            )

        # Center Officer is linked to Employee.
        employee = frappe.get_doc("Employee", self.center_officer)

        # Load the existing Petty Cash Whish.
        whish = frappe.get_doc("Petty Cash Whish", whish_name)

        # Idempotency is based on the settlement, not a non-unique display name.
        for row in whish.employees:
            if row.settlement == self.name:
                return

        # Add the employee's payment information.
        whish.append(
            "employees",
            {
                "employee_name": employee.employee_name,
                "employee": employee.name,
                "settlement": self.name,
                "phone_number": self.whish_phone_number,
                "whish_id": self.whish_id,
                "salary_received_net": self.total_expenses,
                "currency": self.currency,
            }
        )

        whish.flags.ignore_permissions = True
        whish.save()

    def load_petty_cash_configuration(self):
        before = self.get_doc_before_save()
        if before and (before.workflow_state or "Draft") != "Draft":
            return

        config = frappe.db.get_value(
            "Petty Cash Configuration",
            {"center_officer": self.center_officer},
            [
                "cost_center", "petty_cash_account", "payment_account", "petty_cash_limit",
                "whish_phone_number", "whish_id", "currency",
            ],
            as_dict=True
        )

        if not config:
            frappe.throw(
                "No Petty Cash Configuration was found for this Center Officer."
            )

        self.cost_center = config.cost_center
        self.petty_cash_account = config.petty_cash_account
        self.payment_account = config.payment_account
        self.petty_cash_limit = config.petty_cash_limit
        self.company = frappe.db.get_value("Cost Center", config.cost_center, "company")
        self.whish_phone_number = config.whish_phone_number
        self.whish_id = config.whish_id
        self.currency = config.currency

    @frappe.whitelist()
    def load_account_balance(self):
        if "LSA Finance Approver" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
           frappe.throw("Only Finance may select and inspect the settlement account.", frappe.PermissionError)

        if self.workflow_state != "Pending Finance Review":
           frappe.throw("The account can only be selected during Finance Review.")

        if not self.account:
           self.amount = 0
           return

        account = frappe.get_cached_doc("Account", self.account)

        if not frappe.has_permission("Account", "read", account.name):
           frappe.throw("You do not have permission to read this Account.", frappe.PermissionError)

        if account.is_group:
           frappe.throw(
               _("Please select a ledger account, not an account group.")
           )

        if account.disabled or account.company != self.company or account.root_type != "Expense":
           frappe.throw(_("Select an enabled Expense ledger account for {0}.").format(self.company))

        # Do not persist or disclose an unrelated ledger balance through the settlement.
        return get_balance_on(
          account=self.account,
          date=frappe.utils.today(),
          company=account.company
        )

    def validate_expenses(self):
        if not self.expenses:
            frappe.throw(
                "At least one expense is required."
            )

        for expense in self.expenses:

            if not expense.amount or expense.amount <= 0:
                frappe.throw(
                    f"Expense row {expense.idx}: Amount must be greater than zero."
                )


            if not expense.receipt:
                frappe.throw(
                    f"Receipt is required for expense row {expense.idx}."
                )

            receipt = frappe.db.get_value(
                "File", {"file_url": expense.receipt}, ["name", "is_private"], as_dict=True
            )
            if not receipt or not receipt.is_private:
                frappe.throw(f"Expense row {expense.idx}: Receipt must be a valid private File attachment.")

            if frappe.utils.get_first_day(expense.expense_date) != frappe.utils.get_first_day(self.month):
                frappe.throw(f"Expense row {expense.idx}: Expense Date must be in the settlement month.")

    def calculate_totals(self):
        total = sum(
            expense.amount or 0
            for expense in self.expenses
        )

        self.total_expenses = total
        self.remaining_balance = self.petty_cash_limit - total

        if self.total_expenses > self.petty_cash_limit:
            frappe.throw(
                "Total Expenses cannot exceed the Petty Cash Limit."
            )
    def create_whish_journal_entry(self):
        if frappe.session.user != "Administrator" and "LSA President" not in frappe.get_roles():
            frappe.throw("Only President may complete final approval and payment.", frappe.PermissionError)
        if self.payment_status == "Paid":
            frappe.throw(
                "This Petty Cash Settlement has already been paid."
            )

        if self.journal_entry:
            frappe.throw(
                "A Journal Entry is already linked to this settlement."
            )

        if self.payment_method != "Whish":
            frappe.throw(
                "Payment Method must be Whish."
            )

        self.payment_date = frappe.utils.today()
        self.db_set("payment_date", self.payment_date)

        whish_account = frappe.db.get_value(
            "Account",
            {
                "name": self.payment_account,
                "is_group": 0,
                "disabled": 0
            },
            ["name", "company", "account_currency"],
            as_dict=True
        )

        if not whish_account:
            frappe.throw(
                "The configured Payment Account could not be found or is disabled."
            )

        company = whish_account.company

        cost_center_company = frappe.db.get_value(
            "Cost Center",
            self.cost_center,
            "company"
        )

        if cost_center_company != company:
            frappe.throw(
                "The Cost Center and Whish account belong to different companies."
            )

        if not self.account:
            frappe.throw(
                "An Account must be selected during Finance Review."
            )

        account_company = frappe.db.get_value(
            "Account",
            self.account,
            "company"
        )

        if account_company != company:
            frappe.throw(
                f"Account {self.account} does not belong to Company {company}."
            )

        expense_account = frappe.get_cached_doc("Account", self.account)
        if expense_account.is_group or expense_account.disabled or expense_account.root_type != "Expense":
            frappe.throw("The Finance Account must be an enabled Expense ledger account.")

        company_currency = frappe.db.get_value("Company", company, "default_currency")
        if expense_account.account_currency != company_currency or whish_account.account_currency != company_currency:
            frappe.throw("Settlement accounts must use the company currency.")

        journal_entry = frappe.new_doc("Journal Entry")

        journal_entry.posting_date = self.payment_date
        journal_entry.company = company
        journal_entry.user_remark = (
            f"Petty Cash Settlement {self.name}"
        )

        journal_entry.append(
            "accounts",
            {
                "account": self.account,
                "debit_in_account_currency": self.total_expenses,
                "cost_center": self.cost_center,
            },
        )

        journal_entry.append(
            "accounts",
            {
                "account": whish_account.name,
                "credit_in_account_currency": self.total_expenses
            }
        )

        journal_entry.flags.ignore_permissions = True
        journal_entry.insert()
        journal_entry.submit()

        self.db_set("journal_entry", journal_entry.name)
        self.db_set("payment_status", "Paid")
        self.update_petty_cash_whish()

        return journal_entry.name

    def cancel_payment_artifacts(self):
        if self.journal_entry:
            journal_entry = frappe.get_doc("Journal Entry", self.journal_entry)
            if journal_entry.docstatus == 1:
                journal_entry.flags.ignore_permissions = True
                journal_entry.cancel()

        whish_name = frappe.db.get_value(
            "Petty Cash Whish Employee", {"settlement": self.name}, "parent"
        )
        if whish_name:
            whish = frappe.get_doc("Petty Cash Whish", whish_name)
            whish.set("employees", [row for row in whish.employees if row.settlement != self.name])
            whish.flags.ignore_permissions = True
            whish.save()
    def generate_pdf_report(self):
        existing = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": "Petty Cash Settlement",
                "attached_to_name": self.name,
                "file_name": f"{self.name}.pdf",
                "is_private": 1,
            },
            "name",
        )
        if existing:
            return existing

        html = self.build_pdf_html()

        pdf_content = get_pdf(html)

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{self.name}.pdf",
            "content": pdf_content,
            "is_private": 1,
            "attached_to_doctype": "Petty Cash Settlement",
            "attached_to_name": self.name,
        })

        file_doc.save(ignore_permissions=True)

        return file_doc.name

    def build_pdf_html(self):
        expense_rows = []

        for number, expense in enumerate(self.expenses, start=1):
            expense_rows.append(
                f"""
                <tr>
                    <td class="number">{number}</td>
                    <td>{escape_html(str(expense.expense_date or ""))}</td>
                    <td>{escape_html(expense.expense_item or "")}</td>
                    <td>{escape_html(expense.invoice_number or "")}</td>
                    <td>{escape_html(expense.supplier or "")}</td>
                    <td>{escape_html(expense.related_details or "")}</td>
                    <td class="amount">
                        {flt(expense.amount, 2):,.2f}
                    </td>
                </tr>
                """
            )

        return f"""
        <style>

            @page {{
                size: A4 landscape;
                margin: 0.6in;
            }}

            .report {{
                font-family: Calibri, Arial, sans-serif;
                font-size: 10pt;
                color: #000;
            }}

            .title {{
                text-align: center;
                font-size: 20pt;
                font-weight: bold;
                margin-bottom: 20px;
            }}

            .subtitle {{
                text-align: center;
                font-size: 10pt;
                margin-bottom: 20px;
            }}

            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}

            .info-table td {{
                border: 1px solid #000;
                padding: 6px;
            }}

            .info-label {{
                font-weight: bold;
                background: #d9eaf7;
                width: 16%;
            }}

            .expense-table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
            }}

            .expense-table th,
            .expense-table td {{
                border: 1px solid #000;
                padding: 4px;
                vertical-align: middle;
            }}

            .expense-table th {{
                background: #9dc3e6;
                font-weight: bold;
                text-align: center;
                font-size: 9pt;
            }}

            .expense-table td {{
                font-size: 9pt;
            }}

            .number {{
                width: 4%;
                text-align: center;
            }}

            .date {{
                width: 9%;
            }}

            .item {{
                width: 17%;
            }}

            .invoice {{
                width: 11%;
            }}

            .supplier {{
                width: 14%;
            }}

            .details {{
                width: 29%;
            }}

            .amount {{
                width: 16%;
                text-align: right;
            }}

            .totals-table {{
                width: 40%;
                margin-left: auto;
                margin-top: 20px;
                border-collapse: collapse;
            }}

            .totals-table td {{
                border: 1px solid #000;
                padding: 6px;
            }}

            .total-label {{
                font-weight: bold;
                background: #d9eaf7;
            }}

            .footer {{
                margin-top: 30px;
                font-size: 9pt;
            }}

        </style>

        <div class="report">

            <div class="title">
                PETTY CASH SETTLEMENT REPORT
            </div>

            <div class="subtitle">
                Settlement: {escape_html(self.name)}
            </div>

            <table class="info-table">

                <tr>
                    <td class="info-label">Center Officer</td>
                    <td>{escape_html(self.center_officer or "")}</td>

                    <td class="info-label">Month</td>
                    <td>{formatdate(self.month) if self.month else ""}</td>
                </tr>

                <tr>
                    <td class="info-label">Cost Center</td>
                    <td>{escape_html(self.cost_center or "")}</td>

                    <td class="info-label">Petty Cash Account</td>
                    <td>{escape_html(self.petty_cash_account or "")}</td>
                </tr>

                <tr>
                    <td class="info-label">Petty Cash Limit</td>
                    <td>{flt(self.petty_cash_limit, 2):,.2f}</td>

                    <td class="info-label">Payment Method</td>
                    <td>{escape_html(self.payment_method or "")}</td>
                </tr>

                <tr>
                    <td class="info-label">Payment Date</td>
                    <td>{formatdate(self.payment_date) if self.payment_date else ""}</td>

                    <td class="info-label">Payment Status</td>
                    <td>{escape_html(self.payment_status or "")}</td>
                </tr>

            </table>

            <table class="expense-table">

                <thead>
                    <tr>
                        <th class="number">No.</th>
                        <th class="date">Date</th>
                        <th class="item">Expense Item</th>
                        <th class="invoice">Invoice No.</th>
                        <th class="supplier">Supplier</th>
                        <th class="details">Related Details</th>
                        <th class="amount">Amount</th>
                    </tr>
                </thead>

                <tbody>
                    {"".join(expense_rows)}
                </tbody>

            </table>

            <table class="totals-table">

                <tr>
                    <td class="total-label">Petty Cash Limit</td>
                    <td class="amount">
                        {flt(self.petty_cash_limit, 2):,.2f}
                    </td>
                </tr>

                <tr>
                    <td class="total-label">Total Expenses</td>
                    <td class="amount">
                        {flt(self.total_expenses, 2):,.2f}
                    </td>
                </tr>

                <tr>
                    <td class="total-label">Remaining Balance</td>
                    <td class="amount">
                        {flt(self.remaining_balance, 2):,.2f}
                    </td>
                </tr>

            </table>

            <div class="footer">

                <p>
                    <strong>Journal Entry:</strong>
                    {escape_html(self.journal_entry or "")}
                </p>

                <p>
                    <strong>Payment Status:</strong>
                    {escape_html(self.payment_status or "")}
                </p>

                <p>
                    This report was generated automatically by the
                    Center Expense Management system.
                </p>

            </div>

        </div>
        """
    def send_pdf_report_by_email(self, file_name):
        if not self.report_email:
            frappe.throw(
                _("Report Email is required before completing the settlement.")
            )

        file_doc = frappe.get_doc("File", file_name)

        frappe.sendmail(
            recipients=[self.report_email],
            subject=f"Petty Cash Settlement Report - {self.name}",
            message=f"""
                <p>Dear Recipient,</p>

                <p>
                    Please find attached the Petty Cash Settlement Report
                    for settlement <strong>{self.name}</strong>.
                </p>

                <p>
                    This email was automatically generated by the
                    Center Expense Management system.
                </p>
            """,
            attachments=[
                {
                    "fname": file_doc.file_name,
                    "fcontent": file_doc.get_content(),
                }
            ],
        )
    @frappe.whitelist()
    def add_return_comment(self, reason, action):
        allowed_actions = {
            "Return to Center Officer": ("Pending Accountant Review", "LSA Accountant"),
            "Return to Accountant": ("Pending Finance Review", "LSA Finance Approver"),
            "Return to Finance": ("Pending Operations Approval", "LSA Operations Manager"),
            "Return to Operations": ("Pending Director Approval", "LSA Executive Director"),
            "Return to Director": ("Pending Treasurer Approval", "LSA Board Treasurer"),
            "Return to Treasurer": ("Pending President Approval", "LSA President"),
        }
        if action not in allowed_actions:
            frappe.throw("Invalid return action.")

        expected_state, required_role = allowed_actions[action]
        if self.workflow_state != expected_state or required_role not in frappe.get_roles():
            frappe.throw("You cannot perform this return action.", frappe.PermissionError)

        if not reason or not reason.strip():
            frappe.throw("A return reason is required.")

        self.add_comment(
            "Comment",
            text=(
                f"<b>Settlement Returned</b><br>"
                f"Action: {escape_html(action)}<br>"
                f"Reason: {escape_html(reason.strip())}"
            )
        )
