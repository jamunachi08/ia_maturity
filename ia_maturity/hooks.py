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
# Both hooks also run GRC setup; GRC setup itself is gated by the site's grc_enabled flag.
# install_type_defaults runs last: it needs GRC setup to have published the seed templates.
after_install = ["ia_maturity.install.after_install", "ia_maturity.grc.setup.setup", "ia_maturity.install.install_type_defaults"]
after_migrate = ["ia_maturity.install.after_migrate", "ia_maturity.grc.setup.setup"]

# Desk assets ------------------------------------------------------------------
app_include_css = "/assets/ia_maturity/css/ia_maturity_desk.css"

# Document events ------------------------------------------------------------
doc_events = {
	"User": {
		"before_insert": "ia_maturity.grc.profile.set_new_user_workspace_defaults",
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

# GRC platform integration (site activation uses grc_enabled).
from ia_maturity.grc.schema import TENANT_DOCTYPES

auth_hooks = ["ia_maturity.grc.security.guard_request"]
after_request = ["ia_maturity.grc.security.after_request"]
page_renderer = ["ia_maturity.grc.routing.GRCLoginPage"]
get_website_user_home_page = "ia_maturity.grc.routing.website_home"
website_route_rules = [
    {"from_route": "/grc/<path:app_path>", "to_route": "grc"},
    {"from_route": "/onboarding", "to_route": "grc"},
    {"from_route": "/grc-site/<path:page>", "to_route": "grc-site"},
]
scheduler_events = {"daily": ["ia_maturity.grc.notifications.send_reminders"]}
role_home_page.update({
    "GRC Customer": "grc/customer", "GRC Organization Admin": "grc/customer",
    "GRC Auditor": "grc/auditor", "GRC Reviewer": "grc/auditor", "GRC App Admin": "grc/auditor",
    "GRC Consultant": "grc/auditor", "GRC Manager": "grc/auditor",
    "IA Maturity Reviewer": "grc/auditor", "IA Maturity Manager": "grc/auditor"
})
doc_events["User"]["before_validate"] = "ia_maturity.grc.identity.validate_user_names"
doc_events["User"]["validate"] = "ia_maturity.grc.security.validate_user"
doc_events["DocShare"] = {"validate": "ia_maturity.grc.security.forbid_share"}
doc_events["IA Maturity Template"] = {"validate": "ia_maturity.grc.assessments.validate_template"}
doc_events["IA Maturity Assessment"] = {"before_validate": "ia_maturity.grc.assessments.freeze"}
for _doctype in TENANT_DOCTYPES:
    _previous = has_permission.get(_doctype)
    has_permission[_doctype] = ([_previous] if _previous else []) + ["ia_maturity.grc.security.has_permission"]
    _previous = permission_query_conditions.get(_doctype)
    permission_query_conditions[_doctype] = ([_previous] if _previous else []) + [
        "ia_maturity.grc.conditions.query_" + _doctype.lower().replace(" ", "_")
    ]
    doc_events.setdefault(_doctype, {}).update({
        "validate": "ia_maturity.grc.security.validate_document",
        "on_update": "ia_maturity.grc.security.changed",
    })
doc_events["GRC Settings"] = {
    "validate": "ia_maturity.grc.security.validate_document",
    "on_update": "ia_maturity.grc.security.changed",
}
has_permission["File"] = "ia_maturity.grc.security.file_permission"

override_whitelisted_methods = {"frappe.core.doctype.user.user.update_password": "ia_maturity.grc.auth.reset_password"}

on_login = ["ia_maturity.grc.auth.enforce_staff_mfa"]
on_session_creation = ["ia_maturity.grc.mfa.stamp_session"]

has_permission["*"] = "ia_maturity.grc.security.document_boundary"

override_whitelisted_methods["frappe.utils.print_format.download_pdf"] = "ia_maturity.printing.download_pdf"

override_whitelisted_methods["frappe.core.doctype.user.user.sign_up"] = "ia_maturity.grc.auth.sign_up"

boot_session = ["ia_maturity.grc.desk.boot_session"]

app_include_js = ["/assets/ia_maturity/js/grc_staff_desk.js"]

doc_events["File"] = {"on_trash": "ia_maturity.grc.security.evidence_deleted"}

# Public site content is writable only through the audited approval service.
for _site_dt in ("GRC Site Content", "GRC Site Revision", "GRC Site Event"):
    doc_events.setdefault(_site_dt, {}).update({"validate": "ia_maturity.grc.site_content.guard_document", "on_trash": "ia_maturity.grc.site_content.guard_delete"})

for _operations_dt in ("GRC Operations Policy", "GRC Operations Request"):
    doc_events.setdefault(_operations_dt, {}).update({"validate":"ia_maturity.grc.operations.guard", "on_trash":"ia_maturity.grc.operations.no_delete"})

# Themes and screen layouts change only through their audited admin services.
doc_events["GRC Theme"] = {"validate": "ia_maturity.grc.themes.guard", "on_trash": "ia_maturity.grc.themes.guard"}
doc_events["GRC Screen Layout"] = {"validate": "ia_maturity.grc.screen_layouts.guard", "on_trash": "ia_maturity.grc.screen_layouts.guard"}

# Scope and onboarding records are writable only through their audited services.
doc_events["GRC Audit Scope Configuration"] = {"validate": "ia_maturity.grc.scope.guard_configuration", "on_trash": "ia_maturity.grc.scope.no_delete"}
doc_events["GRC Onboarding Invitation"] = {"validate": "ia_maturity.grc.onboarding.guard", "on_trash": "ia_maturity.grc.scope.no_delete"}
doc_events["Email Queue"] = {"on_change": "ia_maturity.grc.onboarding.email_queue_changed"}
has_permission["GRC Onboarding Invitation"] = "ia_maturity.grc.onboarding.has_permission"
permission_query_conditions["GRC Onboarding Invitation"] = "ia_maturity.grc.onboarding.query_condition"

from ia_maturity.grc.departments import DEPARTMENT_TABLES
for _department_dt in DEPARTMENT_TABLES:
    doc_events[_department_dt] = {"validate": "ia_maturity.grc.departments.guard", "on_trash": "ia_maturity.grc.scope.no_delete"}
