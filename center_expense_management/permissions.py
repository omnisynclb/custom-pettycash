import frappe


APPROVER_ROLES = {
	"System Manager",
	"LSA HR Manager",
	"LSA Accountant",
	"LSA Finance Approver",
	"LSA Operations Manager",
	"LSA Executive Director",
}


def _roles(user):
	return set(frappe.get_roles(user))


def can_review_all(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(_roles(user) & APPROVER_ROLES)


def employee_for_user(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def settlement_query_condition(user=None):
	user = user or frappe.session.user
	if can_review_all(user):
		return ""

	employee = employee_for_user(user)
	if not employee:
		return "1=0"

	return f"`tabPetty Cash Settlement`.`center_officer` = {frappe.db.escape(employee)}"


def settlement_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if can_review_all(user):
		return True

	if "LSA Center Officer" not in _roles(user):
		return False

	employee = employee_for_user(user)
	if permission_type == "create":
		return bool(employee)

	# Receipt uploads happen before the first save and Frappe checks `write`
	# against a temporary `new-petty-cash-settlement-*` document. Permit only
	# this unsaved case for a Center Officer linked to an active Employee.
	doc_name = str(getattr(doc, "name", "") or "")
	is_new = getattr(doc, "is_new", None)
	if (
		permission_type == "write"
		and employee
		and ((callable(is_new) and is_new()) or doc_name.startswith("new-petty-cash-settlement-"))
	):
		return True

	return bool(employee and doc.center_officer == employee)
