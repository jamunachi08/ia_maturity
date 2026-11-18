"""Preserve the existing default on GRC sites once; never reactivate templates."""
import frappe


def execute():
    if not frappe.utils.cint(frappe.conf.get("grc_enabled")):
        return
    name = frappe.db.get_single_value("IA Maturity Settings", "default_template")
    if name:
        row = frappe.db.get_value("IA Maturity Template", name, ["is_active", "grc_published", "assessment_type"], as_dict=True)
        if row and row.is_active and row.grc_published:
            kind = row.assessment_type or "Internal Audit"
            if not frappe.db.exists("IA Maturity Template", {"assessment_type": kind, "grc_is_default": 1}):
                frappe.db.set_value("IA Maturity Template", name, {"assessment_type": kind, "grc_is_default": 1})
