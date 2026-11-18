"""Private, idempotent workflow notices and reminder delivery tracking."""
import frappe
from frappe.utils import add_days, cint, getdate, now_datetime, today, escape_html, get_url, validate_email_address
from ia_maturity.grc import security as sec


def queue(entity, reference, recipient, state, key, kind="Status"):
    # Platform identities can have synthetic/explicit GRC roles, but their
    # usernames are not business email recipients.
    if not recipient or recipient in frappe.STANDARD_USERS:
        return
    user = frappe.db.get_value("User", recipient, ["enabled", "email"], as_dict=True)
    if not user or not user.enabled or not sec.can_access(entity, recipient):
        return
    from ia_maturity.grc import departments as dept
    reference_doc = None
    for dt in ("GRC Assessment Assignment", "GRC Follow Up"):
        if frappe.db.exists(dt, reference):
            reference_doc = frappe.get_doc(dt, reference)
            break
    if reference_doc and not dept.can_read(reference_doc, recipient):
        return
    from ia_maturity.grc.preferences import optional_allowed
    if not optional_allowed(entity, recipient, kind):
        return
    if frappe.db.exists("GRC Reminder Delivery", {"delivery_key": key}):
        return
    with sec.service_write():
        delivery = frappe.get_doc(dict(doctype="GRC Reminder Delivery", entity=entity,
            grc_department=dept.kind(reference_doc) if reference_doc else None,
            reference_name=reference, recipient=recipient, subject=f"AlphaX | {state}",
            delivery_key=key, notification_kind=kind)).insert(ignore_permissions=True)
    email = validate_email_address(user.email or "")
    if not email or "," in email:
        delivery.db_set({"status": "Failed", "error": "Recipient has no single valid email address."})
        return
    url = get_url(sec.home(recipient), allow_header_override=False)
    message_count = len(frappe.local.message_log)
    try:
        emails = frappe.sendmail(recipients=[email], subject=delivery.subject, delayed=True,
            message=f'<p>{escape_html(state)}</p><p><a href="{escape_html(url)}">'
                    'Open your workspace / فتح مساحة العمل</a></p>'
                    '<p>Sign in to view authorized details. / سجّل الدخول للاطلاع على التفاصيل المصرح بها.</p>',
            reference_doctype="GRC Reminder Delivery", reference_name=delivery.name)
        queue_name = frappe.db.get_value("Email Queue", {
            "reference_doctype": "GRC Reminder Delivery", "reference_name": delivery.name}, "name")
        if not emails or not queue_name:
            delivery.db_set({"status": "Failed", "error": "Email could not be queued."})
        else:
            delivery.db_set({"email_queue": queue_name, "status": "Queued"})
    except (frappe.OutgoingEmailError, frappe.InvalidEmailAddressError) as exc:
        error = ("Notification email configuration contains an invalid address."
                 if isinstance(exc, frappe.InvalidEmailAddressError)
                 else "Outgoing email is not configured or unavailable.")
        delivery.db_set({"status": "Failed", "error": error})
        # A non-critical mail configuration error must not appear as a failed
        # customer submission. Keep the failure in the delivery record/log.
        del frappe.local.message_log[message_count:]
        frappe.log_error(title="GRC notification delivery failed")


def workflow_notice(assignment):
    state = assignment.workflow_state
    if state in {"Submitted", "Resubmitted"}:
        recipients = {assignment.consultant, assignment.reviewer}
        from ia_maturity.grc.departments import kind, manager
        department = kind(assignment)
        recipients.update(r.user for r in frappe.get_all("GRC Department Staff", filters={"department": department,
            "role": "Manager", "active": 1}, fields=["user"]) if manager(department, r.user))
        recipients.update(frappe.get_all("User", filters={"enabled": 1,
            "name": ["in", frappe.get_all("Has Role", filters={"role": "GRC App Admin", "parenttype": "User"}, pluck="parent") or [""]]}, pluck="name"))
    else:
        recipients = {assignment.respondent}
    for recipient in sorted(recipients - set(frappe.STANDARD_USERS) - {None, ""}):
        queue(assignment.entity, assignment.name, recipient, state,
              f"workflow:{assignment.name}:{assignment.assessment}:{state}:{recipient}:{assignment.modified}",
              kind="Clarification" if state == "Clarification Required" else "Status")


def send_reminders():
    if not sec.enabled():
        return
    settings = frappe.get_single("GRC Settings")
    if not settings.reminders_enabled:
        return
    interval = max(1, cint(settings.reminder_days) or 7)
    for a in frappe.get_all("GRC Assessment Assignment",
            filters={"workflow_state": ["not in", ["Approved", "Report Released"]]}, fields=["*"]):
        if a.last_reminded_on and getdate(a.last_reminded_on) > getdate(add_days(today(), -interval)):
            continue
        review = a.workflow_state in {"Submitted", "Resubmitted", "Under Review"}
        due = a.review_due_date if review else a.due_date
        if not due or getdate(due) > getdate(today()):
            continue
        recipients = {a.consultant, a.reviewer} if review else {a.respondent}
        for recipient in recipients:
            if recipient:
                queue(a.entity, a.name, recipient, "Review overdue" if review else "Assessment action overdue",
                    f"reminder:{a.name}:{recipient}:{today()}", kind="Reminder")
        frappe.db.set_value("GRC Assessment Assignment", a.name, "last_reminded_on", now_datetime())
    for f in frappe.get_all("GRC Follow Up", filters={"status": "Open", "due_date": ["<=", today()]}, fields=["*"]):
        if not f.last_reminded_on or getdate(f.last_reminded_on) <= getdate(add_days(today(), -interval)):
            queue(f.entity, f.name, f.assigned_to, "Customer follow-up due", f"followup:{f.name}:{today()}", kind="Reminder")
            frappe.db.set_value("GRC Follow Up", f.name, "last_reminded_on", now_datetime())
    # Frappe Email Queue owns delivery retries; reflect its terminal state for the admin.
    for row in frappe.get_all("GRC Reminder Delivery",
            filters={"status": "Queued", "email_queue": ["is", "set"]}, fields=["name", "email_queue"]):
        status = frappe.db.get_value("Email Queue", row.email_queue, "status")
        if status in {"Sent", "Error", "Expired"}:
            frappe.db.set_value("GRC Reminder Delivery", row.name,
                "status", "Sent" if status == "Sent" else "Failed")
