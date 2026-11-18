"""Read-only deployment readiness check: bench --site SITE execute ia_maturity.grc.health.check."""
# Kept as a short discoverable entry point for local operators.
import os
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]/"sites")
import frappe
frappe.init(site="grc.local");frappe.connect()
from ia_maturity.grc.health import check
print(frappe.as_json(check()))
frappe.destroy()
