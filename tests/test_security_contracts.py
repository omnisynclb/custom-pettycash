import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

try:
	import frappe  # noqa: F401
except ModuleNotFoundError:
	sys.modules["frappe"] = types.SimpleNamespace()

from center_expense_management import permissions


ROOT = Path(__file__).resolve().parents[1]


class PermissionTests(unittest.TestCase):
	def fake_frappe(self, *, roles=(), employee=None):
		return types.SimpleNamespace(
			session=types.SimpleNamespace(user="officer@example.com"),
			get_roles=lambda user: list(roles),
			db=types.SimpleNamespace(
				get_value=lambda *args, **kwargs: employee,
				escape=lambda value: "'" + value.replace("'", "''") + "'",
			),
		)

	def test_approver_can_query_all(self):
		with patch.object(permissions, "frappe", self.fake_frappe(roles={"LSA Finance Approver"})):
			self.assertEqual(permissions.settlement_query_condition(), "")

	def test_center_officer_is_limited_to_linked_employee(self):
		fake = self.fake_frappe(roles={"LSA Center Officer"}, employee="HR-EMP-0001")
		with patch.object(permissions, "frappe", fake):
			condition = permissions.settlement_query_condition()
			self.assertIn("center_officer", condition)
			self.assertIn("HR-EMP-0001", condition)

	def test_unlinked_user_is_denied(self):
		with patch.object(permissions, "frappe", self.fake_frappe(roles={"LSA Center Officer"})):
			self.assertEqual(permissions.settlement_query_condition(), "1=0")

	def test_center_officer_cannot_access_another_employee(self):
		fake = self.fake_frappe(roles={"LSA Center Officer"}, employee="HR-EMP-0001")
		doc = types.SimpleNamespace(center_officer="HR-EMP-0002")
		with patch.object(permissions, "frappe", fake):
			self.assertFalse(permissions.settlement_has_permission(doc))

	def test_center_officer_can_create_before_identity_is_bound(self):
		fake = self.fake_frappe(roles={"LSA Center Officer"}, employee="HR-EMP-0001")
		doc = types.SimpleNamespace(center_officer=None)
		with patch.object(permissions, "frappe", fake):
			self.assertTrue(permissions.settlement_has_permission(doc, permission_type="create"))


class RepositoryContractTests(unittest.TestCase):
	def load_json(self, relative_path):
		return json.loads((ROOT / relative_path).read_text())

	def test_every_json_file_is_valid(self):
		for path in ROOT.rglob("*.json"):
			with self.subTest(path=path):
				json.loads(path.read_text())

	def test_workflow_separates_self_approval(self):
		workflow = self.load_json("center_expense_management/fixtures/workflow.json")[0]
		self.assertTrue(workflow["transitions"])
		for row in workflow["transitions"]:
			with self.subTest(action=row["action"], state=row["state"]):
				if row["action"] == "Submit for Accountant Review":
					self.assertTrue(row["allow_self_approval"])
				else:
					self.assertFalse(row["allow_self_approval"])

	def test_every_workflow_role_uses_production_lsa_roles(self):
		workflow = self.load_json("center_expense_management/fixtures/workflow.json")[0]
		referenced = {row["allow_edit"] for row in workflow["states"]}
		referenced.update(row["allowed"] for row in workflow["transitions"])
		self.assertLessEqual(
			referenced,
			{
				"LSA Center Officer", "LSA Accountant", "LSA Finance Approver",
				"LSA Operations Manager", "LSA Executive Director",
				"LSA Board Treasurer", "LSA President",
			},
		)

	def test_finance_has_settlement_permission(self):
		doctype = self.load_json(
			"center_expense_management/center_expense_management/doctype/"
			"petty_cash_settlement/petty_cash_settlement.json"
		)
		roles = {row["role"] for row in doctype["permissions"]}
		self.assertIn("LSA Finance Approver", roles)
		self.assertIn("LSA Executive Director", roles)
		self.assertIn("LSA Board Treasurer", roles)
		self.assertIn("LSA President", roles)

	def test_workflow_reaches_president_before_completion(self):
		workflow = self.load_json("center_expense_management/fixtures/workflow.json")[0]
		forward = [
			(row["state"], row["next_state"])
			for row in workflow["transitions"]
			if row["action"] in {
				"Submit for Accountant Review", "Approve", "Approve as Director",
				"Approve as Treasurer", "Final Approve",
			}
		]
		self.assertEqual(
			forward,
			[
				("Draft", "Pending Accountant Review"),
				("Pending Accountant Review", "Pending Finance Review"),
				("Pending Finance Review", "Pending Operations Approval"),
				("Pending Operations Approval", "Pending Director Approval"),
				("Pending Director Approval", "Pending Treasurer Approval"),
				("Pending Treasurer Approval", "Pending President Approval"),
				("Pending President Approval", "Completed"),
			],
		)

	def test_workflow_references_are_shipped_as_fixtures(self):
		workflow = self.load_json("center_expense_management/fixtures/workflow.json")[0]
		state_rows = self.load_json("center_expense_management/fixtures/workflow_state.json")
		action_rows = self.load_json("center_expense_management/fixtures/workflow_action_master.json")
		shipped_states = {row["name"] for row in state_rows}
		shipped_actions = {row["name"] for row in action_rows}
		self.assertEqual({row["state"] for row in workflow["states"]}, shipped_states)
		self.assertEqual({row["action"] for row in workflow["transitions"]}, shipped_actions)

		hooks = (ROOT / "center_expense_management/hooks.py").read_text()
		self.assertLess(hooks.index('"dt": "Workflow State"'), hooks.index('"dt": "Workflow"'))
		self.assertLess(hooks.index('"dt": "Workflow Action Master"'), hooks.index('"dt": "Workflow"'))

	def test_settings_and_finance_cost_center_exist(self):
		settings = self.load_json(
			"center_expense_management/center_expense_management/doctype/"
			"petty_cash_settings/petty_cash_settings.json"
		)
		self.assertTrue(settings["issingle"])
		self.assertIn("whish_email", {field["fieldname"] for field in settings["fields"]})

		expense = self.load_json(
			"center_expense_management/center_expense_management/doctype/"
			"petty_cash_expense/petty_cash_expense.json"
		)
		cost_center = next(field for field in expense["fields"] if field["fieldname"] == "cost_center")
		self.assertEqual(cost_center["permlevel"], 1)

	def test_no_hard_coded_whish_account(self):
		controller = (
			ROOT
			/ "center_expense_management/center_expense_management/doctype/"
			"petty_cash_settlement/petty_cash_settlement.py"
		).read_text()
		self.assertNotIn('"Whish - OS"', controller)
		self.assertNotIn("custom_lsa_payroll_journal_approval", controller)
		self.assertNotIn("custom_lsa_monthly_payroll_approval", controller)

	def test_production_app_dependency_is_declared(self):
		hooks = (ROOT / "center_expense_management/hooks.py").read_text()
		self.assertIn('required_apps = ["erpnext", "custom_lsa"]', hooks)


if __name__ == "__main__":
	unittest.main()
