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
		with patch.object(permissions, "frappe", self.fake_frappe(roles={"Finance"})):
			self.assertEqual(permissions.settlement_query_condition(), "")

	def test_center_officer_is_limited_to_linked_employee(self):
		fake = self.fake_frappe(roles={"Center Officer"}, employee="HR-EMP-0001")
		with patch.object(permissions, "frappe", fake):
			condition = permissions.settlement_query_condition()
			self.assertIn("center_officer", condition)
			self.assertIn("HR-EMP-0001", condition)

	def test_unlinked_user_is_denied(self):
		with patch.object(permissions, "frappe", self.fake_frappe(roles={"Center Officer"})):
			self.assertEqual(permissions.settlement_query_condition(), "1=0")

	def test_center_officer_cannot_access_another_employee(self):
		fake = self.fake_frappe(roles={"Center Officer"}, employee="HR-EMP-0001")
		doc = types.SimpleNamespace(center_officer="HR-EMP-0002")
		with patch.object(permissions, "frappe", fake):
			self.assertFalse(permissions.settlement_has_permission(doc))

	def test_center_officer_can_create_before_identity_is_bound(self):
		fake = self.fake_frappe(roles={"Center Officer"}, employee="HR-EMP-0001")
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

	def test_every_workflow_role_is_packaged(self):
		workflow = self.load_json("center_expense_management/fixtures/workflow.json")[0]
		roles = self.load_json("center_expense_management/fixtures/role.json")
		packaged = {row["name"] for row in roles}
		referenced = {row["allow_edit"] for row in workflow["states"]}
		referenced.update(row["allowed"] for row in workflow["transitions"])
		self.assertLessEqual(referenced, packaged)

	def test_finance_has_settlement_permission(self):
		doctype = self.load_json(
			"center_expense_management/center_expense_management/doctype/"
			"petty_cash_settlement/petty_cash_settlement.json"
		)
		roles = {row["role"] for row in doctype["permissions"]}
		self.assertIn("Finance", roles)

	def test_no_hard_coded_whish_account(self):
		controller = (
			ROOT
			/ "center_expense_management/center_expense_management/doctype/"
			"petty_cash_settlement/petty_cash_settlement.py"
		).read_text()
		self.assertNotIn('"Whish - OS"', controller)


if __name__ == "__main__":
	unittest.main()
