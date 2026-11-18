"""Assessment types: the configurable master (GRC Department) plus template classification.

Each assessment type is a GRC Department record. Its base behaviour decides which
built-in rules apply, so new types reuse proven Internal Audit or GRC handling:

  Internal Audit behaviour: starts directly, issue-register answers may be calculated.
  GRC behaviour:            scope/section choice, self-reported answers, workbook policy.

The company-profile requirement is a separate per-type switch.
"""
import re

import frappe
from frappe import _
from frappe.utils import cint

from ia_maturity.grc import security as sec
from ia_maturity.grc.read_cache import read_cached

IA, GRC = "Internal Audit", "GRC"
BEHAVIOURS = (IA, GRC)
ICONS = ("clipboard", "shield", "scale", "building", "chart", "briefcase", "leaf", "lock")
BUILTIN = {
    IA: {
        "label": "Internal Audit", "label_ar": "التدقيق الداخلي",
        "description": "Assess your internal audit function, governance, people, methodology and reporting.",
        "description_ar": "قيّم وظيفة التدقيق الداخلي والحوكمة والموارد البشرية والمنهجية والتقارير.",
        "behaviour": IA, "requires_company_profile": 0, "icon": "clipboard", "sort_order": 10, "report_prefix": "IA",
    },
    GRC: {
        "label": "Governance, Risk and Compliance", "label_ar": "الحوكمة والمخاطر والامتثال",
        "description": "Assess your governance, risk management and compliance practices.",
        "description_ar": "قيّم ممارسات الحوكمة وإدارة المخاطر والامتثال.",
        "behaviour": GRC, "requires_company_profile": 1, "icon": "shield", "sort_order": 20, "report_prefix": "GRC",
    },
}
FIELDS = ("label", "label_ar", "description", "description_ar", "behaviour", "requires_company_profile",
          "icon", "sort_order", "report_prefix", "active", "is_system")


def _has_type_columns():
    return frappe.db.table_exists("GRC Department") and frappe.db.has_column("GRC Department", "behaviour")


@read_cached
def type_rows():
    """All assessment types (active and inactive), ordered for display."""
    if not _has_type_columns():
        return [{"name": name, "active": 1, "is_system": 1, **values} for name, values in BUILTIN.items()]
    rows = frappe.get_all("GRC Department", fields=["name", *FIELDS], order_by="sort_order asc, creation asc")
    for row in rows:
        builtin = BUILTIN.get(row.name, {})
        for key in ("label", "label_ar", "description", "description_ar", "icon"):
            row[key] = row.get(key) or builtin.get(key) or (row.name if key == "label" else "")
        row["behaviour"] = row.get("behaviour") if row.get("behaviour") in BEHAVIOURS else builtin.get("behaviour", IA)
    return [dict(row) for row in rows]


def type_names(active_only=False):
    return [row["name"] for row in type_rows() if row.get("active") or not active_only]


def type_row(kind):
    return next((row for row in type_rows() if row["name"] == kind), BUILTIN.get(kind and str(kind)) and {"name": kind, **BUILTIN[kind]})


def behaviour(kind):
    """Base behaviour of an assessment type; unknown or empty values behave as Internal Audit."""
    row = type_row(kind or IA)
    return (row or {}).get("behaviour") or IA


def behaves_like_grc(kind):
    return behaviour(kind) == GRC


def requires_profile(kind):
    row = type_row(kind or IA)
    return bool(row and cint(row.get("requires_company_profile")))


def report_prefix(kind):
    row = type_row(kind or IA)
    return (row or {}).get("report_prefix") or ("GRC" if behaves_like_grc(kind) else "IA")


def label(kind, language="en"):
    row = type_row(kind) or {}
    return (row.get("label_ar") if language == "ar" else None) or row.get("label") or kind


def public_types():
    """Active types for the portal, without internal fields."""
    keep = ("name", "label", "label_ar", "description", "description_ar", "behaviour",
            "requires_company_profile", "icon", "sort_order")
    return [{key: row.get(key) for key in keep} for row in type_rows() if row.get("active")]


def validate_type(value):
    """A known assessment type. Inactive types are rejected by departments.validate_type for new work."""
    if not isinstance(value, str) or value not in type_names():
        frappe.throw(_("Choose a valid assessment type."))
    return value


# ---------------------------------------------------------------------------------------------
# Administration (GRC App Admin only; every change is audited)


@frappe.whitelist()
def assessment_types_admin():
    sec.require_admin()
    usage = _usage()
    return {"types": [{**row, "templates": usage.get(row["name"], 0)} for row in type_rows()],
            "behaviours": list(BEHAVIOURS), "icons": list(ICONS)}


def _usage():
    counts = {}
    for name in frappe.get_all("IA Maturity Template", pluck="assessment_type"):
        counts[name or IA] = counts.get(name or IA, 0) + 1
    return counts


def _clean(data, existing=None):
    data = frappe.parse_json(data) if isinstance(data, str) else dict(data or {})
    out = {}
    for key in ("label", "label_ar", "description", "description_ar"):
        value = str(data.get(key) or "").strip()
        if len(value) > (140 if key.startswith("label") else 500):
            frappe.throw(_("Text is too long."))
        out[key] = value
    if not out["label"]:
        frappe.throw(_("Enter a label."))
    out["behaviour"] = data.get("behaviour") or (existing or {}).get("behaviour") or IA
    if out["behaviour"] not in BEHAVIOURS:
        frappe.throw(_("Choose a valid base behaviour."))
    out["icon"] = data.get("icon") or "clipboard"
    if out["icon"] not in ICONS:
        frappe.throw(_("Choose a valid icon."))
    prefix = str(data.get("report_prefix") or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,8}", prefix):
        frappe.throw(_("The report prefix must be 2 to 8 letters or digits."))
    out["report_prefix"] = prefix
    out["requires_company_profile"] = 1 if cint(data.get("requires_company_profile")) else 0
    out["sort_order"] = max(0, min(9999, cint(data.get("sort_order") or 10)))
    out["active"] = 1 if cint(data.get("active", 1)) else 0
    return out


@frappe.whitelist(methods=["POST"])
def save_assessment_type(data, name=None):
    sec.require_admin()
    raw = frappe.parse_json(data) if isinstance(data, str) else dict(data or {})
    if name:
        if not frappe.db.exists("GRC Department", name):
            frappe.throw(_("This assessment type no longer exists."))
        doc = frappe.get_doc("GRC Department", name, for_update=True)
        before = {key: doc.get(key) for key in FIELDS}
        values = _clean(raw, before)
        if doc.is_system and values["behaviour"] != (doc.behaviour or BUILTIN[name]["behaviour"]):
            frappe.throw(_("The base behaviour of a built-in assessment type cannot change."))
        if not values["active"] and doc.active and _usage().get(name) and name in (IA, GRC):
            frappe.throw(_("Built-in assessment types stay active while questionnaires use them."))
        doc.update(values)
    else:
        code = str(raw.get("name") or raw.get("department_name") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &()\-]{1,58}[A-Za-z0-9)]", code):
            frappe.throw(_("Enter a type name of 3 to 60 letters, digits, spaces, &, ( ) or -."))
        if frappe.db.exists("GRC Department", code):
            frappe.throw(_("An assessment type with this name already exists."))
        before = None
        doc = frappe.new_doc("GRC Department")
        doc.update({"department_name": code, **_clean(raw), "is_system": 0})
    with sec.service_write():
        doc.save(ignore_permissions=True)
    after = {key: doc.get(key) for key in FIELDS}
    sec.log("Assessment type created" if before is None else "Assessment type changed",
        details={"type": doc.name, "before": before, "after": after})
    from ia_maturity.grc.read_cache import invalidate
    invalidate()
    return {"name": doc.name}


# ---------------------------------------------------------------------------------------------
# Template classification (unchanged behaviour, now against the configurable list)


@frappe.whitelist(methods=["POST"])
def set_template_type(name, assessment_type, modified, is_active=None, make_default=0):
    from ia_maturity.grc.scope import require_configure
    require_configure()
    value = validate_type(assessment_type)
    lock_defaults()
    doc = frappe.get_doc("IA Maturity Template", name, for_update=True)
    if str(doc.modified) != str(modified):
        frappe.throw(_("Template changed. Reload before saving."), frappe.TimestampMismatchError)
    before = {"assessment_type": doc.assessment_type or IA, "is_active": doc.is_active, "is_default": doc.grc_is_default}
    doc.assessment_type = value
    if is_active is not None:
        if str(is_active) not in ("0", "1"):
            frappe.throw(_("Choose a valid template status."))
        doc.is_active = int(is_active)
    doc.save(ignore_permissions=True)
    if cint(make_default):
        make_type_default(doc)
    sec.log("Template settings changed", details={"template": name, "before": before, "after": {"assessment_type": value, "is_active": doc.is_active, "is_default": doc.grc_is_default}})
    return {"name": name, "assessment_type": value}


def lock_defaults():
    # A consistent lock order serializes default changes across types and templates.
    frappe.db.sql("select name from `tabIA Maturity Template` order by name for update")


def default_template(assessment_type=IA):
    return frappe.db.get_value("IA Maturity Template", {
        "assessment_type": validate_type(assessment_type), "grc_is_default": 1,
        "is_active": 1, "grc_published": 1,
    }, "name")


def make_type_default(doc):
    lock_defaults()
    doc.reload()
    if not doc.is_active or not doc.grc_published:
        frappe.throw(_("The default questionnaire must be active and published."))
    kind = validate_type(doc.assessment_type or IA)
    previous = default_template(kind)
    for name in frappe.get_all("IA Maturity Template", filters={"assessment_type": kind, "grc_is_default": 1}, pluck="name"):
        frappe.db.set_value("IA Maturity Template", name, "grc_is_default", 0)
    frappe.db.set_value("IA Maturity Template", doc.name, "grc_is_default", 1)
    doc.reload()
    sec.log("Default template changed", details={"assessment_type": kind, "before": previous, "after": doc.name})
