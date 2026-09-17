# Center Expense Management

A Frappe application for managing **center petty cash expenses, monthly petty cash settlements, and Whish payment records**.

The application allows Center Officers to record their monthly expenses, automatically calculate petty cash balances, and submit settlements through a controlled multi-stage approval workflow.

After the required reviews and approvals, the Treasurer processes the payment through **Whish**. The application automatically creates the corresponding ERPNext Journal Entry, marks the settlement as paid, generates a **PDF Petty Cash Settlement Report**, attaches the report to the settlement, and sends the report by email.

The application also maintains a monthly **Petty Cash Whish** record. A new monthly Petty Cash Whish document is automatically created by the Frappe scheduler, and completed petty cash settlements can automatically add the corresponding Center Officer and payment amount to the appropriate monthly Whish record.

---

## Features

* Petty Cash Configuration for each Center Officer
* Center Officer linked to an ERPNext **Employee**
* Monthly Petty Cash Settlement
* Expense tracking with:

  * Expense Item
  * Expense Date
  * Invoice Number
  * Supplier
  * Related Details
  * Amount
  * Invoice/Receipt Attachment
* Automatic loading of:

  * Cost Center
  * Petty Cash Account
  * Petty Cash Limit
* Finance account selection during Finance Review
* Finance-only account lookup with company and expense-account restrictions
* Automatic calculation of:

  * Total Expenses
  * Remaining Balance
* Validation of expense amounts and required information
* Prevention of duplicate monthly settlements for the same Center Officer
* Mandatory receipt for every expense
* Server-side validation to prevent expenses exceeding the petty cash limit
* Server-side validation requiring Finance to select an Account before approving the settlement
* Multi-stage settlement approval workflow
* Accountant Review
* Finance Review
* Operations Approval
* Treasurer Processing
* Accountant return-to-Center-Officer capability
* Finance return-to-Accountant capability
* Operations return-to-Finance capability
* Return reason captured in the Frappe Timeline
* Whish payment processing
* Automatic Journal Entry creation when the Treasurer completes the settlement
* Automatic linking of the Journal Entry to the settlement
* Automatic payment status update to `Paid`
* Automatic PDF settlement report generation
* Automatic attachment of the PDF report to the settlement
* Prevention of duplicate payment processing
* Prevention of duplicate Journal Entry creation
* Automatic email delivery of the generated PDF report
* Automatic monthly Petty Cash Whish creation
* Automatic `PCW-MM-YYYY` naming for monthly Petty Cash Whish records
* Automatic addition of completed settlement information to the corresponding monthly Petty Cash Whish
* Duplicate protection for Petty Cash Whish employee entries

---

# DocTypes

## Petty Cash Configuration

Stores the petty cash configuration for each Center Officer.

Each configuration contains:

* Center Officer
* Cost Center
* Petty Cash Account
* Petty Cash Limit

The Center Officer is linked to an **Employee**.

The configuration determines the petty cash limit and accounting information automatically loaded when the Center Officer creates a monthly settlement.

---

## Petty Cash Account Allocation

The **Petty Cash Account Allocation** DocType is retained for configuration and account-related functionality where applicable.

Each allocation contains:

* Account
* Amount

The application uses the appropriate ERPNext accounting Account selected during Finance Review.

> The settlement's available Account balance is obtained from the ERPNext Account balance when using the account-balance functionality.

---

## Petty Cash Expense

Child table used to record individual expenses within a Petty Cash Settlement.

Each expense contains:

* Expense Item
* Expense Date
* Invoice Number
* Supplier
* Related Details
* Amount
* Receipt

The Expense Account is **not stored on individual expense rows**. Accounting account selection is handled at the settlement level during Finance Review.

The following expense information is required:

* Expense Item
* Expense Date
* Invoice Number
* Supplier
* Amount
* Receipt

Related Details is optional and can be used to provide additional information about an expense.

---

## Petty Cash Settlement

The main document used to create, review, approve, and process a Center Officer's monthly petty cash settlement.

It contains:

* Center Officer
* Month
* Cost Center
* Petty Cash Account
* Petty Cash Limit
* Total Expenses
* Remaining Balance
* Expenses
* Account
* Amount
* Payment Method
* Payment Date
* Journal Entry
* Payment Status
* Report Email

The **Center Officer** field is a Link to the ERPNext **Employee** DocType.

The **Account** and **Amount** fields are settlement-level fields.

The Account is selected during **Finance Review**.

The Account must be an enabled expense ledger in the settlement company. The Amount mirrors the
validated settlement total and is read-only. Account balances are not persisted on settlements.

The settlement also receives an automatically generated PDF report after successful Treasurer processing.

## Production prerequisites

* ERPNext must be installed before this app.
* Every Center Officer User must be linked through `Employee.user_id`.
* Each Center Officer must have exactly one Petty Cash Configuration.
* Configuration accounts and Cost Center must belong to the same company.
* `Payment Account` must be an enabled Asset ledger using the company currency; this is the
  Whish wallet or clearing account credited by the generated Journal Entry.
* Receipts must be uploaded as private File records.

Install and migrate on staging first. The integrity migration intentionally stops when it finds
duplicate configurations, monthly Whish documents, or active monthly settlements, so those records
can be reviewed instead of being silently discarded.

---

## Petty Cash Whish

The **Petty Cash Whish** DocType stores the monthly Whish payment information.

Each document represents one month.

It contains:

* Month and Year
* Employees

The **Month and Year** field is stored as a Date representing the first day of the month.

For example:

```text
2026-09-01
```

represents September 2026.

### Petty Cash Whish Naming

Monthly Petty Cash Whish documents use the following naming format:

```text
PCW-MM-YYYY
```

Examples:

```text
PCW-09-2026
PCW-10-2026
PCW-11-2026
```

The document name is generated automatically from the Month and Year value.

---

## Petty Cash Whish Employee

Child table used inside **Petty Cash Whish**.

Each row contains:

* Name
* Phone Number
* Whish ID
* Salary Received (NET)
* Currency

When a completed Petty Cash Settlement is added to a monthly Petty Cash Whish:

| Field                 | Source                                 |
| --------------------- | -------------------------------------- |
| Name                  | Center Officer's Employee name         |
| Phone Number          | Blank / `null`                         |
| Whish ID              | Blank / `null`                         |
| Salary Received (NET) | Petty Cash Settlement `Total Expenses` |
| Currency              | Blank / `null`                         |

The current implementation does not require Phone Number or Whish ID fields to exist on the Employee record.

No Salary Slip lookup is performed.

The **Salary Received (NET)** value is specifically the settlement's `total_expenses`.

---

# Workflow

The Petty Cash Settlement follows a multi-stage approval workflow:

```text
Draft
  │
  │ Submit for Accountant Review
  ▼
Pending Accountant Review
  │
  │ Approve
  ▼
Pending Finance Review
  │
  │ Approve
  ▼
Pending Operations Approval
  │
  │ Approve
  ▼
Pending Treasurer Processing
  │
  │ Complete
  ▼
Completed
```

## Workflow Roles

| Stage                | Role           |
| -------------------- | -------------- |
| Draft / Submission   | Center Officer |
| Accountant Review    | Accountant     |
| Finance Review       | Finance        |
| Operations Approval  | Operations     |
| Treasurer Processing | Treasurer      |

---

# Finance Review

During **Pending Finance Review**, the Finance user must select an accounting Account before approving the settlement.

The Account field is editable during Finance Review and read-only during the other workflow stages.

The Amount field is read-only.

When Finance selects an Account, the application retrieves the available balance associated with that ERPNext Account.

The application also verifies that the selected Account is a valid ledger account and not an Account Group.

The server-side validation prevents Finance from approving the settlement without selecting an Account.

```text
Pending Finance Review
        │
        ├── Account not selected
        │       ↓
        │   Cannot Approve
        │
        └── Account selected
                ↓
        Pending Operations Approval
```

This requirement is enforced on the server and does not rely solely on client-side JavaScript.

---

# Workflow Return Paths

The workflow allows corrections to be requested at different review stages.

## Accountant → Center Officer

```text
Pending Accountant Review
        │
        │ Return to Center Officer
        ▼
      Draft
```

## Finance → Accountant

```text
Pending Finance Review
        │
        │ Return to Accountant
        ▼
Pending Accountant Review
```

## Operations → Finance

```text
Pending Operations Approval
        │
        │ Return to Finance
        ▼
Pending Finance Review
```

This provides a controlled review chain where each department can return the settlement to the appropriate preceding stage.

---

# Return Reasons

When a settlement is returned, the application displays a popup requesting a **Reason for Return**.

The reason is required.

The return actions are:

```text
Return to Center Officer
Return to Accountant
Return to Finance
```

The return reason is stored in the Frappe **Timeline** as a comment.

The comment contains:

* Return action
* Return reason

Example:

```text
Settlement Returned
Action: Return to Accountant
Reason: Please verify the supporting invoice.
```

The return reason is not stored as a permanent field on the Petty Cash Settlement DocType.

---

# Accounting / Whish Payment

The Treasurer processes approved settlements using **Whish**.

The application automatically creates a Journal Entry when the settlement moves from:

```text
Pending Treasurer Processing
        ↓
Completed
```

The settlement contains one accounting Account selected during Finance Review.

The accounting entry uses the settlement's selected Account and the **actual settlement expense total**.

Conceptually:

```text
Debit  → Selected Settlement Account
Credit → Whish - OS
```

For example, if the settlement contains total expenses of 100:

```text
Dr  Selected Account - OS       100
Cr  Whish - OS                  100
```

The selected Account is stored on the **Petty Cash Settlement**, rather than on each individual expense row.

The Journal Entry:

* Uses the settlement Payment Date as the posting date.
* Uses the same company as the Whish account.
* Debits the selected settlement Account.
* Uses the settlement Cost Center for the debit entry.
* Credits the `Whish - OS` account with the total settlement amount.
* Is automatically submitted.
* Is automatically linked to the Petty Cash Settlement.
* Changes the settlement Payment Status to `Paid`.

The application validates that the Whish account, selected Account, and Cost Center belong to the appropriate company.

---

## Payment Protection

The application prevents:

* Paying the same settlement more than once.
* Creating multiple Journal Entries for the same settlement.
* Using a missing Whish account.
* Using an invalid or disabled accounting account.
* Using a Cost Center belonging to a different company from the Whish account.
* Completing the Finance Review without selecting an Account.

The application also prevents a settlement from being processed again if it already has a Journal Entry or has already been marked as `Paid`.

---

# Automatic Monthly Petty Cash Whish

The application automatically creates a new **Petty Cash Whish** document for each month.

This is implemented using a Frappe scheduler event.

The scheduler runs the following function:

```text
center_expense_management.tasks.create_monthly_petty_cash_whish
```

The function:

1. Determines the current month.
2. Converts the current date to the first day of the month.
3. Checks whether a Petty Cash Whish already exists for that month.
4. Creates the document if it does not exist.
5. Does nothing if the monthly document already exists.

For example:

```text
Current date:
2026-09-16

Month:
2026-09-01

Generated document:
PCW-09-2026
```

When the month changes:

```text
October 2026
        ↓
PCW-10-2026
```

The scheduler therefore does not require manual creation of monthly Whish documents.

---

## Monthly Whish Duplicate Protection

The scheduler checks:

```python
frappe.db.exists(
    "Petty Cash Whish",
    {
        "month_and_year": month
    }
)
```

before creating a document.

Therefore, if the scheduler executes multiple times during the same month, it will not create duplicate monthly Petty Cash Whish documents.

The function has also been tested manually through the Frappe console and confirmed to return a single monthly document when executed repeatedly.

---

# Automatic Petty Cash Whish Employee Update

After a successful Whish payment, the application updates the corresponding monthly **Petty Cash Whish**.

The payment date determines which monthly Whish document is used.

For example:

```text
Payment Date:
2026-09-16

Matching Petty Cash Whish:
PCW-09-2026
```

The application then retrieves the Employee linked to the settlement's **Center Officer**.

A row is added to the monthly Whish employee table.

Example:

```text
Name:
John Doe

Phone Number:
blank

Whish ID:
blank

Salary Received (NET):
100

Currency:
blank
```

The `Salary Received (NET)` value is taken directly from:

```text
Petty Cash Settlement → Total Expenses
```

No Salary Slip or payroll calculation is performed.

---

## Petty Cash Whish Employee Duplicate Protection

Before adding an Employee to the monthly Petty Cash Whish, the application checks whether that Employee already exists in the table.

If the Employee is already present, another row is not created.

This protects the monthly Whish record from duplicate employee rows if the payment/update process is triggered again.

---

## Missing Monthly Whish Protection

When a settlement is completed, the application searches for a Petty Cash Whish whose:

```text
Month and Year
```

matches the settlement's:

```text
Payment Date
```

For example:

```text
Payment Date = 2026-09-16
        ↓
Expected Month and Year = 2026-09-01
        ↓
Expected Whish = PCW-09-2026
```

If the corresponding monthly Petty Cash Whish does not exist, the application reports the problem instead of silently losing the Whish payment record.

---

# PDF Settlement Report

When the Treasurer successfully completes a settlement, the application automatically generates a **Petty Cash Settlement Report PDF**.

The PDF is generated after successful payment processing.

The generated report is automatically attached to the **Petty Cash Settlement** as a private Frappe File.

The report is also sent to the configured **Report Email** address.

---

## PDF Report Contents

The report includes:

* Report title
* Settlement number
* Center Officer
* Month
* Cost Center
* Petty Cash Account
* Petty Cash Limit
* Payment Method
* Payment Date
* Payment Status
* Detailed expense table
* Expense Date
* Expense Item
* Invoice Number
* Supplier
* Related Details
* Expense Amount
* Total Expenses
* Remaining Balance
* Journal Entry number
* Payment Status
* System-generated report footer

The expense table contains one row for each expense recorded in the settlement.

---

## PDF Layout

The report is generated in **A4 landscape format** and uses a structured table-based layout with:

* Centered report title
* Settlement information section
* Expense details table
* Highlighted table headers
* Totals section
* Payment and Journal Entry information
* System-generated footer

The PDF is stored as a private file and attached directly to the corresponding settlement.

---

## PDF Generation and Email Flow

```text
Treasurer clicks Complete
        │
        ▼
Validate Whish Payment
        │
        ▼
Create Journal Entry
        │
        ▼
Submit Journal Entry
        │
        ▼
Update Payment Information
        │
        ▼
Update Monthly Petty Cash Whish
        │
        ▼
Generate PDF Report
        │
        ▼
Attach PDF to Settlement
        │
        ▼
Send PDF by Email
        │
        ▼
Settlement = Completed
```

The Treasurer does not need to manually create or attach the report.

---

# User Guide

## 1. Configure Petty Cash

Before creating settlements, a system administrator should create a **Petty Cash Configuration** for each Center Officer.

Go to:

```text
Petty Cash Configuration → New
```

Enter:

* **Center Officer** – Select the Employee who will manage the petty cash.
* **Cost Center** – Select the Cost Center associated with the Employee.
* **Petty Cash Account** – Select the account used for petty cash.
* **Petty Cash Limit** – Enter the maximum amount available to the Center Officer.

Save the configuration.

The configuration is automatically used when the Center Officer creates a Petty Cash Settlement.

---

## 2. Create a Monthly Petty Cash Settlement

The Center Officer creates one settlement for each month.

Go to:

```text
Petty Cash Settlement → New
```

Select:

* **Center Officer**
* **Month**

The following fields are automatically populated from the Center Officer's Petty Cash Configuration:

* Cost Center
* Petty Cash Account
* Petty Cash Limit

The Center Officer must then add each expense separately in the **Expenses** table.

The Center Officer does not select an accounting Account for individual expenses.

---

## 3. Add Expenses

Each expense should be entered as a separate row.

Complete the expense information:

| Field           | Description                              |
| --------------- | ---------------------------------------- |
| Expense Item    | Description or category of the expense   |
| Expense Date    | Date the expense occurred                |
| Invoice Number  | Invoice or receipt number                |
| Supplier        | Supplier associated with the expense     |
| Related Details | Additional information about the expense |
| Amount          | Amount paid                              |
| Receipt         | Invoice or receipt attachment            |

A receipt must be attached to every expense.

Invoice Number and Supplier are required.

Related Details is optional.

The application automatically calculates:

```text
Total Expenses
Remaining Balance
```

The Center Officer cannot submit the settlement if the total expenses exceed the configured Petty Cash Limit.

---

## 4. Submit the Settlement

After entering all expenses and attaching the required receipts, the Center Officer submits the settlement for review.

The workflow moves the settlement to:

```text
Pending Accountant Review
```

A Center Officer cannot create more than one settlement for the same month.

---

## 5. Accountant Review

The Accountant reviews the submitted settlement.

The Accountant should verify:

* Expense details
* Expense amounts
* Receipts/invoices
* Cost Center
* Petty Cash Account
* Total Expenses
* Petty Cash Limit

If everything is correct, the Accountant approves the settlement.

The workflow moves to:

```text
Pending Finance Review
```

If corrections are required, the Accountant can return the settlement to the Center Officer and provide a return reason.

---

## 6. Finance Review

The Finance user performs the financial review after Accountant approval.

The Finance user should verify:

* Expense amounts
* Receipts/invoices
* Cost Center
* Petty Cash Account
* Petty Cash Limit
* Total Expenses
* Accounting correctness of the settlement

During this stage, Finance selects the appropriate **Account**.

The Account field is available for editing during:

```text
Pending Finance Review
```

After selecting an Account, the application retrieves the available balance for the selected ERPNext Account.

The Amount field is read-only.

The Finance user must select an Account before approving the settlement.

If Finance attempts to approve without selecting an Account, the server rejects the workflow transition.

If everything is correct, Finance approves the settlement.

The workflow moves to:

```text
Pending Operations Approval
```

If corrections are required, Finance can return the settlement to the Accountant and provide a return reason.

---

## 7. Operations Approval

The Operations user performs the operational review after Finance approval.

The Operations user should verify that:

* The expenses are appropriate.
* Required supporting documents are attached.
* The settlement information is complete.
* The selected Account is appropriate.
* The total amount is within the applicable petty cash limits.

If approved, the workflow moves to:

```text
Pending Treasurer Processing
```

If corrections are required, Operations can return the settlement to Finance and provide a return reason.

---

## 8. Treasurer Processing

The Treasurer performs the final payment and accounting step.

The Treasurer should:

1. Open the settlement in **Pending Treasurer Processing**.
2. Verify the expenses and total amount.
3. Verify that the Account has been selected.
4. Select:

   * **Payment Method:** `Whish`
   * **Payment Date:** Date on which the payment is processed.
5. Click **Complete**.

When the Treasurer completes the workflow, the application automatically:

1. Validates the Whish account.
2. Validates the Cost Center and company.
3. Validates the selected Account and accounting company.
4. Creates a Journal Entry.
5. Creates the debit entry using the selected settlement Account.
6. Applies the settlement Cost Center to the debit entry.
7. Credits `Whish - OS` with the total settlement amount.
8. Submits the Journal Entry.
9. Stores the Journal Entry number in the settlement.
10. Updates the payment status to `Paid`.
11. Finds the Petty Cash Whish corresponding to the Payment Date.
12. Adds the Center Officer to the monthly Whish employee table.
13. Sets Salary Received (NET) to the settlement Total Expenses.
14. Generates the Petty Cash Settlement PDF.
15. Attaches the PDF to the settlement.
16. Sends the PDF report to the configured Report Email address.

The settlement then reaches:

```text
Completed
```

No manual Journal Entry creation or PDF generation is required from the Treasurer.

---

# Payment Fields

The settlement contains the following payment-related fields:

| Field          | Description                                                             |
| -------------- | ----------------------------------------------------------------------- |
| Payment Method | Payment method used for the settlement. Currently `Whish`.              |
| Payment Date   | Date used for the payment and Journal Entry.                            |
| Journal Entry  | Automatically populated with the Journal Entry created for the payment. |
| Payment Status | Shows whether the settlement has been paid.                             |

The normal payment status is:

```text
Unpaid
```

After successful Treasurer processing:

```text
Paid
```

---

# Monthly Settlement Rules

The application enforces several rules to maintain data integrity:

* Each Center Officer can have only one settlement for a given month.
* Center Officer is linked to an Employee.
* At least one expense is required.
* Expense amounts must be greater than zero.
* Invoice Number is required for every expense.
* Supplier is required for every expense.
* A receipt is required for every expense.
* Related Details is optional.
* Total Expenses cannot exceed the configured Petty Cash Limit.
* Cost Center is automatically loaded from the Center Officer's configuration.
* Petty Cash Account is automatically loaded from the Center Officer's configuration.
* Petty Cash Limit is automatically loaded from the Center Officer's configuration.
* Finance must select an Account before approving the Finance Review stage.
* The selected Account must be a valid ledger Account.
* The settlement Amount is automatically populated from the selected Account balance.
* The settlement Amount is read-only.
* The Whish account must exist and be enabled.
* The Whish account must belong to the appropriate company.
* The Cost Center must belong to the same company as the Whish account.
* A settlement cannot be paid twice.
* A settlement cannot create multiple Journal Entries for the same payment.
* A settlement generates its PDF report after successful payment processing.
* The generated PDF is stored as a private attachment.
* The generated PDF is emailed to the configured Report Email address.
* A monthly Petty Cash Whish is automatically created for each month.
* Monthly Petty Cash Whish records use the `PCW-MM-YYYY` naming format.
* The monthly Petty Cash Whish is determined using the settlement Payment Date.
* A Center Officer is not added twice to the same monthly Petty Cash Whish.
* Salary Received (NET) in the Whish table equals the settlement Total Expenses.
* Phone Number, Whish ID, and Currency remain blank when no source value is available.

---

# Validation

Validation is performed at the application/server level to protect the data even if client-side validation is bypassed.

The settlement validates:

```text
Center Officer + Month
        ↓
Petty Cash Configuration
        ↓
Expenses
        ↓
Required Expense Information
        ↓
Receipts
        ↓
Total Expenses
        ↓
Petty Cash Limit
        ↓
Finance Account Selection
        ↓
Account Validation
        ↓
Whish Payment
        ↓
Journal Entry
        ↓
Monthly Petty Cash Whish Update
```

## Finance Account Validation

The Finance Account requirement is enforced based on the workflow transition.

The validation specifically detects the transition:

```text
Pending Finance Review
        ↓
Pending Operations Approval
```

If the Account is empty, the transition is rejected:

```text
Finance must select an Account before approving the settlement.
```

This validation is performed on the server and is not dependent solely on browser-side scripts.

---

## Petty Cash Limit Validation

If the total expenses exceed the configured petty cash limit, the settlement is rejected:

```text
Total Expenses cannot exceed the Petty Cash Limit.
```

This validation is performed on the server and is not dependent solely on browser-side scripts.

---

# Automatic Monthly Scheduler

The application uses Frappe's scheduler to create the monthly Petty Cash Whish.

The scheduler configuration is located in:

```text
center_expense_management/hooks.py
```

The relevant configuration is:

```python
scheduler_events = {
    "daily": [
        "center_expense_management.tasks.create_monthly_petty_cash_whish"
    ]
}
```

The scheduler function is located in:

```text
center_expense_management/tasks.py
```

The function:

```text
create_monthly_petty_cash_whish
```

checks for the current month's document before creating one.

The function can also be executed manually for testing:

```bash
bench --site $SITE_NAME execute center_expense_management.tasks.create_monthly_petty_cash_whish
```

---

# Installation

The application is intended for **Frappe Framework v16**.

Install the app using the Frappe `bench` CLI:

```bash
cd $PATH_TO_YOUR_BENCH

bench get-app https://github.com/Ibrahim-abdulwahab/petty_cash_management.git --branch version-16

bench --site $SITE_NAME install-app center_expense_management
```

After installation, migrate the site:

```bash
bench --site $SITE_NAME migrate
```

Clear the cache if necessary:

```bash
bench --site $SITE_NAME clear-cache
```

Restart the bench when required:

```bash
bench restart
```

---

# Configuration

After installing the application:

1. Create or verify the required user roles:

   * Center Officer
   * Accountant
   * Finance
   * Operations
   * Treasurer

2. Create a **Petty Cash Configuration** for each Center Officer.

3. Configure the appropriate:

   * Cost Center
   * Petty Cash Account
   * Petty Cash Limit

4. Ensure the required accounting Accounts exist and belong to the correct company.

5. Ensure the Whish account exists and is enabled:

```text
Whish - OS
```

6. Ensure the **Petty Cash Settlement Workflow** is installed and active.

7. Ensure the users responsible for each workflow stage have the appropriate roles and permissions.

8. Ensure the Frappe scheduler is running so monthly Petty Cash Whish documents can be created automatically.

---

# Development

Enable developer mode on the development site:

```bash
bench set-config -g developer_mode 1
```

After making changes to application code or DocTypes, migrate the site:

```bash
bench --site $SITE_NAME migrate
```

Clear the cache:

```bash
bench --site $SITE_NAME clear-cache
```

If application assets have been changed, build the application:

```bash
bench build --app center_expense_management
```

Restart the bench when required:

```bash
bench restart
```

---

## Exporting Fixtures

When DocType or workflow configuration is changed through the Frappe interface, export the changes into the application's fixture files:

```bash
bench --site $SITE_NAME export-fixtures
```

After exporting fixtures, inspect the changes before committing:

```bash
cd apps/center_expense_management

git status
git diff
```

`export-fixtures` updates configuration fixture files. It does not modify the application's Python or JavaScript source code.

---

## Python Syntax Checks

The main settlement controller can be checked with:

```bash
python3 -m py_compile center_expense_management/center_expense_management/doctype/petty_cash_settlement/petty_cash_settlement.py
```

The monthly scheduler can be checked with:

```bash
python3 -m py_compile center_expense_management/tasks.py
```

The application hooks can be checked with:

```bash
python3 -m py_compile center_expense_management/hooks.py
```

No output indicates that the Python file passed the syntax check.

---

## JavaScript Syntax Check

The Petty Cash Settlement JavaScript file can be checked with:

```bash
node --check center_expense_management/center_expense_management/doctype/petty_cash_settlement/petty_cash_settlement.js
```

No output indicates that the JavaScript file passed the syntax check.

---

# Testing the Monthly Petty Cash Whish

The monthly Whish creation function can be tested from the Frappe console:

```bash
bench --site $SITE_NAME console
```

Then:

```python
from center_expense_management.tasks import create_monthly_petty_cash_whish

create_monthly_petty_cash_whish()
```

Verify the current month's document:

```python
frappe.db.get_value(
    "Petty Cash Whish",
    {
        "month_and_year": frappe.utils.get_first_day(
            frappe.utils.today()
        )
    },
    ["name", "month_and_year"],
    as_dict=True
)
```

Running the function multiple times should not create duplicates.

The monthly count can be checked with:

```python
frappe.db.count(
    "Petty Cash Whish",
    {
        "month_and_year": frappe.utils.get_first_day(
            frappe.utils.today()
        )
    }
)
```

The expected result is:

```text
1
```

---

# GitHub Repository

The project is maintained in the following GitHub repository:

```text
https://github.com/Ibrahim-abdulwahab/petty_cash_management
```

The main development branch is:

```text
version-16
```

The Frappe application contained in the repository is:

```text
center_expense_management
```

The Petty Cash Settlement workflow is stored as an application fixture:

```text
center_expense_management/fixtures/workflow.json
```

This ensures that the workflow configuration, including the Finance Review stage, can be tracked in Git and included when the application is deployed or installed on another Frappe site.

---

# Git Workflow

After making changes:

```bash
cd /home/frappe/frappe-bench/apps/center_expense_management
```

Check the changes:

```bash
git status
```

Review them:

```bash
git diff
```

Add the changes:

```bash
git add .
```

Commit:

```bash
git commit -m "Describe your changes"
```

Push to the development branch:

```bash
git push origin version-16
```

If the remote branch contains changes that are intentionally being replaced by the local branch, a force push can be used carefully:

```bash
git push origin version-16 --force-with-lease
```

`--force-with-lease` is preferred over `--force` because it helps prevent accidentally overwriting changes that were pushed to the remote branch by someone else.

---

# Project Structure

The main application structure is:

```text
center_expense_management/
│
├── center_expense_management/
│   ├── center_expense_management/
│   │   └── doctype/
│   │       ├── petty_cash_configuration/
│   │       ├── petty_cash_account_allocation/
│   │       ├── petty_cash_expense/
│   │       ├── petty_cash_settlement/
│   │       ├── petty_cash_whish/
│   │       └── petty_cash_whish_employee/
│   │
│   ├── fixtures/
│   │   └── workflow.json
│   │
│   ├── hooks.py
│   ├── tasks.py
│   └── modules.txt
│
├── README.md
├── license.txt
├── pyproject.toml
└── requirements.txt
```

---

# Main Application Responsibilities

The main Petty Cash Settlement controller is responsible for:

* Loading petty cash configuration
* Validating the Center Officer and month
* Working with Employee-linked Center Officers
* Validating expenses
* Calculating totals
* Enforcing the petty cash limit
* Loading and validating the selected ERPNext Account
* Loading the available Account balance
* Validating the Finance Account workflow transition
* Creating the Whish Journal Entry
* Validating accounting company consistency
* Linking the Journal Entry to the settlement
* Updating the payment status
* Updating the corresponding monthly Petty Cash Whish
* Preventing duplicate Whish employee entries
* Generating the PDF settlement report
* Attaching the PDF report to the settlement
* Sending the PDF report by email
* Recording return reasons in the Frappe Timeline

The monthly scheduler is responsible for:

* Determining the current month
* Checking whether a Petty Cash Whish already exists
* Creating the monthly Petty Cash Whish when necessary
* Using the `PCW-MM-YYYY` naming format
* Preventing duplicate monthly Petty Cash Whish records

---

# Complete End-to-End Process

The overall system flow is:

```text
Center Officer / Employee
        │
        ▼
Create Monthly Petty Cash Settlement
        │
        ▼
Add Expenses + Receipts
        │
        ▼
Submit for Accountant Review
        │
        ▼
Accountant Review
        │
        ├── Return + Reason
        │
        ▼
Finance Review
        │
        ├── Select Account
        │
        ├── Account Balance Loaded
        │
        ├── Return + Reason
        │
        ▼
Operations Approval
        │
        ├── Return + Reason
        │
        ▼
Treasurer Processing
        │
        ▼
Whish Payment
        │
        ▼
Create + Submit Journal Entry
        │
        ▼
Mark Settlement Paid
        │
        ▼
Find Monthly Petty Cash Whish
        │
        ▼
Add Center Officer + Total Expenses
        │
        ▼
Generate PDF
        │
        ▼
Attach PDF
        │
        ▼
Email PDF
        │
        ▼
Completed
```

Separately, the daily Frappe scheduler maintains the monthly Whish documents:

```text
Frappe Scheduler
       │
       ▼
Check Current Month
       │
       ▼
Does PCW-MM-YYYY Exist?
       │
       ├── Yes → Do Nothing
       │
       └── No
            │
            ▼
       Create Monthly PCW
```

---

# Contributing

This app uses `pre-commit` for code formatting and linting.

Install and enable pre-commit:

```bash
cd apps/center_expense_management
pre-commit install
```

Pre-commit is configured to use:

* Ruff
* ESLint
* Prettier
* PyUpgrade

Before committing changes, check the repository:

```bash
git status
```

Then:

```bash
git add .
git commit -m "Describe your changes"
git push origin version-16
```

---

# License

MIT
