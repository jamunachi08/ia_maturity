"""Admin-defined screen layouts. Today: the company profile screen.

Two built-in presets ship with the app; admins duplicate and adjust them, then choose
the default. Layouts change presentation only: validation, permissions and the saved
data are identical in every layout.
"""
import re

import frappe
from frappe import _
from frappe.utils import cint

from ia_maturity.grc import security as sec

DOCTYPE = "GRC Screen Layout"
SCREENS = ("Company profile",)
STYLES = ("Standard", "Compact")
YES_NO = ("Use global setting", "Dropdown", "Buttons")
OPTIONS = ("style", "columns", "yes_no_display", "show_intro", "show_report_lookup", "show_saved_assessments",
           "continue_label", "continue_label_ar")
PRESETS = {
    "Standard": {
        "description": "The original two-column company profile form with explanatory notes.",
        "style": "Standard", "columns": "2", "yes_no_display": "Use global setting", "show_intro": 1,
        "show_report_lookup": 0, "show_saved_assessments": 0, "continue_label": "", "continue_label_ar": "",
    },
    "Compact": {
        "description": "Single card in workbook style: one column, Yes/No buttons, continue straight to the questions, "
                       "report lookup by ID and saved assessments.",
        "style": "Compact", "columns": "1", "yes_no_display": "Buttons", "show_intro": 0,
        "show_report_lookup": 1, "show_saved_assessments": 1,
        "continue_label": "Continue to questions", "continue_label_ar": "المتابعة إلى الأسئلة",
    },
}
DEFAULT_PRESET = "Standard"


def _ready():
    return frappe.db.table_exists(DOCTYPE)


def _global_yes_no():
    value = frappe.db.get_single_value("GRC Settings", "organization_yes_no_display")
    return value if value in ("Dropdown", "Buttons") else "Dropdown"


def resolve(row):
    """Layout options as the portal uses them, with the Yes/No style resolved."""
    values = {key: row.get(key) for key in OPTIONS}
    values["name"] = row.get("name")
    values["style"] = values["style"] if values["style"] in STYLES else "Standard"
    values["columns"] = 1 if str(values["columns"]) == "1" else 2
    display = values.get("yes_no_display")
    values["yes_no_display"] = display if display in ("Dropdown", "Buttons") else _global_yes_no()
    for key in ("show_intro", "show_report_lookup", "show_saved_assessments"):
        values[key] = bool(cint(values.get(key)))
    return values


def layout_for(screen="Company profile"):
    row = None
    if _ready():
        row = frappe.db.get_value(DOCTYPE, {"screen": screen, "is_default": 1}, ["name", *OPTIONS], as_dict=True)
    return resolve(row or {"name": DEFAULT_PRESET, **PRESETS[DEFAULT_PRESET]})


def setup():
    if not _ready():
        return
    with sec.service_write():
        for name, values in PRESETS.items():
            if not frappe.db.exists(DOCTYPE, name):
                frappe.get_doc({"doctype": DOCTYPE, "layout_name": name, "screen": "Company profile", "is_system": 1,
                    **values}).insert(ignore_permissions=True)
        for screen in SCREENS:
            if not frappe.db.exists(DOCTYPE, {"screen": screen, "is_default": 1}):
                frappe.db.set_value(DOCTYPE, DEFAULT_PRESET, "is_default", 1, update_modified=False)


def guard(doc, method=None):
    if not sec.enabled() or frappe.flags.get("in_migrate") or frappe.flags.get("in_install"):
        return
    if not frappe.flags.get("grc_service_write"):
        sec.deny()


def _clean(data):
    out = {}
    out["style"] = data.get("style") if data.get("style") in STYLES else frappe.throw(_("Choose a valid style."))
    out["columns"] = "1" if str(data.get("columns")) == "1" else "2"
    out["yes_no_display"] = data.get("yes_no_display") if data.get("yes_no_display") in YES_NO else frappe.throw(
        _("Choose a valid Yes/No display."))
    for key in ("show_intro", "show_report_lookup", "show_saved_assessments"):
        out[key] = 1 if cint(data.get(key)) else 0
    for key in ("continue_label", "continue_label_ar"):
        value = str(data.get(key) or "").strip()
        if len(value) > 60:
            frappe.throw(_("Button labels must be 60 characters or fewer."))
        out[key] = value
    return out


@frappe.whitelist()
def screen_layouts():
    sec.require_admin()
    rows = frappe.get_all(DOCTYPE, fields=["name", "screen", "description", "is_default", "is_system", "modified", *OPTIONS],
        order_by="is_system desc, layout_name asc")
    return {"layouts": rows, "screens": list(SCREENS), "styles": list(STYLES), "yes_no": list(YES_NO),
            "global_yes_no": _global_yes_no()}


@frappe.whitelist(methods=["POST"])
def save_screen_layout(data, name=None):
    sec.require_admin()
    data = frappe.parse_json(data) if isinstance(data, str) else dict(data or {})
    values = _clean(data)
    description = str(data.get("description") or "").strip()[:500]
    if name:
        if not frappe.db.exists(DOCTYPE, name):
            frappe.throw(_("This layout no longer exists."))
        doc = frappe.get_doc(DOCTYPE, name, for_update=True)
        if doc.is_system:
            frappe.throw(_("Built-in layouts cannot be changed. Duplicate the layout to make your own version."))
        before = {k: doc.get(k) for k in OPTIONS}
        doc.update({**values, "description": description})
    else:
        layout_name = str(data.get("layout_name") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &()\-]{1,38}[A-Za-z0-9)]", layout_name):
            frappe.throw(_("Enter a layout name of 3 to 40 letters, digits, spaces, &, ( ) or -."))
        if frappe.db.exists(DOCTYPE, layout_name):
            frappe.throw(_("A layout with this name already exists."))
        screen = data.get("screen") or "Company profile"
        if screen not in SCREENS:
            frappe.throw(_("Choose a valid screen."))
        before = None
        doc = frappe.get_doc({"doctype": DOCTYPE, "layout_name": layout_name, "screen": screen,
            "description": description, "is_system": 0, **values})
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Screen layout created" if before is None else "Screen layout changed",
        details={"layout": doc.name, "before": before, "after": values})
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def set_default_screen_layout(name):
    sec.require_admin()
    if not frappe.db.exists(DOCTYPE, name):
        frappe.throw(_("This layout no longer exists."))
    screen = frappe.db.get_value(DOCTYPE, name, "screen")
    frappe.db.sql("select name from `tabGRC Screen Layout` order by name for update")
    previous = frappe.db.get_value(DOCTYPE, {"screen": screen, "is_default": 1}, "name")
    with sec.service_write():
        for other in frappe.get_all(DOCTYPE, filters={"screen": screen, "is_default": 1}, pluck="name"):
            frappe.db.set_value(DOCTYPE, other, "is_default", 0)
        frappe.db.set_value(DOCTYPE, name, "is_default", 1)
    sec.log("Default screen layout changed", details={"screen": screen, "before": previous, "after": name})
    return layout_for(screen)


@frappe.whitelist(methods=["POST"])
def delete_screen_layout(name):
    sec.require_admin()
    doc = frappe.get_doc(DOCTYPE, name)
    if doc.is_system or doc.is_default:
        frappe.throw(_("Built-in and default layouts cannot be deleted."))
    with sec.service_write():
        frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)
    sec.log("Screen layout deleted", details={"layout": name})
    return {"deleted": name}


# ---------------------------------------------------------------------------------------------
# Compact-layout helpers: both return only assessments the user can already open.

NOT_FOUND = "No report with this ID is available to you."


@frappe.whitelist()
def find_report(report_id):
    sec.require_login()
    report_id = str(report_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]{3,79}", report_id):
        frappe.throw(_(NOT_FOUND))
    from ia_maturity.grc.auth import limit
    limit("report-lookup", frappe.session.user, 30, seconds=600)
    name = frappe.db.get_value("IA Maturity Assessment", {"grc_report_id": report_id}, "name") or (
        report_id if frappe.db.exists("IA Maturity Assessment", report_id) else None)
    if not name:
        frappe.throw(_(NOT_FOUND))
    doc = frappe.get_doc("IA Maturity Assessment", name)
    # Same message whether it does not exist or is not visible: IDs cannot be probed.
    if not sec.can_read_assessment(doc):
        frappe.throw(_(NOT_FOUND))
    return {"name": doc.name, "report_id": doc.get("grc_report_id") or doc.name}


@frappe.whitelist()
def saved_assessments(entity, limit=10):
    sec.require_entity(entity)
    limit = max(1, min(25, cint(limit) or 10))
    rows = frappe.get_all("IA Maturity Assessment", filters={"entity": entity},
        fields=["name", "entity", "respondent", "grc_department", "grc_assessment_type", "template",
                "grc_report_id", "docstatus", "answered_count", "question_count", "modified", "grc_assignment"],
        order_by="modified desc", limit=limit * 4)
    out = []
    for row in rows:
        if sec.can_read_assessment(row):
            out.append({"name": row.name, "report_id": row.grc_report_id or row.name,
                "assessment_type": row.grc_assessment_type, "submitted": row.docstatus == 1,
                "answered": row.answered_count, "questions": row.question_count, "modified": row.modified})
        if len(out) >= limit:
            break
    return out
