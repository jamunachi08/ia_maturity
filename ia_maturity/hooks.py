app_name = "ia_maturity"
app_title = "AlphaX IA Maturity"
app_publisher = "IRSAA Business Solutions"
app_description = "AlphaX IA Maturity – Internal Audit Function Maturity Assessment (IIA GIAS) for Frappe / ERPNext"
app_email = "erpsupport@irsaa.com"
app_license = "MIT"
required_apps = ["frappe"]
app_logo_url = "/assets/ia_maturity/images/alphax_mark.png"

try:  # /app on Frappe v15, /desk on v16+
	from ia_maturity.compat import desk_base as _desk_base

	_DESK = _desk_base()
except Exception:
	_DESK = "/app"

# Entry on the apps screen (Frappe v15 /apps, v16 desktop)
add_to_apps_screen = [
	{
		"name": "ia_maturity",
		"logo": "/assets/ia_maturity/images/alphax_icon.png",
		"title": "AlphaX IA Maturity",
		"route": f"{_DESK}/ia-maturity",
		# only desk staff see the tile; respondents must land on the portal (role_home_page)
		"has_permission": "ia_maturity.permissions.show_on_apps_screen",
	}
]

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
		"ia_maturity.branding.get_brand",
		"ia_maturity.report_data.arabic_font_css",
		"ia_maturity.report_data.ia_report_guard",
	]
}

# Portal ---------------------------------------------------------------------
portal_menu_items = [
	{
		"title": "AlphaX IA Maturity Assessment",
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
