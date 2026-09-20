app_name = "center_expense_management"
app_title = "Center Expense Management"
app_publisher = "OmniSync"
app_description = "Manages expense of centers"
app_email = "ibrahim.abdulwahab@gmail.com"
app_license = "mit"

fixtures = [
    {
        "dt": "Workflow State",
        "filters": [["name", "in", [
            "Draft",
            "Pending Accountant Review",
            "Pending Finance Review",
            "Pending Operations Approval",
            "Pending Director Approval",
            "Pending Treasurer Approval",
            "Pending President Approval",
            "Completed",
        ]]],
    },
    {
        "dt": "Workflow Action Master",
        "filters": [["name", "in", [
            "Submit for Accountant Review",
            "Approve",
            "Return to Center Officer",
            "Return to Accountant",
            "Return to Finance",
            "Approve as Director",
            "Return to Operations",
            "Approve as Treasurer",
            "Return to Director",
            "Final Approve",
            "Return to Treasurer",
        ]]],
    },
    {
        "dt": "Workflow",
        "filters": [
            ["name", "=", "Petty Cash Settlement Workflow"]
        ]
    }
]

required_apps = ["erpnext", "custom_lsa"]

permission_query_conditions = {
    "Petty Cash Settlement": "center_expense_management.permissions.settlement_query_condition",
}

has_permission = {
    "Petty Cash Settlement": "center_expense_management.permissions.settlement_has_permission",
}
scheduler_events = {
    "daily": [
        "center_expense_management.tasks.create_monthly_petty_cash_whish",
        "center_expense_management.tasks.send_monthly_reminders",
        "center_expense_management.tasks.send_scheduled_whish_excel",
    ]
}

after_migrate = [
    "center_expense_management.workspace.restore.run",
]
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "center_expense_management",
# 		"logo": "/assets/center_expense_management/logo.png",
# 		"title": "Center Expense Management",
# 		"route": "/center_expense_management",
# 		"has_permission": "center_expense_management.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/center_expense_management/css/center_expense_management.css"
# app_include_js = "/assets/center_expense_management/js/center_expense_management.js"

# include js, css files in header of web template
# web_include_css = "/assets/center_expense_management/css/center_expense_management.css"
# web_include_js = "/assets/center_expense_management/js/center_expense_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "center_expense_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "center_expense_management/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "center_expense_management.utils.jinja_methods",
# 	"filters": "center_expense_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "center_expense_management.install.before_install"
# after_install = "center_expense_management.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "center_expense_management.uninstall.before_uninstall"
# after_uninstall = "center_expense_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "center_expense_management.utils.before_app_install"
# after_app_install = "center_expense_management.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "center_expense_management.utils.before_app_uninstall"
# after_app_uninstall = "center_expense_management.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "center_expense_management.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "center_expense_management.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"center_expense_management.tasks.all"
# 	],
# 	"daily": [
# 		"center_expense_management.tasks.daily"
# 	],
# 	"hourly": [
# 		"center_expense_management.tasks.hourly"
# 	],
# 	"weekly": [
# 		"center_expense_management.tasks.weekly"
# 	],
# 	"monthly": [
# 		"center_expense_management.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "center_expense_management.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "center_expense_management.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "center_expense_management.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "center_expense_management.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["center_expense_management.utils.before_request"]
# after_request = ["center_expense_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["center_expense_management.utils.before_job"]
# after_job = ["center_expense_management.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"center_expense_management.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
