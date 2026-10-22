app_name = "ia_maturity"
app_title = "IA Maturity"
app_publisher = "IA Maturity Contributors"
app_description = "Internal Audit Function Maturity Assessment (IIA GIAS) for Frappe / ERPNext"
app_email = "jamunachi007@gmail.com"
app_license = "MIT"
required_apps = ["frappe"]

# Installation / migration ---------------------------------------------------
after_install = "ia_maturity.install.after_install"
after_migrate = "ia_maturity.install.after_migrate"

# Desk assets ------------------------------------------------------------------
app_include_css = "/assets/ia_maturity/css/ia_maturity_desk.css"

# Document events ------------------------------------------------------------
doc_events = {
	"User": {
		"after_insert": "ia_maturity.permissions.on_user_created",
	}
}

# Jinja helpers used by the print format ----------------------------------------
jinja = {
	"methods": [
		"ia_maturity.report_data.get_report_context",
		"ia_maturity.report_data.section_bar_svg",
	]
}

# Portal ---------------------------------------------------------------------
portal_menu_items = [
	{
		"title": "IA Maturity Assessment",
		"route": "/ia-assessment",
		"reference_doctype": "IA Maturity Assessment",
		"role": "IA Assessment Respondent",
	}
]

role_home_page = {"IA Assessment Respondent": "ia-assessment"}

# Permissions ------------------------------------------------------------------
has_permission = {
	"IA Maturity Action": "ia_maturity.permissions.action_has_permission",
}
permission_query_conditions = {
	"IA Maturity Action": "ia_maturity.permissions.action_query_conditions",
}
