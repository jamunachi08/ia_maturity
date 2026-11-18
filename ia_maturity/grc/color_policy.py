"""Manager-controlled presentation ranges; never changes assessment scoring."""
import hashlib
import json
import math
import re
from pathlib import Path
import frappe
from frappe import _
from ia_maturity.grc import security as sec
DEFAULT_RANGES=json.loads((Path(__file__).parents[1]/"public"/"section-color-ranges.json").read_text())

def validate_ranges(value):
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):frappe.throw(_("Enter a valid list of color ranges."))
    if not isinstance(value,list) or not value:frappe.throw(_("Add at least one color range starting at 0%."))
    result=[]
    for row in value:
        if not isinstance(row,dict) or isinstance(row.get("min_score"),bool):frappe.throw(_("Each range needs a numeric starting percentage and a hex color."))
        try:minimum=float(row.get("min_score"))
        except (TypeError,ValueError):frappe.throw(_("Enter a numeric starting percentage."))
        if not math.isfinite(minimum) or not 0<=minimum<=100:frappe.throw(_("Range percentages must be between 0 and 100."))
        color=str(row.get("color") or "").strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",color):frappe.throw(_("Choose a color in #RRGGBB format."))
        result.append({"min_score":minimum,"color":color.upper()})
    result.sort(key=lambda row:row["min_score"])
    if result[0]["min_score"]!=0 or len({row["min_score"] for row in result})!=len(result):frappe.throw(_("Ranges must start at 0% and have unique starting percentages."))
    return result

def get_ranges():
    raw=frappe.get_cached_doc("GRC Settings").get("section_color_ranges")
    return validate_ranges(raw) if raw else [dict(row) for row in DEFAULT_RANGES]

def revision(ranges):return hashlib.sha256(json.dumps(ranges,sort_keys=True).encode()).hexdigest()

def require_manager():
    sec.require_login()
    if not (sec.is_admin() or "GRC Manager" in sec.roles()):sec.deny()

@frappe.whitelist()
def color_ranges():
    require_manager()
    ranges=get_ranges()
    return {"ranges":ranges,"revision":revision(ranges)}

@frappe.whitelist(methods=["POST"])
def save_color_ranges(ranges,expected_revision=None):
    require_manager()
    ranges=validate_ranges(ranges)
    # Serialize policy writes until the request transaction commits.
    frappe.db.sql("select name from `tabDocType` where name=%s for update",("GRC Settings",))
    frappe.clear_document_cache("GRC Settings","GRC Settings")
    before=get_ranges()
    if expected_revision and expected_revision!=revision(before):frappe.throw(_("Color ranges changed. Reload before saving."),frappe.TimestampMismatchError)
    doc=frappe.get_single("GRC Settings")
    doc.section_color_ranges=frappe.as_json(ranges)
    with sec.service_write():doc.save(ignore_permissions=True)
    sec.log("Section color ranges changed",details={"before":before,"after":ranges})
    return {"ranges":ranges,"revision":revision(ranges)}
