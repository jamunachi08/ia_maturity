"""Portal colour themes: built-in presets, admin-defined themes and the site default.

The portal derives every brand shade from these few colours at runtime, so a theme
change needs no rebuild. Status colours (success, warning, danger) stay fixed because
they carry meaning in reports and workflow states.
"""
import re

import frappe
from frappe import _

from ia_maturity.grc import security as sec

DOCTYPE = "GRC Theme"
COLOURS = ("primary", "primary_dark", "accent", "ink", "muted", "background", "surface", "border")
PRESETS = {
    "IRSAA": {
        "description": "IRSAA logo colours: IRSAA blue with the green accent from the mark and the Business Solutions grey.",
        "primary": "#12506E", "primary_dark": "#0C3A50", "accent": "#487242", "ink": "#1F2A30",
        "muted": "#5A6562", "background": "#F4F7F8", "surface": "#FFFFFF", "border": "#DCE3E6",
    },
    "AlphaX Classic": {
        "description": "The original AlphaX portal colours.",
        "primary": "#176698", "primary_dark": "#104C73", "accent": "#0E6B66", "ink": "#27333E",
        "muted": "#687787", "background": "#F5F7FA", "surface": "#FFFFFF", "border": "#E2E7EC",
    },
}
DEFAULT_PRESET = "IRSAA"
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _ready():
    return frappe.db.table_exists(DOCTYPE)


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Pairs the portal actually draws, with the WCAG AA minimum for normal text.
CONTRAST_RULES = (
    ("primary", "#FFFFFF", 4.5, "White button text on the primary colour"),
    ("primary_dark", "#FFFFFF", 4.5, "White text on the primary dark colour"),
    ("ink", "surface", 7.0, "Text on panels"),
    ("ink", "background", 7.0, "Text on the page background"),
    ("muted", "surface", 4.5, "Muted text on panels"),
    ("primary", "surface", 4.5, "Links on panels"),
    ("accent", "surface", 3.0, "Accent marks on panels"),
)


def validate_colours(values):
    clean = {}
    for key in COLOURS:
        value = str(values.get(key) or "").strip()
        if not HEX.match(value):
            frappe.throw(_("Enter {0} as a six-digit hex colour such as #12506E.").format(key.replace("_", " ")))
        clean[key] = value.upper()
    problems = []
    for fg, bg, minimum, what in CONTRAST_RULES:
        bg_value = clean.get(bg, bg)
        ratio = contrast(clean[fg], bg_value)
        if ratio < minimum:
            problems.append(f"{what}: {ratio:.1f}:1, needs {minimum:g}:1")
    if problems:
        frappe.throw(_("These colours are hard to read. Adjust them and save again.") + "<br>" + "<br>".join(problems))
    return clean


def tokens(name=None):
    """Colours of a theme (default when name is empty); falls back to the IRSAA preset."""
    row = None
    if _ready():
        filters = {"name": name} if name else {"is_default": 1}
        row = frappe.db.get_value(DOCTYPE, filters, ["name", *COLOURS], as_dict=True)
    if not row:
        return {"name": DEFAULT_PRESET, **{k: PRESETS[DEFAULT_PRESET][k] for k in COLOURS}}
    return {"name": row.name, **{k: row[k] for k in COLOURS}}


def setup():
    """Seed the presets; make IRSAA the default when no default exists. Never overwrites admin edits."""
    if not _ready():
        return
    with sec.service_write():
        for name, values in PRESETS.items():
            if not frappe.db.exists(DOCTYPE, name):
                frappe.get_doc({"doctype": DOCTYPE, "theme_name": name, "is_system": 1, **values}).insert(ignore_permissions=True)
        if not frappe.db.exists(DOCTYPE, {"is_default": 1}):
            frappe.db.set_value(DOCTYPE, DEFAULT_PRESET, "is_default", 1, update_modified=False)


def guard(doc, method=None):
    """Theme records change only through the audited service below."""
    if not sec.enabled() or frappe.flags.get("in_migrate") or frappe.flags.get("in_install"):
        return
    if not frappe.flags.get("grc_service_write"):
        sec.deny()


@frappe.whitelist()
def themes():
    sec.require_admin()
    rows = frappe.get_all(DOCTYPE, fields=["name", "description", "is_default", "is_system", "modified", *COLOURS],
        order_by="is_system desc, theme_name asc")
    return {"themes": rows, "contrast_rules": [{"foreground": f, "background": b, "minimum": m, "label": w} for f, b, m, w in CONTRAST_RULES]}


@frappe.whitelist(methods=["POST"])
def save_theme(data, name=None):
    sec.require_admin()
    data = frappe.parse_json(data) if isinstance(data, str) else dict(data or {})
    colours = validate_colours(data)
    description = str(data.get("description") or "").strip()[:500]
    if name:
        if not frappe.db.exists(DOCTYPE, name):
            frappe.throw(_("This theme no longer exists."))
        doc = frappe.get_doc(DOCTYPE, name, for_update=True)
        if doc.is_system:
            frappe.throw(_("Built-in themes cannot be changed. Duplicate the theme to make your own version."))
        before = {k: doc.get(k) for k in COLOURS}
        doc.update({**colours, "description": description})
    else:
        theme_name = str(data.get("theme_name") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &()\-]{1,38}[A-Za-z0-9)]", theme_name):
            frappe.throw(_("Enter a theme name of 3 to 40 letters, digits, spaces, &, ( ) or -."))
        if frappe.db.exists(DOCTYPE, theme_name):
            frappe.throw(_("A theme with this name already exists."))
        before = None
        doc = frappe.get_doc({"doctype": DOCTYPE, "theme_name": theme_name, "description": description, "is_system": 0, **colours})
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Theme created" if before is None else "Theme changed", details={"theme": doc.name, "before": before, "after": colours})
    if name and doc.is_default:
        _bump()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def set_default_theme(name):
    sec.require_admin()
    if not frappe.db.exists(DOCTYPE, name):
        frappe.throw(_("This theme no longer exists."))
    frappe.db.sql("select name from `tabGRC Theme` order by name for update")
    previous = frappe.db.get_value(DOCTYPE, {"is_default": 1}, "name")
    with sec.service_write():
        for other in frappe.get_all(DOCTYPE, filters={"is_default": 1}, pluck="name"):
            frappe.db.set_value(DOCTYPE, other, "is_default", 0)
        frappe.db.set_value(DOCTYPE, name, "is_default", 1)
    sec.log("Default theme changed", details={"before": previous, "after": name})
    _bump()
    return tokens()


@frappe.whitelist(methods=["POST"])
def delete_theme(name):
    sec.require_admin()
    doc = frappe.get_doc(DOCTYPE, name)
    if doc.is_system or doc.is_default:
        frappe.throw(_("Built-in and default themes cannot be deleted."))
    with sec.service_write():
        frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)
    sec.log("Theme deleted", details={"theme": name})
    return {"deleted": name}


def _bump():
    """Clear cached bootstrap/public responses so every visitor gets the new colours."""
    frappe.clear_cache()
