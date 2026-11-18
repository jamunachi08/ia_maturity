"""Revoke only journey-test staff assignments on the isolated local fixture site."""
import os
import re
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
os.chdir(root/"sites")
import frappe
frappe.init(site="grc.local")
try:
    frappe.connect()
    if not (frappe.conf.db_name == "grc_local" and frappe.conf.mute_emails and frappe.conf.allow_tests):
        raise RuntimeError("Requires the isolated muted local acceptance site.")
    email=sys.argv[1]
    if not re.fullmatch(r"grc-journey-[a-z0-9-]+@example\.test",email):
        raise ValueError("Requires a reserved journey test address.")
    frappe.set_user("Administrator")
    from ia_maturity.grc.administration import assign_customer
    for membership in frappe.get_all("GRC Organization Membership",filters={"user":email},fields=["entity"]):
        if not membership.entity.startswith("Journey acceptance "):
            raise ValueError("Unexpected organization.")
        for assignment in frappe.get_all("Auditor Customer Assignment",filters={"entity":membership.entity,"active":1},fields=["auditor","responsibility"]):
            if assignment.auditor not in {"auditor@grc.example.test","reviewer@grc.example.test"}:
                raise ValueError("Unexpected staff assignment.")
            assign_customer(membership.entity,assignment.auditor,assignment.responsibility,active=0)
    frappe.db.commit()
finally:
    frappe.destroy()
