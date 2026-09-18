from pathlib import Path

import frappe
from frappe.modules.import_file import import_file_by_path


FIXTURES = (
	Path(__file__).parents[1]
	/ "center_expense_management"
	/ "workspace"
	/ "petty_cash"
	/ "petty_cash.json",
	Path(__file__).parents[1]
	/ "center_expense_management"
	/ "workspace_sidebar"
	/ "petty_cash"
	/ "petty_cash.json",
)


def run():
	for fixture in FIXTURES:
		if not fixture.exists():
			frappe.throw(f"Petty Cash workspace fixture is missing: {fixture}")
		if not import_file_by_path(str(fixture), force=True, ignore_version=True):
			frappe.throw(f"Petty Cash workspace fixture could not be imported: {fixture}")

	frappe.clear_cache()
