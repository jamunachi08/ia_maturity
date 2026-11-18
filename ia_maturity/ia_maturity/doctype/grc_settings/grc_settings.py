from frappe.model.document import Document


class GRCSettings(Document):
    def validate(self):
        from ia_maturity.grc.maturity_visibility import validate_mode
        validate_mode(self.get("overall_maturity_visibility") or "Hidden")
        from ia_maturity.grc.email_policy import validate_policy
        validate_policy(self)
        from ia_maturity.grc.mfa_policy import validate_settings
        validate_settings(self)
