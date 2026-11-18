"""Use the requested visible section tabs instead of the former completion default."""
import frappe

def execute():
    value=frappe.db.get_single_value("GRC Settings","customer_sections_visibility")
    if value in (None,"","Collapsed until complete"):
        frappe.db.set_single_value("GRC Settings","customer_sections_visibility","Always expanded")
    frappe.clear_document_cache("GRC Settings","GRC Settings")
