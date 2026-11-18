"""Versioned assessments, explicit review transitions, and immutable report releases."""
import hashlib
import json
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime, today
from ia_maturity.grc import security as sec

ISSUE_FIELDS = ("issue_doctype", "issue_entity_field", "issue_opened_field", "issue_closed_field",
    "issue_lookback_months", "issue_min_sample", "closure_a_above", "closure_b_above",
    "closure_c_above", "lock_auto_answers")
DOCTYPE = "IA Maturity Assessment"


def report_identity(kind):
    from ia_maturity.grc.assessment_types import report_prefix
    prefix = report_prefix(kind)
    return prefix + "-" + now_datetime().strftime("%Y%m%d%H%M%S") + "-" + frappe.generate_hash(length=8)


def publish(name):
    from ia_maturity.scoring import get_config
    doc = frappe.get_doc("IA Maturity Template", name)
    if doc.grc_published:
        return doc
    config = dict(get_config())
    settings = frappe.get_single("IA Maturity Settings")
    config["issues"] = {key: settings.get(key) for key in ISSUE_FIELDS}
    # GRC issue calculation must never query an arbitrary ERP DocType.
    config["issues"].update(dict(issue_doctype="IA Audit Issue", issue_entity_field="entity",
        issue_opened_field="raised_on", issue_closed_field="closed_on"))
    from ia_maturity.grc.assessment_types import behaves_like_grc
    if behaves_like_grc(doc.assessment_type):
        from ia_maturity.grc.workbook import published_policy
        config = published_policy(doc)
    config["template_version"] = doc.version
    config["weighting_method"] = doc.weighting_method
    doc.grc_policy = frappe.as_json(config)
    doc.grc_published = 1
    doc.flags.grc_publishing = True
    doc.save(ignore_permissions=True)
    return doc


def validate_template(doc, method=None):
    if not sec.enabled():
        return
    # The type field is free text so new types need no schema change; validate it here.
    from ia_maturity.grc.assessment_types import validate_type
    doc.assessment_type = validate_type(doc.assessment_type or "Internal Audit")
    before = doc.get_doc_before_save()
    if not doc.is_active or not doc.grc_published or (before and before.assessment_type != doc.assessment_type):
        doc.grc_is_default = 0
    if before and before.grc_published:
        for key in ("template_name", "version", "framework", "weighting_method",
                    "introduction", "introduction_ar", "answer_rule", "answer_rule_ar",
                    "default_allow_comment", "default_allow_attachment",
                    "grc_policy", "grc_published", "grc_source_sha256", "grc_source_manifest"):
            if before.get(key) != doc.get(key):
                frappe.throw(_("Published versions are immutable. Create a new version to make changes."))
        for table in ("questions", "sections"):
            clean = lambda rows: [{k: v for k, v in row.as_dict().items()
                if k not in {"modified", "modified_by", "__islocal"}} for row in rows]
            if clean(before.get(table)) != clean(doc.get(table)):
                frappe.throw(_("Published questions and sections cannot be changed."))
    if doc.grc_published and not before and not doc.flags.get("grc_publishing"):
        frappe.throw(_("Publish this template through GRC administration."))


def freeze(doc, method=None):
    if not sec.enabled():
        return
    from ia_maturity.grc.organization_profile import guard_snapshot
    guard_snapshot(doc)
    if not doc.get("grc_assessment_type"):
        doc.grc_assessment_type = frappe.db.get_value("IA Maturity Template", doc.template, "assessment_type") or "Internal Audit"
    before = doc.get_doc_before_save()
    doc.grc_department = doc.grc_assessment_type
    if before and any(before.get(k) != doc.get(k) for k in ("grc_department", "grc_invited_sections", "grc_invitation", "grc_report_id")):
        frappe.throw(_("Assessment department, invitation and report identity cannot change."))
    if not doc.grc_policy_snapshot:
        template = frappe.get_doc("IA Maturity Template", doc.template)
        if not template.grc_published:
            frappe.throw(_("Select a published questionnaire version."))
        doc.grc_policy_snapshot = template.grc_policy
        doc.grc_sections_snapshot = frappe.as_json([row.as_dict() for row in template.sections])
    from ia_maturity.grc import scope
    scope.pin(doc)
    scope.validate_assessment(doc)
    before = doc.get_doc_before_save()
    if before and before.grc_policy_snapshot:
        if (before.grc_policy_snapshot != doc.grc_policy_snapshot or
                before.grc_sections_snapshot != doc.grc_sections_snapshot):
            frappe.throw(_("Assessment policy snapshots cannot be modified."))


def scoring_config(doc):
    from ia_maturity.scoring import get_config
    return frappe._dict(json.loads(doc.grc_policy_snapshot)) if doc.get("grc_policy_snapshot") else get_config()


def issue_settings(doc):
    if doc.get("grc_policy_snapshot"):
        return frappe._dict(json.loads(doc.grc_policy_snapshot).get("issues", {}))
    return frappe.get_cached_doc("IA Maturity Settings")


def lock_assignment(name):
    assignment = frappe.get_doc("GRC Assessment Assignment", name, for_update=True)
    sec.require_entity(assignment.entity)
    from ia_maturity.grc.departments import can_read
    if not can_read(assignment):
        sec.deny()
    return assignment


def get_assignment(doc):
    if not doc.grc_assignment:
        sec.deny()
    assignment = frappe.get_doc("GRC Assessment Assignment", doc.grc_assignment)
    if assignment.assessment != doc.name:
        # History remains readable, but edits and state transitions always use the current revision.
        frappe.throw(_("This is a previous submission. Open the current assessment."))
    return assignment


def new_assessment(entity, template=None, respondent=None, due_date=None, assessment_type=None, invitation=None):
    sec.require_entity(entity)
    respondent = respondent or frappe.session.user
    if sec.account_type() == "Customer":
        if sec.membership(entity) not in {"Organization Admin", "Contributor"}:
            sec.deny()
        if sec.membership(entity) != "Organization Admin" and respondent != frappe.session.user:
            sec.deny()
    elif not sec.can_manage_entity(entity):
        sec.deny()
    pending = sec.account_type() != "Customer" and respondent == frappe.session.user
    if not pending and sec.membership(entity, respondent) not in {"Organization Admin", "Contributor"}:
        frappe.throw(_("Select an active organization administrator or contributor as the owner."))
    from ia_maturity.grc.assessment_types import default_template
    template = template or default_template(assessment_type or "Internal Audit")
    if not template:
        frappe.throw(_("Choose an active published template. No default is configured for this assessment type."))
    published = frappe.get_doc("IA Maturity Template", template)
    if assessment_type:
        from ia_maturity.grc.assessment_types import validate_type
        if (published.assessment_type or "Internal Audit") != validate_type(assessment_type):
            frappe.throw(_("Select a template matching the assessment type."))
    if not published.grc_published or not published.is_active:
        frappe.throw(_("Select an active published questionnaire."))
    from ia_maturity.grc import departments as dept
    kind = published.assessment_type or "Internal Audit"
    dept.ensure_start(entity, kind)
    owner = frappe.db.get_value("IA Maturity Entity", entity, "grc_auditor_owner")
    if owner and (not frappe.db.get_value("User", owner, "enabled") or "Consultant" not in sec.responsibilities(entity, owner)):
        owner = None
    with sec.service_write():
        assignment = frappe.get_doc(dict(doctype="GRC Assessment Assignment", entity=entity,
            template=template, respondent=respondent, customer_pending=int(pending), grc_department=kind,
            consultant=owner or (frappe.session.user if sec.account_type() == "Auditor" and "Consultant" in sec.responsibilities(entity) else None),
            due_date=due_date or add_days(today(), cint(frappe.db.get_single_value("GRC Settings", "default_due_days")) or 14)
        )).insert(ignore_permissions=True)
        doc = frappe.get_doc(dict(doctype=DOCTYPE, entity=entity, template=template,
            respondent=respondent, grc_assignment=assignment.name, assessment_date=today(), grc_assessment_type=kind,
            grc_department=kind, grc_invitation=invitation.name if invitation else None,
            grc_invited_sections=invitation.minimum_sections if invitation else "[]",
            grc_report_id=report_identity(kind),
            language=frappe.db.get_value("User", respondent, "language") or "en"))
        doc.load_questions()
        doc.insert(ignore_permissions=True)
        assignment.assessment = doc.name
        assignment.save(ignore_permissions=True)
    sec.log("Assessment started", entity, assignment.name, doc.name, internal=False)
    return doc


def visible_results(doc, user=None):
    if sec.is_admin(user) or sec.account_type(user) == "Auditor":
        return True
    if frappe.db.exists("GRC Report Release", {"assessment": doc.name}):
        return True
    return doc.docstatus == 1 and frappe.db.get_single_value(
        "GRC Settings", "results_visibility") == "Preliminary scorecard"


def can_review(assignment, action):
    from ia_maturity.grc.departments import can_read
    if not can_read(assignment):
        return False
    if sec.is_admin():
        return True
    r = sec.responsibilities(assignment.entity)
    user = frappe.session.user
    if action in {"approve", "release"}:
        return "Reviewer" in r and assignment.reviewer == user
    return (("Consultant" in r and assignment.consultant == user)
            or ("Reviewer" in r and assignment.reviewer == user))


def _section_rows(doc):
    if doc.get("grc_sections_snapshot"):
        return frappe.parse_json(doc.grc_sections_snapshot) or []
    if doc.section_scores:
        return doc.section_scores
    if doc.template and frappe.db.exists("IA Maturity Template", doc.template):
        return frappe.get_cached_doc("IA Maturity Template", doc.template).sections
    return []


def _live_scoring(doc, policy):
    """Pinned points, bands and section weights so the questionnaire can mirror scoring.compute."""
    points = policy.get("points") or {}
    numeric = {letter: flt(points.get(letter)) for letter in ("A", "B", "C", "D")}
    bands = []
    for band in policy.get("bands") or []:
        if not band.get("level_name"):
            continue
        bands.append({
            "level_name": band.get("level_name"),
            "level_name_ar": band.get("level_name_ar") or "",
            "min_score": flt(band.get("min_score")),
            "color": band.get("color") or "",
        })
    sections = []
    from ia_maturity.grc import scope
    for row in scope.sections(doc, _section_rows(doc)):
        get = row.get
        code = get("section_code")
        if not code:
            continue
        raw_weight = get("weight")
        sections.append({"code": code, "weight": 1.0 if raw_weight in (None, "") else flt(raw_weight)})
    return {
        "points": numeric,
        "max_points": flt(policy.get("max_points")) or (max(numeric.values()) if numeric else 100),
        "weighting_method": policy.get("weighting_method") or "",
        "bands": bands,
        "sections": sections,
    }


def _section_meta(doc):
    """Section titles and references for the questionnaire, without score figures."""
    rows = _section_rows(doc)
    meta = []
    for row in rows:
        get = row.get
        code = get("section_code")
        if not code:
            continue
        meta.append({
            "code": code,
            "title": get("section_title") or code,
            "title_ar": get("section_title_ar") or "",
            "reference": get("reference") or "",
            "reference_ar": get("reference_ar") or "",
        })
    return meta


def payload(doc, detail=True):
    sec.require_assessment(doc)
    from ia_maturity.grc.organization_profile import assessment_kind, read_profile, is_complete
    assignment = frappe.get_doc("GRC Assessment Assignment", doc.grc_assignment) if doc.grc_assignment else None
    data = {key: doc.get(key) for key in (
        "name", "entity", "template", "respondent", "respondent_name", "language", "docstatus",
        "question_count", "answered_count", "modified", "amended_from", "grc_assignment")}
    data["report_id"] = doc.get("grc_report_id") or doc.name
    data["assessment_type"] = assessment_kind(doc)
    from ia_maturity.grc.assessment_types import label as type_label, requires_profile
    data["assessment_type_label"] = type_label(data["assessment_type"], doc.language)
    data["profile_required"] = bool(doc.docstatus == 0 and requires_profile(data["assessment_type"]) and not is_complete(read_profile(frappe.get_doc("IA Maturity Entity", doc.entity))))
    from ia_maturity.grc.identity import display_name
    data["respondent_name"] = display_name(doc.respondent)
    data["state"] = assignment.workflow_state if assignment else "Draft"
    data["due_date"] = assignment.due_date if assignment else None
    data["consultant"] = assignment.consultant if assignment else None
    data["reviewer"] = assignment.reviewer if assignment else None
    data["clarification"] = assignment.clarification if assignment else ""
    data["current"] = not assignment or assignment.assessment == doc.name
    from ia_maturity.grc import scope
    data["scope"] = scope.payload(doc)
    data["scope_editable"] = bool(data["current"] and sec.can_edit_assessment(doc))
    data["editable"] = bool(data["scope_editable"] and scope.ready(doc))
    data["can_assign"] = bool(sec.is_admin() or sec.is_organization_manager(doc.entity) or assignment and assignment.consultant == frappe.session.user
        and "Consultant" in sec.responsibilities(doc.entity))
    data["customer_pending"] = bool(assignment and assignment.customer_pending)
    if data["customer_pending"]:
        data["respondent_name"] = _("Awaiting customer administrator")
    data["review_actions"] = []
    if assignment and data["current"]:
        actions = {"Submitted": ["start_review"], "Resubmitted": ["start_review"],
            "Under Review": ["clarify", "approve"], "Approved": ["release"]}
        data["review_actions"] = [a for a in actions.get(assignment.workflow_state, []) if can_review(assignment, a)]
    from ia_maturity.grc import report_policy
    from ia_maturity.grc.response_policy import flags_for_answer
    released = bool(frappe.db.exists("GRC Report Release", {"assessment": doc.name}))
    data["released"] = released
    from ia_maturity.grc.color_policy import get_ranges, DEFAULT_RANGES
    frozen=frappe.db.get_value("GRC Report Release", {"assessment":doc.name}, "report_context") if released else None
    data["section_color_ranges"] = (json.loads(frozen).get("section_color_ranges") or DEFAULT_RANGES) if frozen else get_ranges()
    presentation = frappe.get_cached_doc("GRC Settings")
    data["overall_maturity_visibility"] = presentation.get("overall_maturity_visibility") or "Hidden"
    data["expand_maturity"] = bool(cint(presentation.get("expand_maturity")))
    data["expand_report"] = bool(cint(presentation.get("expand_report")))
    data["customer_score_timing"] = presentation.get("customer_score_timing") or "After all answers"
    data["customer_sections_visibility"] = presentation.get("customer_sections_visibility") or "Always expanded"
    data["results_visible"] = visible_results(doc)
    data["sections"] = [s for s in _section_meta(doc) if scope.codes(doc) is None or s["code"] in scope.codes(doc)]
    caps = report_policy.customer_capabilities(doc)
    data.update({k: caps[k] for k in (
        "allow_report_download", "allow_report_email", "report_access_timing",
        "can_download_report", "can_email_report", "report_preliminary")})
    if data["results_visible"]:
        data.update(dict(overall_score=doc.overall_score, maturity_level=doc.maturity_level,
            section_scores=[{k: s.get(k) for k in ("section_code", "section_title", "section_title_ar",
                "score_pct", "maturity_level")} for s in doc.section_scores],
            gating_note=doc.gating_note, preliminary=not released))
    if caps["can_download_report"]:
        data["pdf_url"] = "/api/method/ia_maturity.grc.api.download_report?name=" + doc.name
    if detail:
        fields = ("question_code", "section_code", "section_title", "section_title_ar", "question_text",
            "topic_code", "topic_title", "topic_title_ar", "source_ref",
            "question_text_ar", "short_label", "short_label_ar", "guidance", "guidance_ar",
            "option_a", "option_b", "option_c", "option_d", "option_a_ar", "option_b_ar",
            "option_c_ar", "option_d_ar", "allow_na", "selection_mode", "multi_score_method",
            "selected_option", "comment", "evidence",
            "auto_calculated", "auto_note", "auto_note_ar", "allow_comment", "allow_attachment")
        data["questions"] = [{k: row.get(k) for k in fields} for row in scope.answers(doc)]
        policy = scoring_config(doc)
        for row in data["questions"]:
            flags = flags_for_answer(row)
            row["allow_comment"] = flags["allow_comment"]
            row["allow_attachment"] = flags["allow_attachment"]
            row["locked"] = bool(row["auto_calculated"] and policy.get("issues", {}).get("lock_auto_answers"))
            row["evidence_deletable"] = bool(row["evidence"] and frappe.db.exists("File", {
                "file_url": row["evidence"], "attached_to_doctype": DOCTYPE, "attached_to_name": doc.name}))
        data["template_version"] = policy.get("template_version")
        if data["editable"]:
            data["scoring"] = _live_scoring(doc, policy)
            by_code = {a.question_code: a for a in doc.answers}
            for row in data["questions"]:
                src = by_code[row["question_code"]]
                row["is_gating"] = cint(src.is_gating)
                row["gate_trigger"] = src.gate_trigger or ""
                row["gate_cap_level"] = src.gate_cap_level or ""
        if data["results_visible"]:
            from ia_maturity.report_data import get_report_context
            data["report"] = (json.loads(frappe.db.get_value("GRC Report Release",
                {"assessment": doc.name}, "report_context")) if released
                else get_report_context(doc, doc.language, audience="client"))
    return data


def save(name, answers, modified=None, language=None):
    doc = frappe.get_doc(DOCTYPE, name)
    sec.require_assessment(doc, write=True)
    from ia_maturity.grc.organization_profile import require_assessment_profile
    require_assessment_profile(doc)
    assignment = lock_assignment(doc.grc_assignment)
    doc.reload()
    sec.require_assessment(doc, write=True)
    if assignment.assessment != doc.name or doc.docstatus != 0:
        frappe.throw(_("This submission is no longer editable."))
    if modified and str(doc.modified) != str(modified):
        frappe.throw(_("This assessment changed in another tab. Reload before saving."), frappe.TimestampMismatchError)
    from ia_maturity.grc import scope
    scope.require_ready(doc)
    answers = frappe.parse_json(answers) or {}
    if not isinstance(answers, dict):
        frappe.throw(_("Invalid answers."))
    rows = {a.question_code: a for a in scope.answers(doc)}
    before = {code: {k: row.get(k) or "" for k in ("selected_option", "comment", "evidence")} for code,row in rows.items()}
    old_state = assignment.workflow_state
    if set(answers) - set(rows):
        frappe.throw(_("Unknown question."))
    from ia_maturity.grc.response_policy import flags_for_answer
    config = scoring_config(doc)
    for code, values in answers.items():
        row = rows[code]
        if not isinstance(values, dict):
            frappe.throw(_("Invalid answer."))
        flags = flags_for_answer(row)
        if not (row.auto_calculated and config.get("issues", {}).get("lock_auto_answers")):
            if "selected_option" in values:
                from ia_maturity.scoring import normalize_selected
                multi = (row.selection_mode or "Single") == "Multi"
                if values.get("selected_option") is not None and not isinstance(values["selected_option"], str):
                    frappe.throw(_("Invalid answer for {0}.").format(code))
                normalized = normalize_selected(values.get("selected_option"), multi=multi)
                if values.get("selected_option") and normalized is None:
                    frappe.throw(_("Invalid answer for {0}.").format(code))
                row.selected_option = normalized or ""
        if "comment" in values:
            comment = str(values.get("comment") or "")[:5000]
            if comment and not flags["allow_comment"]:
                frappe.throw(_("Comments are disabled for question {0}.").format(code))
            if flags["allow_comment"]:
                row.comment = comment
        if "evidence" in values:
            evidence = values.get("evidence") or ""
            if evidence and not flags["allow_attachment"]:
                frappe.throw(_("Attachments are disabled for question {0}.").format(code))
            if flags["allow_attachment"]:
                if evidence:
                    validate_evidence_reference(doc, evidence)
                row.evidence = evidence
    if language in {"en", "ar"}:
        doc.language = language
    scope.lock_on_first_answer(doc)
    with sec.service_write():
        doc.save(ignore_permissions=True)
        if assignment.workflow_state in {"Draft", "In Progress"}:
            assignment.workflow_state = "In Progress"
            assignment.save(ignore_permissions=True)
    changes = []
    for row in scope.answers(doc):
        after = {k: row.get(k) or "" for k in ("selected_option", "comment", "evidence")}
        if before[row.question_code] != after:
            changes.append({"question": row.question_code, "before": before[row.question_code], "after": after})
    if changes:
        sec.log("Answers changed", doc.entity, assignment.name, doc.name,
            {"changes": changes, "on_behalf": sec.account_type() == "Auditor"}, internal=False)
    if old_state != assignment.workflow_state:
        sec.log("Status changed", doc.entity, assignment.name, doc.name,
            {"from": old_state, "to": assignment.workflow_state}, internal=False)
    return payload(doc)


def validate_evidence_reference(doc, url):
    file_name = sec.check_file_url(url)
    file = frappe.get_doc("File", file_name)
    if file.attached_to_doctype != DOCTYPE:
        sec.deny()
    source = frappe.get_doc(DOCTYPE, file.attached_to_name)
    if source.entity != doc.entity or source.grc_assignment != doc.grc_assignment:
        sec.deny()


def submit(name):
    doc = frappe.get_doc(DOCTYPE, name)
    sec.require_assessment(doc, write=True)
    assignment = lock_assignment(doc.grc_assignment)
    if assignment.assessment != doc.name or assignment.workflow_state not in {
            "Draft", "In Progress", "Clarification Required"}:
        frappe.throw(_("This assessment cannot be submitted in its current state."))
    if assignment.customer_pending:
        frappe.throw(_("Invite a customer administrator and assign a customer owner before submission."))
    from ia_maturity.grc import scope
    scope.require_ready(doc)
    for row in scope.answers(doc):
        if row.evidence:
            validate_evidence_reference(doc, row.evidence)
    with sec.service_write():
        doc.flags.ignore_permissions = True
        doc.submit()
        assignment.workflow_state = "Resubmitted" if assignment.workflow_state == "Clarification Required" else "Submitted"
        assignment.clarification = ""
        assignment.save(ignore_permissions=True)
    sec.log(assignment.workflow_state, doc.entity, assignment.name, doc.name, internal=False)
    from ia_maturity.grc.notifications import workflow_notice
    workflow_notice(assignment)
    return payload(doc)


def transition(name, action, comment=None):
    doc = frappe.get_doc(DOCTYPE, name)
    sec.require_assessment(doc)
    assignment = lock_assignment(doc.grc_assignment)
    if assignment.assessment != doc.name or not can_review(assignment, action):
        sec.deny()
    required = {"start_review": {"Submitted", "Resubmitted"}, "clarify": {"Under Review"},
        "approve": {"Under Review"}, "release": {"Approved"}}
    if action not in required or assignment.workflow_state not in required[action]:
        frappe.throw(_("Invalid workflow transition."))
    with sec.service_write():
        if action == "start_review":
            assignment.workflow_state = "Under Review"
        elif action == "clarify":
            if not comment or not comment.strip():
                frappe.throw(_("Explain what the customer needs to clarify."))
            doc.db_set("reviewer_comments", comment.strip()[:5000])
            doc.flags.ignore_permissions = True
            doc.cancel()
            amended = frappe.copy_doc(doc)
            amended.docstatus = 0
            amended.grc_report_id = report_identity(doc.grc_assessment_type or "Internal Audit")
            amended.amended_from = doc.name
            amended.review_status = ""
            amended.reviewer_comments = ""
            amended.reviewer = None
            amended.reviewed_on = None
            amended.insert(ignore_permissions=True)
            assignment.assessment = amended.name
            assignment.clarification = comment.strip()[:5000]
            assignment.workflow_state = "Clarification Required"
        elif action == "approve":
            doc.db_set({"review_status": "Approved", "reviewer": frappe.session.user,
                "reviewed_on": now_datetime(), "reviewer_comments": (comment or "")[:5000]})
            assignment.workflow_state = "Approved"
        else:
            release_report(doc)
            assignment.workflow_state = "Report Released"
        assignment.save(ignore_permissions=True)
    sec.log(assignment.workflow_state, doc.entity, assignment.name, assignment.assessment,
        {"comment": (comment or "")[:5000]} if action == "clarify" else {}, internal=False)
    if comment and action != "clarify":
        sec.log("Internal review comment", doc.entity, assignment.name, assignment.assessment,
            {"comment": comment[:5000]}, internal=True)
    from ia_maturity.grc.notifications import workflow_notice
    workflow_notice(assignment)
    return payload(frappe.get_doc(DOCTYPE, assignment.assessment))


def release_report(doc):
    if frappe.db.exists("GRC Report Release", {"assessment": doc.name}):
        frappe.throw(_("This report has already been released."))
    from ia_maturity.report_data import get_report_context
    from frappe.utils.file_manager import save_file
    context = get_report_context(doc, doc.language, audience="client")
    from ia_maturity.grc.color_policy import get_ranges
    context["section_color_ranges"] = get_ranges()
    context["release_reference_date"] = str(now_datetime())
    release = frappe.get_doc(dict(doctype="GRC Report Release", entity=doc.entity,
        assessment=doc.name, report_context=frappe.as_json(context),
        released_by=frappe.session.user, released_on=now_datetime(),
        language=doc.language)).insert(ignore_permissions=True)
    # Rendering uses the frozen release context, even if app settings subsequently change.
    from ia_maturity.grc.pdf import render
    pdf = render(context)
    from ia_maturity.grc.assessment_types import report_prefix
    prefix = report_prefix(doc.grc_assessment_type)
    file = save_file(f"{prefix}-{doc.name}.pdf", pdf, "GRC Report Release", release.name, is_private=1)
    release.pdf_file = file.name
    release.pdf_sha256 = hashlib.sha256(pdf).hexdigest()
    release.save(ignore_permissions=True)
    return release
