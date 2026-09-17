import frappe


APPROVER_ROLES = {
	"System Manager",
	"LSA Accountant",
	"LSA Finance Approver",
	"LSA Operations Manager",
	"LSA Executive Director",
	"LSA Board Treasurer",
	"LSA President",
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
	if permission_type == "create":
		return True

	employee = employee_for_user(user)
	return bool(employee and doc.center_officer == employee)
