"""Workbook-backed organization context. This is separate from personal profiles.

Authorization always precedes profile reads/writes. Organization context is unscored;
submitted GRC assessments retain their own immutable copy.
"""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, getdate, today
from ia_maturity.grc import security as sec

CATALOG_PATH = Path(__file__).parent.parent / "setup_data" / "grc_profile_catalog.json"
FIELDS = ("organization", "industry_type", "industry_sector", "other_sector", "company_nationality",
          "cr_number", "ksa_license_type", "ksa_license_na", "other_regulator")
PREFIX = "grc_profile_"


@lru_cache(maxsize=1)
def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def regulator_names(industry, sector, nationality):
    data = catalog()
    key = industry + "|" + sector
    specific = data["sector_regulators"][key] if key in data["sector_regulators"] else data["industry_regulators"].get(industry, [])
    names = list(data["general_regulators"]) + list(specific)
    option = next((x for x in data["nationalities"] if x["name"] == nationality), {})
    if option.get("add_misa"):
        names.append("MISA (Ministry of Investment)")
    return list(dict.fromkeys(names))


def _text(value, limit=500):
    if not isinstance(value, str) or len(value) > limit:
        frappe.throw(_("Invalid company profile value."))
    return value.strip()


def validate_profile(raw, reference_date=None):
    """Validate a complete profile and return canonical values; no database writes."""
    if not isinstance(raw, dict) or set(raw) - set(FIELDS) - {"ksa_license_rows", "regulators"}:
        frappe.throw(_("Invalid company profile fields."))
    result = {key: _text(raw.get(key, "")) for key in FIELDS if key != "ksa_license_na"}
    flag = raw.get("ksa_license_na", 0)
    if flag not in (0, 1, False, True, "0", "1"):
        frappe.throw(_("Invalid company profile value."))
    result["ksa_license_na"] = cint(flag)
    if not result["organization"]:
        frappe.throw(_("Enter the organization name."))
    industries = {x["name"]: x["sectors"] for x in catalog()["industries"]}
    if result["industry_type"] not in industries:
        frappe.throw(_("Select the industry type."))
    if result["industry_sector"] not in industries[result["industry_type"]]:
        frappe.throw(_("Select the industry sector."))
    if result["industry_sector"] == "Other" and not result["other_sector"]:
        frappe.throw(_("Name the sector."))
    if result["industry_sector"] != "Other":
        result["other_sector"] = ""
    nationality = next((x for x in catalog()["nationalities"] if x["name"] == result["company_nationality"]), None)
    if not nationality:
        frappe.throw(_("Select the company nationality."))
    if not nationality["ask_cr"]:
        result["cr_number"] = ""
    elif result["cr_number"] and not re.fullmatch(r"[0-9]{10}", result["cr_number"]):
        frappe.throw(_("The CR number must be 10 digits, or leave it empty."))
    if not result["ksa_license_na"] and not result["ksa_license_type"]:
        frappe.throw(_("Enter the KSA license type, or tick N/A."))
    rows = raw.get("ksa_license_rows", [])
    if not isinstance(rows, list) or len(rows) > 100:
        frappe.throw(_("Invalid license rows."))
    result["ksa_license_rows"] = []
    # N/A rows are inactive. Save canonical rows as empty rather than leaking hidden
    # stale rows into snapshots/reports. The UI retains unsaved detail while toggling.
    if not result["ksa_license_na"]:
        for row in rows:
            if not isinstance(row, dict) or set(row) - {"license_name", "valid", "expiry_date"}:
                frappe.throw(_("Invalid license rows."))
            name = _text(row.get("license_name", ""))
            valid = _text(row.get("valid", ""))
            expiry = _text(row.get("expiry_date", ""), 10)
            if not name and not valid and not expiry:
                continue
            if not name or valid not in {"Yes", "No"} or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", expiry):
                frappe.throw(_("Complete each license row (name, valid, expiry date), or remove it."))
            try:
                date = getdate(expiry)
            except (ValueError, TypeError, frappe.ValidationError):
                frappe.throw(_("Complete each license row (name, valid, expiry date), or remove it."))
            if valid == "Yes" and date < getdate(reference_date or today()):
                frappe.throw(_("A license with a past expiry date cannot be marked valid."))
            result["ksa_license_rows"].append({"license_name": name, "valid": valid, "expiry_date": str(date)})
    if result["ksa_license_na"]:
        result["ksa_license_type"] = ""
    allowed = regulator_names(result["industry_type"], result["industry_sector"], result["company_nationality"])
    responses = raw.get("regulators", [])
    if not isinstance(responses, list) or len(responses) > 100:
        frappe.throw(_("Invalid regulator answers."))
    answers = {}
    for row in responses:
        if not isinstance(row, dict) or set(row) - {"name", "answer"}:
            frappe.throw(_("Invalid regulator answers."))
        name, answer = row.get("name"), row.get("answer", "")
        if name not in allowed or name in answers or answer not in ("", "Yes", "No"):
            frappe.throw(_("Invalid regulator answers."))
        answers[name] = answer
    result["regulators"] = [{"name": name, "answer": answers.get(name, "")} for name in allowed]
    return result


def read_profile(doc):
    value = {key: doc.get(PREFIX + key) or (doc.entity_name if key == "organization" else 0 if key == "ksa_license_na" else "") for key in FIELDS}
    value["ksa_license_rows"] = [{"license_name": r.license_name or "", "valid": r.valid or "", "expiry_date": str(r.expiry_date or "")} for r in doc.get("grc_license_rows") or []]
    if value["ksa_license_na"]:
        value["ksa_license_rows"] = []
    value["regulators"] = [{"name": r.regulator_name, "answer": r.answer or ""} for r in doc.get("grc_regulator_answers") or []]
    return value


def is_complete(profile):
    try:
        validate_profile(profile)
        return True
    except frappe.ValidationError:
        # Validation is intentionally silent on reads; do not leave hidden errors
        # in the response message queue.
        if getattr(frappe.local, "message_log", None):
            frappe.local.message_log.pop()
        return False


def _payload(doc):
    profile = read_profile(doc)
    return {"profile": profile, "modified": str(doc.modified), "can_edit": sec.can_manage_entity(doc.name), "complete": is_complete(profile)}


@frappe.whitelist()
def profile_catalog():
    sec.require_login()
    # Copy before returning; never expose the mutable process-cache object.
    data = json.loads(json.dumps(catalog()))
    data["server_today"] = today()
    from ia_maturity.grc.screen_layouts import layout_for
    data["layout"] = layout_for("Company profile")
    # Kept for older clients: the layout now decides the Yes/No style.
    data["organization_yes_no_display"] = data["layout"]["yes_no_display"]
    return data


@frappe.whitelist()
def organization_profile(entity):
    sec.require_entity(entity)
    from ia_maturity.grc.departments import can_profile
    if not can_profile(entity):
        sec.deny()
    return _payload(frappe.get_doc("IA Maturity Entity", entity))


@frappe.whitelist(methods=["POST"])
def save_organization_profile(entity, data, modified=None):
    sec.require_entity(entity, manage=True)
    from ia_maturity.grc.departments import can_profile
    if not can_profile(entity):
        sec.deny()
    raw = frappe.parse_json(data)
    value = validate_profile(raw)
    doc = frappe.get_doc("IA Maturity Entity", entity, for_update=True)
    if modified is not None and str(doc.modified) != str(modified):
        frappe.throw(_("Company profile changed. Reload before saving."), frappe.TimestampMismatchError)
    for key in FIELDS:
        doc.set(PREFIX + key, value[key])
    # Preserve previously stored rows when N/A is selected, but they remain inactive
    # and are omitted from all public profile/snapshot output below.
    if not value["ksa_license_na"]:
        doc.set("grc_license_rows", value["ksa_license_rows"])
    doc.set("grc_regulator_answers", [{"regulator_name": r["name"], "answer": r["answer"]} for r in value["regulators"]])
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Company profile updated", entity=entity, details={"fields": list(FIELDS)}, internal=False)
    return _payload(doc)


def assessment_kind(doc):
    return doc.get("grc_assessment_type") or frappe.db.get_value("IA Maturity Template", doc.template, "assessment_type") or "Internal Audit"


def require_assessment_profile(doc):
    from ia_maturity.grc.assessment_types import requires_profile
    if not requires_profile(assessment_kind(doc)):
        return None
    return validate_profile(read_profile(frappe.get_doc("IA Maturity Entity", doc.entity)))


def prepare_submission(doc):
    from ia_maturity.grc.assessment_types import requires_profile
    if not sec.enabled() or not requires_profile(assessment_kind(doc)):
        return
    value = require_assessment_profile(doc)
    doc.grc_profile_snapshot = frappe.as_json({"profile": value, "catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()})


def guard_snapshot(doc):
    before = doc.get_doc_before_save()
    if before and before.get("grc_assessment_type") and before.grc_assessment_type != doc.get("grc_assessment_type"):
        frappe.throw(_("Assessment type snapshots cannot be modified."))
    if before and before.docstatus == 1 and before.get("grc_profile_snapshot") != doc.get("grc_profile_snapshot"):
        frappe.throw(_("Submitted company profile snapshots cannot be modified."))


def backfill_assessment_types():
    if not frappe.db.has_column("IA Maturity Assessment", "grc_assessment_type"):
        return
    frappe.db.sql("""update `tabIA Maturity Assessment` a
        inner join `tabIA Maturity Template` t on t.name = a.template
        set a.grc_assessment_type = coalesce(nullif(t.assessment_type, ''), 'Internal Audit')
        where coalesce(a.grc_assessment_type, '') = ''""")
