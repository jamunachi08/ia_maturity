"""Site-scoped React entry points; ERP routes retain Frappe's normal renderer."""
from frappe.website.page_renderers.template_page import TemplatePage
from ia_maturity.grc.security import enabled, home, account_type


class GRCLoginPage(TemplatePage):
    def __init__(self, path, http_status_code=None):
        self.requested_path = path
        super().__init__("grc", http_status_code)

    def can_render(self):
        return self.requested_path in {"login", "signup", "update-password"} and enabled() and super().can_render()


def website_home(user):
    if enabled() and user != "Guest" and account_type(user) in {"Customer", "Auditor"}:
        return home(user).lstrip("/")
    return None
