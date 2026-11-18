"""GRC app administration, available inside the auditor dashboard only."""
import frappe
from frappe import _
from frappe.utils import cint, getdate
from ia_maturity.grc import security as sec
from ia_maturity.grc import assessments as service

SETTINGS_FIELDS = ("overall_maturity_visibility","customer_score_timing", "customer_sections_visibility", "question_extras_enabled", "expand_maturity", "expand_report", "results_visibility", "allow_report_download", "allow_report_email",
    "report_access_timing", "reminders_enabled", "reminder_days", "default_due_days",
    "scoring_owner_approved", "content_approved", "production_hostname", "framework_version",
    "privacy_en", "privacy_ar", "terms_en", "terms_ar", "profile_editable_fields",
    "signup_email_policy", "signup_allowed_domains", "organization_yes_no_display",
    "new_user_page_tour_default", "new_user_help_default")
SCORING_FIELDS = ("points_a", "points_b", "points_c", "points_d", "create_actions_for", "evidence_required_from",
    "issue_lookback_months", "issue_min_sample", "closure_a_above", "closure_b_above", "closure_c_above", "lock_auto_answers")


@frappe.whitelist()
def staff(entity=None):
    if entity:
        sec.require_entity(entity)
        if not (sec.is_admin() or sec.is_organization_manager(entity)):
            sec.deny()
    else:
        sec.require_admin()
    people = frappe.get_all("User", filters={"grc_account_type": "Auditor"},
        fields=["name", "full_name", "enabled"], order_by="full_name")
    from ia_maturity.grc.identity import display_name
    from ia_maturity.grc import departments as dept
    if not sec.is_admin():
        permitted_departments = dept.staff_types() & dept.entity_types(entity)
        people = [p for p in people if dept.staff_types(p.name) & permitted_departments]
    for person in people:
        person["full_name"] = display_name(person.name)
        person["grc_roles"] = sorted(sec.roles(person.name) & {"GRC Auditor", "GRC Consultant", "GRC Reviewer", "GRC Manager", "GRC App Admin"})
    return people


@frappe.whitelist(methods=["POST"])
def save_staff(email, full_name, role="GRC Auditor", enabled=1):
    sec.require_admin()
    if role not in {"GRC Auditor", "GRC Consultant", "GRC Reviewer", "GRC Manager", "GRC App Admin"}:
        sec.deny()
    from ia_maturity.grc.identity import validate_name
    validate_name(full_name.strip(), required=True)
    email = email.strip().lower()
    if frappe.db.exists("User", email) and sec.account_type(email) != "Auditor":
        frappe.throw(_("Create a separate GRC staff account instead of converting an ERP or customer account."))
    if email == frappe.session.user and (not cint(enabled) or role != "GRC App Admin"):
        frappe.throw(_("Keep your own administrator access active."))
    from ia_maturity.grc.operations import maybe_queue
    if not frappe.db.exists("User",email):
        from frappe.utils import validate_email_address
        if not validate_email_address(email):frappe.throw(_("Enter a valid email address."))
        queued=maybe_queue('Auditor Onboarding',{'email':email,'full_name':full_name,'role':role,'enabled':cint(enabled)})
        if queued:return queued
    doc = frappe.get_doc("User", email) if frappe.db.exists("User", email) else frappe.new_doc("User")
    first, _sep, last = full_name.strip().partition(" ")
    doc.update(dict(email=email, first_name=first, last_name=last, enabled=cint(enabled),
        user_type="System User", grc_account_type="Auditor", send_welcome_email=0))
    doc.set("roles", [{"role": role}])
    doc.flags.no_welcome_mail = True
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("GRC staff updated", details={"user": doc.name, "role": role, "enabled": doc.enabled})
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def assign_customer(entity, auditor, responsibility="Consultant", active=1):
    sec.require_entity(entity)
    if not (sec.is_admin() or sec.is_organization_manager(entity)):
        sec.deny()
    if responsibility not in {"Manager", "Consultant", "Reviewer"} or sec.account_type(auditor) != "Auditor":
        sec.deny()
    if responsibility == "Manager" and not sec.is_admin():
        sec.deny()
    if not frappe.db.exists("IA Maturity Entity", entity):
        sec.deny()
    from ia_maturity.grc import departments as dept
    shared = dept.staff_types(auditor) & dept.entity_types(entity)
    if not shared or not sec.is_admin() and not (shared & dept.staff_types()):
        sec.deny()
    from ia_maturity.grc.operations import maybe_queue
    previous=frappe.db.get_value("Auditor Customer Assignment",{'entity':entity,'auditor':auditor,'responsibility':responsibility},['name','active'],as_dict=True)
    queued=maybe_queue('Customer Assignment',{'entity':entity,'auditor':auditor,'responsibility':responsibility,'active':cint(active),'_before':dict(previous) if previous else None},entity)
    if queued:return queued
    name = frappe.db.get_value("Auditor Customer Assignment",
        {"entity": entity, "auditor": auditor, "responsibility": responsibility}, "name")
    doc = frappe.get_doc("Auditor Customer Assignment", name) if name else frappe.new_doc("Auditor Customer Assignment")
    doc.update(dict(entity=entity, auditor=auditor, responsibility=responsibility, active=cint(active)))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    return {"name": doc.name, "active": doc.active}


@frappe.whitelist(methods=["POST"])
def assign_assessment(name, consultant=None, reviewer=None, due_date=None, review_due_date=None, respondent=None, reason=None):
    doc = service.lock_assignment(name)
    if not (sec.is_admin() or sec.is_organization_manager(doc.entity) or doc.consultant == frappe.session.user and "Consultant" in sec.responsibilities(doc.entity)):
        sec.deny()
    from ia_maturity.grc import departments as dept
    department = dept.kind(doc)
    for staff_user in (consultant, reviewer):
        if staff_user and department not in dept.staff_types(staff_user):
            sec.deny()
    before = {k: doc.get(k) for k in ("consultant", "reviewer", "respondent", "due_date", "review_due_date")}
    transfer = any(before[k] and (v or None) != before[k] for k,v in (("consultant", consultant), ("reviewer", reviewer)))
    transfer = transfer or bool(respondent and respondent != doc.respondent)
    if transfer and (not isinstance(reason, str) or not reason.strip()):
        frappe.throw(_("Enter a reason for the ownership transfer."))
    if reason and len(reason) > 2000:
        frappe.throw(_("Use a transfer reason of up to 2000 characters."))
    for value, responsibility in ((consultant, "Consultant"), (reviewer, "Reviewer")):
        if value and responsibility not in sec.responsibilities(doc.entity, value):
            frappe.throw(_("Assign the customer to this auditor with the required responsibility first."))
    from ia_maturity.grc.operations import maybe_queue
    queued=maybe_queue('Assessment Assignment',{'name':name,'consultant':consultant,'reviewer':reviewer,'due_date':due_date,'review_due_date':review_due_date,'respondent':respondent,'reason':reason,'_before':{k:str(before[k] or '') for k in before}},doc.entity)
    if queued:return queued
    if respondent and respondent != doc.respondent:
        if doc.workflow_state not in {"Draft", "In Progress"}:
            frappe.throw(_("The customer owner can only be changed before submission."))
        if sec.membership(doc.entity, respondent) not in {"Organization Admin", "Contributor"}:
            sec.deny()
        doc.respondent = respondent
        doc.customer_pending = 0
        frappe.db.set_value("IA Maturity Assessment", doc.assessment, {
            "respondent": respondent, "respondent_name": "", "respondent_email": ""})
    doc.consultant, doc.reviewer = consultant or None, reviewer or None
    if due_date:
        doc.due_date = getdate(due_date)
    if review_due_date:
        doc.review_due_date = getdate(review_due_date)
    doc.needs_reassignment = int(not reviewer)
    with sec.service_write():
        doc.save(ignore_permissions=True)
    after = {k: doc.get(k) for k in before}
    if before != after:
        sec.log("Assessment transferred" if transfer else "Assessment team allocated", doc.entity, doc.name, doc.assessment,
            {"before": before, "after": after, "reason": (reason or "").strip()}, internal=True)
        sec.log("Assessment team updated", doc.entity, doc.name, doc.assessment, internal=False)
    return {"name": doc.name}


def _template_scoring(doc):
    """Points/bands for admin editor preview. Published versions use pinned policy."""
    from ia_maturity.scoring import get_config
    if cint(doc.get("grc_published")) and doc.get("grc_policy"):
        policy = frappe._dict(frappe.parse_json(doc.grc_policy))
    else:
        policy = get_config()
        policy["weighting_method"] = doc.get("weighting_method") or policy.get("weighting_method") or ""
    points = policy.get("points") or {}
    numeric = {letter: float(points.get(letter) or 0) for letter in ("A", "B", "C", "D")}
    bands = []
    for band in policy.get("bands") or []:
        if not band.get("level_name"):
            continue
        bands.append({
            "level_name": band.get("level_name"),
            "level_name_ar": band.get("level_name_ar") or "",
            "min_score": float(band.get("min_score") or 0),
            "color": band.get("color") or "",
        })
    sections = []
    for row in doc.get("sections") or []:
        code = row.get("section_code") if isinstance(row, dict) else row.section_code
        if not code:
            continue
        weight = row.get("weight") if isinstance(row, dict) else row.weight
        sections.append({"code": code, "weight": 1.0 if weight in (None, "") else float(weight)})
    return {
        "points": numeric,
        "max_points": float(policy.get("max_points") or (max(numeric.values()) if numeric else 100)),
        "weighting_method": policy.get("weighting_method") or doc.get("weighting_method") or "",
        "bands": bands,
        "sections": sections,
    }


@frappe.whitelist()
def templates(name=None, assessment_type=None, management=0):
    sec.require_login()
    if name:
        if not sec.is_admin():
            sec.deny()
        doc = frappe.get_doc("IA Maturity Template", name)
        data = doc.as_dict()
        data["is_default"] = bool(doc.grc_is_default and doc.is_active and doc.grc_published)
        data["scoring"] = _template_scoring(data)
        data["question_count"] = len(doc.questions or [])
        data["section_count"] = len(doc.sections or [])
        return data
    if cint(management):
        sec.require_admin()
    filters = {} if cint(management) else {"grc_published": 1, "is_active": 1}
    if assessment_type:
        from ia_maturity.grc.assessment_types import validate_type
        filters["assessment_type"] = validate_type(assessment_type)
    rows = frappe.get_all("IA Maturity Template", filters=filters,
        fields=["name", "template_name", "version", "framework", "is_active", "grc_published",
                "introduction", "introduction_ar", "modified", "assessment_type", "grc_is_default"], order_by="modified desc")
    if sec.is_admin() and rows:
        counts = frappe.db.sql("""
            select parent, count(*) as n from `tabIA Maturity Template Question`
            where parent in (%s) group by parent
        """ % ", ".join(["%s"] * len(rows)), tuple(r.name for r in rows), as_dict=True)
        by_parent = {c.parent: c.n for c in counts}
        for row in rows:
            row["question_count"] = by_parent.get(row.name, 0)
    from ia_maturity.grc.departments import allowed_types
    if not sec.is_admin():
        allowed = allowed_types()
        rows = [r for r in rows if r.assessment_type in allowed]
    for row in rows:
        row["is_default"] = bool(row.grc_is_default and row.is_active and row.grc_published)
    return sorted(rows, key=lambda row: not row["is_default"])


@frappe.whitelist(methods=["POST"])
def save_template(data, name=None, clone=0):
    sec.require_admin()
    data = frappe.parse_json(data) or {}
    if name:
        original = frappe.get_doc("IA Maturity Template", name)
        if cint(clone):
            doc = frappe.copy_doc(original)
            doc.grc_published, doc.grc_policy = 0, ""
            doc.grc_default_revision = int(bool(original.grc_is_default))
            if doc.grc_default_revision:
                doc.default_allow_comment = doc.default_allow_attachment = 0
            doc.version = cint(original.version) + 1
            doc.template_name = data.get("template_name") or f"{original.template_name} v{doc.version}"
        else:
            doc = original
    else:
        doc = frappe.new_doc("IA Maturity Template")
    for key in ("template_name", "version", "framework", "weighting_method", "is_active",
                "introduction", "introduction_ar", "answer_rule", "answer_rule_ar",
                "default_allow_comment", "default_allow_attachment"):
        if key in data:
            doc.set(key, data[key])
    for table, child in (("sections", "IA Maturity Template Section"), ("questions", "IA Maturity Template Question")):
        if table in data:
            allowed = {f.fieldname for f in frappe.get_meta(child).fields}
            doc.set(table, [{k: v for k, v in row.items() if k in allowed} for row in data[table]])
    if not doc.sections or not doc.questions:
        frappe.throw(_("Add at least one section and question."))
    with sec.service_write():
        doc.save(ignore_permissions=True)
    sec.log("Questionnaire version saved", details={"template": doc.name, "version": doc.version})
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def publish_template(name, make_default=0):
    sec.require_admin()
    from ia_maturity.grc.assessment_types import lock_defaults, make_type_default
    lock_defaults()
    with sec.service_write():
        doc = service.publish(name)
        if cint(make_default):
            if not doc.is_active:
                frappe.throw(_("The default questionnaire must be active."))
            make_type_default(doc)
    sec.log("Questionnaire published", details={"template": doc.name, "version": doc.version})
    return {"name": doc.name}


@frappe.whitelist()
def settings():
    sec.require_admin()
    doc = frappe.get_single("GRC Settings")
    legacy = frappe.get_single("IA Maturity Settings")
    data = {k: doc.get(k) for k in SETTINGS_FIELDS}
    # Preserve legacy behavior when new report fields are unset on older sites.
    if data.get("allow_report_download") in (None, ""):
        data["allow_report_download"] = 1
    if data.get("allow_report_email") in (None, ""):
        data["allow_report_email"] = 1
    if not data.get("report_access_timing"):
        data["report_access_timing"] = "After Audit"
    data["organization_yes_no_display"] = data.get("organization_yes_no_display") or "Dropdown"
    for field in ("new_user_page_tour_default", "new_user_help_default"):
        data[field] = data.get(field) or "Enabled"
    from ia_maturity.grc.profile import editable_fields, field_catalog
    data["profile_editable_fields"] = editable_fields()
    data["profile_fields"] = field_catalog()
    data["scoring"] = {k: legacy.get(k) for k in SCORING_FIELDS}
    data["delivery"] = frappe.get_all("GRC Reminder Delivery",
        fields=["name", "entity", "recipient", "subject", "status", "creation", "error"],
        order_by="creation desc", limit_page_length=50)
    return data


@frappe.whitelist(methods=["POST"])
def save_settings(data):
    sec.require_admin()
    data = frappe.parse_json(data) or {}
    doc = frappe.get_single("GRC Settings")
    for field, allowed in {
        "customer_score_timing": {"After all answers", "During assessment", "After submission"},
        "customer_sections_visibility": {"Collapsed until complete", "Always collapsed", "Always expanded", "Hidden"},
        "organization_yes_no_display": {"Dropdown", "Buttons"},
        "new_user_page_tour_default": {"Enabled", "Disabled"},
        "new_user_help_default": {"Enabled", "Disabled"},
    }.items():
        if field in data and data[field] not in allowed:
            frappe.throw(_("Invalid assessment visibility setting."))
    if "profile_editable_fields" in data:
        from ia_maturity.grc.profile import validate_policy
        data["profile_editable_fields"] = frappe.as_json(validate_policy(data["profile_editable_fields"]))
    for key in SETTINGS_FIELDS:
        # Legal copy is published only through the site-content approval workflow.
        if key in {"privacy_en", "privacy_ar", "terms_en", "terms_ar"}:
            continue
        if key in data:
            value = data[key]
            if key in {"allow_report_download", "allow_report_email"}:
                value = cint(value)
            doc.set(key, value)
    with sec.service_write():
        doc.save(ignore_permissions=True)
        if "scoring" in data:
            legacy = frappe.get_single("IA Maturity Settings")
            for key in SCORING_FIELDS:
                if key in data["scoring"]:
                    legacy.set(key, data["scoring"][key])
            points = [float(legacy.get("points_" + c) or 0) for c in "abcd"]
            if not (0 <= points[0] < points[1] < points[2] < points[3] <= 100):
                frappe.throw(_("Scoring points must increase from A through D, within 0–100."))
            legacy.save(ignore_permissions=True)
            sec.log("Scoring defaults changed", details={"affects": "Future published versions only"})
    return settings()


@frappe.whitelist()
def consultations():
    sec.require_admin()
    return frappe.get_all("GRC Consultation Request", fields=["name", "full_name", "email",
        "organization", "service", "message", "status", "creation"], order_by="creation desc", limit_page_length=100)


@frappe.whitelist(methods=["POST"])
def update_consultation(name, status):
    sec.require_admin()
    if status not in {"New", "Contacted", "Closed"}:
        sec.deny()
    doc = frappe.get_doc("GRC Consultation Request", name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"name": name, "status": status}
