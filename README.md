# Center Expense Management

ERPNext/Frappe application for monthly petty-cash requests, approval, Whish payment exports,
and accounting entries.

## Workflow

```text
Center Officer
  -> Accountant
  -> Finance
  -> Operations
  -> Director
  -> Treasurer
  -> President
  -> Completed / automatic payment processing
```

Return paths are available at every review stage:

```text
Accountant -> Center Officer
Finance    -> Accountant
Operations -> Finance
Director   -> Operations
Treasurer  -> Director
President  -> Treasurer
```

Self-approval is disabled after the Center Officer's initial submission.

## Monthly process

1. On the configured reminder day (21 by default), the scheduler emails every configured active
   Center Officer who has not created a settlement for the current month.
2. Finance or System Manager can use **Petty Cash Settings > Send Reminders Now** to run the same
   reminder manually.
3. The Center Officer records expenses and uploads a private scanned invoice/receipt for every row.
4. Accountant reviews the request.
5. Finance selects the expense account and assigns a Cost Center to every expense row.
6. Operations, Director, Treasurer, and President approve in sequence.
7. President's final approval submits the settlement and automatically creates the Journal Entry.
8. The settlement is added to the monthly Petty Cash Whish document.
9. Background jobs generate/email the private settlement PDF and current monthly Whish Excel file.

## Configuration

### Petty Cash Settings

This singleton contains:

* automatic-reminder enable/disable switch;
* reminder day;
* reminder subject and message;
* Whish email that receives the generated Excel file.

### Petty Cash Configuration

Create exactly one configuration per Center Officer. It contains:

* Employee;
* default/header Cost Center;
* Petty Cash Account;
* Whish/payment clearing account;
* monthly petty-cash limit;
* optional reminder email override;
* Whish phone number, Whish ID, and currency.

The Employee must be linked to its ERPNext User through `Employee.user_id`. When no reminder email
override is present, the linked User's email is used.

Configuration accounts and Cost Center must belong to one company. The payment account must be an
enabled Asset ledger using the company currency. Whish currency must also match company currency.

## Accounting

Finance selects one enabled Expense ledger account belonging to the settlement company. Each
expense must have a Finance-assigned Cost Center from the same company. The generated Journal Entry:

* creates one debit row per Cost Center, aggregated from the expense rows;
* credits the configured payment/Whish clearing account for the settlement total;
* is inserted and submitted only after President approval;
* is linked back to the settlement and protected against duplicate processing.

Cancelling a completed settlement cancels its linked Journal Entry and removes its exact monthly
Whish row.

## Security and integrity

* Center Officers can access only settlements linked to their own active Employee.
* Account balance lookup and account selection are restricted to Finance during Finance Review.
* Later approvers cannot alter previously approved financial data.
* Finance may change only per-expense Cost Centers plus its assigned settlement fields.
* Receipts must resolve to private Frappe File records.
* Active officer/month settlements, officer configurations, and monthly Whish documents have
  database uniqueness constraints.
* Generated spreadsheet text is protected against spreadsheet-formula injection.

## Installation

ERPNext is a required app. Install on an isolated staging site first:

```bash
bench get-app <repository-url> --branch production-hardening
bench --site <staging-site> install-app center_expense_management
bench --site <staging-site> migrate
bench --site <staging-site> run-tests --app center_expense_management
```

The integrity patch deliberately stops migration if existing duplicate configurations, monthly
Whish documents, or active monthly settlements need manual review.

After migration:

1. Configure **Petty Cash Settings**.
2. Update every **Petty Cash Configuration**, including payment and Whish fields.
3. Assign the packaged roles to separate users.
4. Confirm outgoing email and workers/scheduler are enabled.
5. Exercise the full workflow in staging and compare the Journal Entry with the approved accounting
   policy before production deployment.

## Tests

Repository security/installation contract tests run in GitHub Actions and locally with:

```bash
python -m unittest discover -s tests -v
```

These checks do not replace the required Frappe/ERPNext v16 staging integration test.
