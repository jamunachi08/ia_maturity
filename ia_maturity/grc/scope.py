"""Versioned audit offerings and the authoritative assessment scope boundary."""
import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import now_datetime
from ia_maturity.grc import security as sec

CONFIG = "GRC Audit Scope Configuration"
SCOPE_FIELDS = ("grc_scope_snapshot", "grc_selected_packages", "grc_scope_sections",
                "grc_scope_confirmed", "grc_scope_acknowledgement", "grc_scope_confirmed_by", "grc_scope_confirmed_on")


def can_configure():
    return sec.is_admin() or (sec.account_type() == "Auditor" and "GRC Manager" in sec.roles())


def require_configure():
    sec.require_login()
    if not can_configure():
        sec.deny()


@contextmanager
def writing():
    previous = frappe.flags.get("grc_scope_write")
    frappe.flags.grc_scope_write = True
    try:
        with sec.service_write():
            yield
    finally:
        frappe.flags.grc_scope_write = previous


def guard_configuration(doc, method=None):
    if not sec.enabled() or frappe.flags.get("in_migrate") or frappe.flags.get("in_install"):
        return
    if not frappe.flags.get("grc_scope_write"):
        sec.deny()
    before = doc.get_doc_before_save()
    if before and before.published:
        frappe.throw(_("Published scope configurations are immutable. Create a new version."))


def no_delete(doc, method=None):
    if sec.enabled() and not frappe.flags.get("in_uninstall"):
        sec.deny()


def validate_configuration(template, value):
    value = frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(value, dict) or set(value) != {"required_sections", "packages"}:
        frappe.throw(_("Provide required sections and audit packages."))
    codes = {s.section_code for s in template.sections}
    question_sections = {q.section_code for q in template.questions}
    required = value["required_sections"]
    packages = value["packages"]
    if not isinstance(required, list) or any(not isinstance(c, str) or c not in codes for c in required):
        frappe.throw(_("Choose valid required sections."))
    if not isinstance(packages, list) or len(packages) > 100:
        frappe.throw(_("Provide up to 100 audit packages."))
    result, seen = [], set()
    for package in packages:
        if not isinstance(package, dict):
            frappe.throw(_("Invalid audit package."))
        code = package.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", code) or code in seen:
            frappe.throw(_("Package codes must be unique letters, numbers, underscores or hyphens."))
        seen.add(code)
        row = {"code": code}
        for field in ("label", "label_ar", "description", "description_ar"):
            text = package.get(field, "")
            if not isinstance(text, str) or len(text) > (2000 if "description" in field else 140):
                frappe.throw(_("Invalid package label or description."))
            row[field] = text.strip()
        if not row["label"] or not row["description"]:
            frappe.throw(_("Each package needs an English label and description."))
        sections = package.get("sections")
        if not isinstance(sections, list) or not sections or any(not isinstance(c, str) or c not in codes for c in sections):
            frappe.throw(_("Choose valid sections for each package."))
        if not question_sections.intersection(sections):
            frappe.throw(_("Each package must contain at least one question."))
        row["sections"] = list(dict.fromkeys(sections))
        result.append(row)
    if not result and not question_sections.intersection(required):
        frappe.throw(_("Scope must offer at least one question."))
    return {"required_sections": list(dict.fromkeys(required)), "packages": result}


@frappe.whitelist()
def scope_configurations(template=None):
    require_configure()
    templates = frappe.get_all("IA Maturity Template", filters={"grc_published": 1},
        fields=["name", "template_name", "version", "assessment_type", "modified", "is_active", "grc_is_default"], order_by="modified desc")
    if not template:
        return {"templates": templates, "configurations": []}
    doc = frappe.get_doc("IA Maturity Template", template)
    if not doc.grc_published:
        frappe.throw(_("Choose a published questionnaire version."))
    rows = frappe.get_all(CONFIG, filters={"template": template},
        fields=["name", "version", "published", "configuration", "modified"], order_by="version desc")
    for row in rows:
        row.configuration = frappe.parse_json(row.configuration)
    return {"templates": templates, "configurations": rows, "sections": [
        {"code": s.section_code, "title": s.section_title, "title_ar": s.section_title_ar,
         "question_count": sum(q.section_code == s.section_code for q in doc.questions)} for s in doc.sections]}


@frappe.whitelist(methods=["POST"])
def save_scope_configuration(template, configuration, name=None, modified=None):
    require_configure()
    frappe.db.sql("select name from `tabIA Maturity Template` where name=%s for update", template)
    questionnaire = frappe.get_doc("IA Maturity Template", template)
    if not questionnaire.grc_published:
        frappe.throw(_("Choose a published questionnaire version."))
    config = validate_configuration(questionnaire, configuration)
    if name:
        doc = frappe.get_doc(CONFIG, name, for_update=True)
        if doc.template != template or doc.published:
            frappe.throw(_("Create a new scope version to change a published configuration."))
        if not modified or str(doc.modified) != str(modified):
            frappe.throw(_("Configuration changed. Reload before saving."), frappe.TimestampMismatchError)
    else:
        version = frappe.db.sql(f"select coalesce(max(version),0)+1 from `tab{CONFIG}` where template=%s for update", template)[0][0]
        doc = frappe.get_doc({"doctype": CONFIG, "template": template, "version": version})
    doc.configuration = frappe.as_json(config)
    with writing():
        doc.save(ignore_permissions=True)
    sec.log("Audit packages saved", details={"configuration": doc.name, "version": doc.version})
    return {"name": doc.name, "modified": doc.modified}


@frappe.whitelist(methods=["POST"])
def publish_scope_configuration(name, modified):
    require_configure()
    frappe.db.sql(f"select name from `tab{CONFIG}` where name=%s for update", name)
    doc = frappe.get_doc(CONFIG, name, for_update=True)
    if str(doc.modified) != str(modified):
        frappe.throw(_("Configuration changed. Reload before publishing."), frappe.TimestampMismatchError)
    if doc.published:
        return {"name": name}
    validate_configuration(frappe.get_doc("IA Maturity Template", doc.template), doc.configuration)
    doc.published = 1
    with writing():
        doc.save(ignore_permissions=True)
    sec.log("Audit packages published", details={"configuration": name, "version": doc.version})
    return {"name": name}


def pin(doc):
    if not doc.is_new() or doc.get("grc_scope_snapshot") or doc.amended_from:
        return
    kind = doc.get("grc_assessment_type") or frappe.db.get_value("IA Maturity Template", doc.template, "assessment_type")
    from ia_maturity.grc.assessment_types import behaves_like_grc
    if not behaves_like_grc(kind):
        # IA-style types start directly. Preserve existing saved scope snapshots for history.
        return
    name = frappe.db.get_value(CONFIG, {"template": doc.template, "published": 1}, "name", order_by="version desc")
    if name:
        config = frappe.get_doc(CONFIG, name)
        doc.grc_scope_snapshot = frappe.as_json({**frappe.parse_json(config.configuration), "configuration": name, "version": config.version})
        doc.grc_scope_sections = "[]"
        doc.grc_selected_packages = "[]"
        doc.grc_scope_confirmed = 0


def validate_assessment(doc):
    before = doc.get_doc_before_save()
    if before and any(before.get(k) != doc.get(k) for k in SCOPE_FIELDS):
        if not frappe.flags.get("grc_scope_write") or before.docstatus != 0:
            frappe.throw(_("Assessment scope can only change through the scope controls."))
        if before.grc_scope_snapshot != doc.grc_scope_snapshot:
            frappe.throw(_("The assessment scope configuration is immutable."))


def codes(doc):
    """None means a legacy, all-section assessment. An empty set means no confirmed scope."""
    return set(frappe.parse_json(doc.grc_scope_sections or "[]")) if doc.get("grc_scope_snapshot") else None


def answers(doc):
    selected = codes(doc)
    return [a for a in doc.answers if selected is None or a.section_code in selected]


def sections(doc, rows):
    selected = codes(doc)
    return [s for s in rows if selected is None or s.get("section_code") in selected]


def ready(doc):
    return not doc.get("grc_scope_snapshot") or bool(doc.grc_scope_confirmed and not doc.grc_scope_acknowledgement)


def require_ready(doc):
    if not ready(doc):
        frappe.throw(_("Confirm the assessment scope before answering or submitting."))
    if doc.get("grc_scope_snapshot"):
        validate_selected_scope(doc, codes(doc))


def minimum_sections(doc):
    value = frappe.parse_json(doc.get("grc_invited_sections") or "[]")
    if not isinstance(value, list) or any(not isinstance(code, str) for code in value):
        frappe.throw(_("Invalid invited assessment sections."))
    return set(value)


def has_saved_answers(doc):
    return any(a.get("selected_option") for a in doc.answers)


def validate_selected_scope(doc, selected):
    """Invitation minima and GRC minimum coverage apply at scope save and submit."""
    selected = set(selected)
    if not minimum_sections(doc).issubset(selected):
        frappe.throw(_("Sections selected by your inviting team cannot be removed."))
    from ia_maturity.grc.assessment_types import behaves_like_grc
    if behaves_like_grc(doc.get("grc_assessment_type")) and doc.get("grc_scope_snapshot"):
        config = frappe.parse_json(doc.grc_scope_snapshot)
        required = set(config["required_sections"])
        if not required.issubset(selected) or not (selected - required):
            frappe.throw(_("Include General Maturity Awareness and at least one of Risk, Compliance or Governance."))


def lock_on_first_answer(doc):
    """Integration hook: scope is derived from persisted answer rows, not UI flags."""
    if doc.get("grc_scope_snapshot") and has_saved_answers(doc):
        require_ready(doc)


def payload(doc):
    if not doc.get("grc_scope_snapshot"):
        return None
    from ia_maturity.grc.assessment_types import behaves_like_grc
    config = frappe.parse_json(doc.grc_scope_snapshot)
    selected = codes(doc)
    rows = frappe.parse_json(doc.grc_sections_snapshot or "[]")
    return {**config, "selected_packages": frappe.parse_json(doc.grc_selected_packages or "[]"),
        "minimum_optional_sections": 1 if behaves_like_grc(doc.get("grc_assessment_type")) else 0,
        "invited_sections": sorted(minimum_sections(doc)),
        "minimum_packages": [p["code"] for p in config["packages"] if minimum_sections(doc).intersection(p["sections"])],
        "can_change": doc.docstatus == 0 and not has_saved_answers(doc) and not doc.amended_from,
        "selected_sections": sorted(selected), "confirmed": bool(doc.grc_scope_confirmed),
        "acknowledgement_required": bool(doc.grc_scope_acknowledgement),
        "confirmed_by": doc.grc_scope_confirmed_by, "confirmed_on": doc.grc_scope_confirmed_on,
        "can_correct": sec.is_admin() and doc.docstatus == 0 and not doc.amended_from,
        "sections": [{"code": s["section_code"], "title": s["section_title"], "title_ar": s.get("section_title_ar"),
            "included": s["section_code"] in selected,
            "question_count": sum(a.section_code == s["section_code"] for a in doc.answers)} for s in rows]}


def resolve(doc, packages):
    config = frappe.parse_json(doc.grc_scope_snapshot)
    packages = frappe.parse_json(packages) if isinstance(packages, str) else packages
    offered = {p["code"]: p for p in config["packages"]}
    if not isinstance(packages, list) or any(not isinstance(p, str) or p not in offered for p in packages):
        frappe.throw(_("Choose valid audit packages."))
    packages = list(dict.fromkeys(packages))
    selected = set(config["required_sections"])
    for package in packages:
        selected.update(offered[package]["sections"])
    validate_selected_scope(doc, selected)
    if not any(a.section_code in selected for a in doc.answers):
        frappe.throw(_("Choose a scope containing at least one question."))
    return packages, sorted(selected)


@frappe.whitelist(methods=["POST"])
def confirm_assessment_scope(name, packages, modified, reason=None):
    from ia_maturity.grc import assessments
    doc = frappe.get_doc(assessments.DOCTYPE, name)
    sec.require_assessment(doc, write=True)
    from ia_maturity.grc.organization_profile import require_assessment_profile
    require_assessment_profile(doc)
    assignment = assessments.lock_assignment(doc.grc_assignment)
    doc = frappe.get_doc(assessments.DOCTYPE, name, for_update=True)
    sec.require_assessment(doc, write=True)
    if doc.docstatus != 0 or assignment.assessment != name or not doc.grc_scope_snapshot or doc.amended_from:
        sec.deny()
    if str(doc.modified) != str(modified):
        frappe.throw(_("Assessment changed. Reload before changing scope."), frappe.TimestampMismatchError)
    chosen, selected = resolve(doc, packages)
    old = {"packages": frappe.parse_json(doc.grc_selected_packages or "[]"), "sections": sorted(codes(doc))}
    acknowledgement = bool(doc.grc_scope_acknowledgement and sec.account_type() == "Customer")
    correction = bool(doc.grc_scope_confirmed and not acknowledgement)
    customer_change = bool(correction and sec.account_type() == "Customer" and not has_saved_answers(doc))
    if customer_change:
        correction = False
    if not doc.grc_scope_confirmed and sec.account_type() != "Customer":
        frappe.throw(_("The customer must confirm their assessment scope."), frappe.PermissionError)
    if acknowledgement and (chosen != old["packages"] or selected != old["sections"]):
        sec.deny()
    from ia_maturity.grc.assessment_types import behaves_like_grc
    if correction and behaves_like_grc(doc.get("grc_assessment_type")) and has_saved_answers(doc):
        frappe.throw(_("Assessment sections are locked after the first saved answer."))
    if correction:
        sec.require_admin()
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            frappe.throw(_("Enter a reason for correcting the assessment scope."))
    doc.grc_selected_packages, doc.grc_scope_sections = frappe.as_json(chosen), frappe.as_json(selected)
    doc.grc_scope_confirmed = 1
    doc.grc_scope_acknowledgement = int(correction)
    doc.grc_scope_confirmed_by, doc.grc_scope_confirmed_on = frappe.session.user, now_datetime()
    with writing():
        doc.save(ignore_permissions=True)
    sec.log("Assessment scope corrected" if correction else "Assessment scope confirmed", doc.entity, assignment.name, name,
        {"before": old, "after": {"packages": chosen, "sections": selected}, "reason": reason or ""}, internal=False)
    return assessments.payload(doc)


@frappe.whitelist(methods=["POST"])
def correct_assessment_scope(name, packages, modified, reason):
    sec.require_admin()
    if not frappe.db.get_value("IA Maturity Assessment", name, "grc_scope_confirmed"):
        frappe.throw(_("The customer must confirm their assessment scope first."))
    return confirm_assessment_scope(name, packages, modified, reason)
