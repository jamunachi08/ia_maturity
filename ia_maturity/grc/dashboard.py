"""Bounded dashboard reads using the same live GRC authorization predicates.

Only the requested assignment page is materialized. Counts and previews use
database predicates rather than loading every assignment, action and event.
There is deliberately no cross-request authorization or response cache here.
"""
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, get_system_timezone, today

from ia_maturity.grc import assessments as service, departments as dept, security as sec
from ia_maturity.grc.read_cache import read_request


ASSIGNMENTS = "`tabGRC Assessment Assignment`"
ASSESSMENTS = "`tabIA Maturity Assessment`"
GRANTS = "`tabGRC Department Grant`"
TEMPLATES = "`tabIA Maturity Template`"
RELEASES = "`tabGRC Report Release`"
BROAD_MEMBERSHIPS = {"Organization Admin", "Viewer", "Holding Viewer"}
MILESTONES = ("Assessment started", "Submitted", "Resubmitted")


class ReadScope:
    """A fresh, caller-owned authorization snapshot for one read operation."""

    def __init__(self, entity=None):
        sec.require_login()
        self.user = frappe.session.user
        self.kind = sec.account_type()
        self.admin = sec.is_admin()
        self.all_entities = tuple(sec.entities())
        if entity:
            sec.require_entity(entity)
        self.entities = (entity,) if entity else self.all_entities
        self.broad = tuple(e for e in self.all_entities if self.kind == "Customer"
            and sec.effective_membership(e) in BROAD_MEMBERSHIPS)
        self.staff_types = tuple(dept.staff_types()) if self.kind == "Auditor" and not self.admin else ()
        self.preliminary = frappe.db.get_single_value("GRC Settings", "results_visibility") == "Preliminary scorecard"

    @staticmethod
    def in_values(column, values, params):
        if not values:
            return "0=1"
        params.extend(values)
        return f"{column} IN ({','.join(['%s'] * len(values))})"

    def entity_condition(self, alias, params, selected=True):
        return self.in_values(f"{alias}.entity", self.entities if selected else self.all_entities, params)

    def department_condition(self, alias, department, params):
        if self.admin:
            return "1=1"
        grant = (f"EXISTS (SELECT 1 FROM {GRANTS} g WHERE g.entity={alias}.entity "
            f"AND g.active=1 AND g.department={department}")
        if self.kind == "Auditor":
            allowed_type = self.in_values(department, self.staff_types, params)
            return f"({allowed_type} AND {grant} AND g.profile_access=1))"
        # Customer/ERP dept.can_read permits an unstamped row only when the
        # legacy fallback cannot derive a department; a derived type needs a grant.
        return f"({department} IS NULL OR {grant}))"

    def customer_condition(self, alias, params):
        if self.kind != "Customer":
            return "1=1"
        broad = self.in_values(f"{alias}.entity", self.broad, params)
        params.append(self.user)
        return f"({broad} OR {alias}.respondent=%s)"

    def assessment_condition(self, alias, params):
        if self.admin:
            return f"{alias}.name IS NOT NULL"
        clauses = [f"{alias}.name IS NOT NULL", self.entity_condition(alias, params, selected=False),
            self.department_condition(alias, _department(alias, "assessment"), params),
            self.customer_condition(alias, params)]
        return " AND ".join(f"({clause})" for clause in clauses)

    def results_condition(self, alias):
        if self.admin or self.kind == "Auditor":
            return "1=1"
        released = f"EXISTS (SELECT 1 FROM {RELEASES} r WHERE r.assessment={alias}.name)"
        return f"({released} OR {alias}.docstatus=1)" if self.preliminary else released


def _department(alias, category):
    """SQL form of departments.kind, including legacy unstamped-row fallback."""
    single = (f"(SELECT MIN(g0.department) FROM {GRANTS} g0 WHERE g0.entity={alias}.entity "
        "AND g0.active=1 HAVING COUNT(DISTINCT g0.department)=1)")
    if category == "assessment":
        fallback = (f"CASE WHEN COALESCE({alias}.template,'')<>'' THEN "
            f"COALESCE((SELECT NULLIF(t0.assessment_type,'') FROM {TEMPLATES} t0 "
            f"WHERE t0.name={alias}.template),'Internal Audit') ELSE {single} END")
        return f"COALESCE(NULLIF({alias}.grc_department,''),NULLIF({alias}.grc_assessment_type,''),{fallback})"
    template_fallback = (f"WHEN COALESCE({alias}.template,'')<>'' THEN "
        f"COALESCE((SELECT NULLIF(t0.assessment_type,'') FROM {TEMPLATES} t0 "
        f"WHERE t0.name={alias}.template),'Internal Audit') ") if category == "assignment" else ""
    fallback = (f"CASE WHEN COALESCE({alias}.assessment,'')<>'' THEN "
        f"COALESCE((SELECT NULLIF(s0.grc_assessment_type,'') FROM {ASSESSMENTS} s0 "
        f"WHERE s0.name={alias}.assessment),'Internal Audit') {template_fallback}ELSE {single} END")
    return f"COALESCE(NULLIF({alias}.grc_department,''),{fallback})"


@read_request
def dashboard(entity=None, search=None, state=None, page=1, scorecards=0, group=None):
    scope = ReadScope(entity)
    params = []
    base = [scope.entity_condition("a", params),
        scope.department_condition("a", _department("a", "assignment"), params),
        scope.customer_condition("a", params)]
    base_sql = " AND ".join(f"({clause})" for clause in base)
    summary = frappe.db.sql(f"""SELECT a.workflow_state, COUNT(*) AS count,
        SUM(CASE WHEN a.due_date<%s AND a.workflow_state<>'Report Released' THEN 1 ELSE 0 END) AS overdue
        FROM {ASSIGNMENTS} a WHERE {base_sql} GROUP BY a.workflow_state""",
        [today(), *params], as_dict=True)
    counts = {row.workflow_state: cint(row.count) for row in summary}
    overdue = sum(cint(row.overdue) for row in summary)
    filtered, filtered_params = list(base), list(params)
    if search:
        # Binary substring comparison preserves literal '%'/'_' search behavior.
        filtered.append("LOCATE(BINARY %s, BINARY LOWER(CONCAT(a.entity,' ',COALESCE(a.assessment,''),' ',a.template)))>0")
        filtered_params.append(search.lower().strip())
    if state:
        filtered.append("a.workflow_state=%s")
        filtered_params.append(state)
    groups = {"in_progress": ("Draft", "In Progress"),
        "awaiting_review": ("Submitted", "Resubmitted", "Under Review"), "released": ("Report Released",)}
    if group == "overdue":
        filtered.append("a.due_date<%s AND a.workflow_state<>'Report Released'")
        filtered_params.append(today())
    elif group in groups:
        filtered.append(scope.in_values("a.workflow_state", groups[group], filtered_params))
    elif group:
        frappe.throw(_("Unknown dashboard filter."))
    if cint(scorecards):
        filtered.append(f"EXISTS (SELECT 1 FROM {ASSESSMENTS} s WHERE s.name=a.assessment "
            f"AND s.docstatus=1 AND {scope.results_condition('s')})")
    where = " AND ".join(f"({clause})" for clause in filtered)
    totals = frappe.db.sql(f"SELECT COUNT(*) AS total, COALESCE(SUM(a.needs_reassignment),0) AS needs "
        f"FROM {ASSIGNMENTS} a WHERE {where}", filtered_params, as_dict=True)[0]
    page = max(1, cint(page))
    actionable = ("Submitted", "Resubmitted", "Under Review") if scope.kind == "Auditor" else (
        "Draft", "In Progress", "Clarification Required")
    order_params = []
    actionable_sql = scope.in_values("a.workflow_state", actionable, order_params)
    due = "COALESCE(a.review_due_date,a.due_date,'9999-12-31')" if scope.kind == "Auditor" else "COALESCE(a.due_date,'9999-12-31')"
    rows = frappe.db.sql(f"SELECT a.name,a.assessment,a.needs_reassignment FROM {ASSIGNMENTS} a "
        f"WHERE {where} ORDER BY CASE WHEN {actionable_sql} THEN 0 ELSE 1 END,{due},a.modified DESC "
        "LIMIT %s OFFSET %s", [*filtered_params, *order_params, 15, (page - 1) * 15], as_dict=True)
    assessments = []
    # Canonical payload retains report/scope flags and frozen-history behavior.
    # Its document reads are now bounded by the requested page, never total rows.
    for row in rows:
        if row.assessment:
            doc = frappe.get_doc(service.DOCTYPE, row.assessment)
            if sec.can_read_assessment(doc):
                item = service.payload(doc, detail=False)
                item["needs_reassignment"] = bool(row.needs_reassignment)
                assessments.append(item)
    actions_count, actions = _overdue_actions(scope)
    return {"assessments": assessments, "total": cint(totals.total), "page": page, "page_size": 15,
        "counts": counts, "overdue": overdue, "customer_count": len(scope.all_entities),
        "needs_reassignment": cint(totals.needs), "overdue_actions_count": actions_count,
        "overdue_actions": actions,
        "recent_activity": activity(entity=entity, limit=5, milestones_only=scope.kind == "Customer", _scope=scope),
        "results_visibility": "Preliminary scorecard" if scope.preliminary else frappe.db.get_single_value("GRC Settings", "results_visibility")}


def _overdue_actions(scope):
    params = []
    clauses = [scope.entity_condition("x", params), "x.status NOT IN ('Completed','Cancelled')", "x.due_date<%s"]
    params.append(today())
    access = scope.assessment_condition("s", params)
    if scope.kind == "Customer":
        # Contributors may read their explicitly assigned action even when a
        # different contributor owns the assessment; result visibility still applies.
        contributors = tuple(e for e in scope.all_entities if sec.membership(e) == "Contributor")
        contributed = scope.in_values("x.entity", contributors, params)
        params.append(scope.user)
        access = f"(({access}) OR ({contributed} AND x.assigned_to=%s))"
    clauses.extend([access, scope.results_condition("s")])
    where = " AND ".join(f"({clause})" for clause in clauses)
    source = f"`tabIA Maturity Action` x JOIN {ASSESSMENTS} s ON s.name=x.assessment"
    count = frappe.db.sql(f"SELECT COUNT(*) FROM {source} WHERE {where}", params)[0][0]
    rows = frappe.db.sql("SELECT x.name,x.entity,x.assessment,x.finding_title,x.assigned_to,x.due_date,x.status "
        f"FROM {source} WHERE {where} ORDER BY x.due_date ASC LIMIT 5", params, as_dict=True)
    return cint(count), rows


@read_request
def activity(entity=None, assignment=None, *, limit=None, milestones_only=False, _scope=None):
    """Canonical activity response; dashboards alone request a five-row preview."""
    scope = _scope or ReadScope(entity)
    if assignment:
        row = frappe.get_doc("GRC Assessment Assignment", assignment)
        sec.require_entity(row.entity)
        sec.require_assessment(frappe.get_doc(service.DOCTYPE, row.assessment))
    params = []
    clauses = [scope.entity_condition("v", params),
        scope.department_condition("v", _department("v", "activity"), params)]
    if assignment:
        clauses.append("v.assignment=%s")
        params.append(assignment)
    if scope.kind == "Customer":
        clauses.append("v.internal=0")
    if scope.kind in {"Customer", "Auditor"}:
        access = scope.assessment_condition("s", params)
        clauses.append(f"(COALESCE(v.assessment,'')='' OR ({access}))")
    if milestones_only:
        clauses.extend(["COALESCE(v.assessment,'')<>''", scope.in_values("v.action", MILESTONES, params)])
    where = " AND ".join(f"({clause})" for clause in clauses)
    limit_sql = ""
    if limit is not None:
        limit_sql = " LIMIT %s"
        params.append(max(1, cint(limit)))
    rows = frappe.db.sql("SELECT v.name,v.entity,v.action,v.details,v.creation,v.actor,v.assessment,v.assignment,v.grc_department "
        f"FROM `tabGRC Activity` v LEFT JOIN {ASSESSMENTS} s ON s.name=v.assessment "
        f"WHERE {where} ORDER BY v.creation DESC{limit_sql}", params, as_dict=True)
    if scope.kind == "Customer":
        for row in rows:
            detail = frappe.parse_json(row.details or "{}")
            if row.action == "Answers changed":
                detail = {"questions": [c["question"] for c in detail.get("changes", [])]}
            elif row.action in {"Evidence uploaded", "Evidence deleted"}:
                detail = {"filename": detail.get("filename")}
            elif row.action == "Clarification Required":
                detail = {"clarification": detail.get("comment", "")}
            elif row.action == "Status changed":
                detail = {k: detail.get(k) for k in ("from", "to")}
            else:
                detail = {}
            row.details = frappe.as_json(detail)
    zone = ZoneInfo(get_system_timezone())
    for row in rows:
        row.creation = get_datetime(row.creation).replace(tzinfo=zone).isoformat()
    return rows
