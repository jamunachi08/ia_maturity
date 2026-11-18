"""Guarded local-only fixtures for the four unmocked demo browser journeys.

JSON stdout is consumed internally by Playwright. It can contain a reserved
fixture password or verification code; never print it into shared tool logs.
No credentials are added to source or the browser API.
"""
import argparse
from contextlib import ExitStack
from email import message_from_string
import html
import json
import os
from pathlib import Path
import re
import secrets

ROOT = Path(__file__).resolve().parents[3]
FIELDS = ("results_visibility", "overall_maturity_visibility", "customer_score_timing",
          "report_access_timing", "allow_report_download", "allow_report_email", "expand_maturity", "expand_report")
REPORT_FIELDS = ("client_show_summary", "client_show_sections", "client_show_responses", "client_show_scoring_method")


def local():
    import frappe
    if not (frappe.local.site == "grc.local" and frappe.conf.db_name == "grc_local"
            and frappe.conf.get("mute_emails") and frappe.conf.get("allow_tests")
            and frappe.conf.db_socket == str(ROOT / "sites/.grc-db/mysql.sock")):
        raise RuntimeError("Only the isolated muted local demo site is allowed.")


def state_path(run):
    if not re.fullmatch(r"[a-z0-9]{6,24}", run):
        raise ValueError("Invalid reserved demo run identifier.")
    return ROOT / "sites/grc.local/private" / ("demo-cycle-" + run + ".json")


def reserved(email, run):
    if not re.fullmatch(r"grc-journey-" + re.escape(run) + r"-[a-z0-9-]+@example\.test", email):
        raise ValueError("Only this demo run's reserved accounts are allowed.")


def setup(run):
    import frappe
    from ia_maturity.grc import security as sec, departments
    from frappe.utils.password import update_password
    from frappe.twofactor import get_otpsecret_for_, set_default
    path = state_path(run)
    if path.exists():
        return json.loads(path.read_text())
    settings = frappe.get_single("GRC Settings")
    report_settings = frappe.get_single("IA Maturity Settings")
    state = {"run": run, "staff": {}, "previous_settings": {k: settings.get(k) for k in FIELDS},
        "previous_report_settings": {k: report_settings.get(k) for k in REPORT_FIELDS}}
    for short, department in (("ia", "Internal Audit"), ("grc", "GRC")):
        state["staff"][short] = {}
        for role in ("Consultant", "Reviewer", "Manager"):
            email = f"grc-journey-{run}-{short}-{role.lower()}@example.test"
            reserved(email, run)
            if frappe.db.exists("User", email):
                raise RuntimeError("Unexpected existing fixture user.")
            password = secrets.token_urlsafe(24)
            with sec.service_write():
                user = frappe.get_doc({"doctype": "User", "email": email,
                    "first_name": "Journey", "last_name": short.upper() + " " + role,
                    "user_type": "System User", "grc_account_type": "Auditor", "enabled": 1,
                    "grc_mfa_policy": "Default", "grc_mfa_opt_in": 0,
                    "roles": [{"role": "GRC " + role}], "send_welcome_email": 0})
                user.flags.no_welcome_mail = True
                user.insert(ignore_permissions=True)
            update_password(email, password)
            get_otpsecret_for_(email)
            set_default(email + "_otplogin", 1)
            departments.save_department_staff(email, department, role)
            state["staff"][short][role.lower()] = {"email": email, "password": password}
    values = {"results_visibility": "Preliminary scorecard", "overall_maturity_visibility": "After assessment completion",
        "customer_score_timing": "After submission", "report_access_timing": "Before Audit",
        "allow_report_download": 1, "allow_report_email": 1, "expand_maturity": 1, "expand_report": 1}
    frappe.db.set_single_value("GRC Settings", values)
    frappe.db.set_single_value("IA Maturity Settings", {k: 1 for k in REPORT_FIELDS})
    frappe.clear_document_cache("GRC Settings", "GRC Settings")
    frappe.clear_document_cache("IA Maturity Settings", "IA Maturity Settings")
    frappe.db.commit()
    path.write_text(json.dumps(state, indent=2))
    path.chmod(0o600)
    return state


def assign(run, entity, name, kind):
    import frappe
    from ia_maturity.grc import administration, ownership, operations, security as sec
    if not entity.startswith("Journey demo " + run + " "):
        raise ValueError("Only this demo run's company is allowed.")
    doc = frappe.get_doc("IA Maturity Assessment", name)
    if doc.entity != entity or doc.grc_assessment_type != kind:
        raise ValueError("Fixture assessment/company/type mismatch.")
    state = json.loads(state_path(run).read_text())
    staff = state["staff"]["ia" if kind == "Internal Audit" else "grc"]
    with ownership.writing(), operations.writing(apply=True):
        for role in ("Consultant", "Reviewer", "Manager"):
            email = staff[role.lower()]["email"]
            result = administration.assign_customer(entity, email, role)
            row = frappe.get_doc("Auditor Customer Assignment", result["name"])
            row.grc_lock_exception = 1
            row.save(ignore_permissions=True)
        administration.assign_assessment(doc.grc_assignment, consultant=staff["consultant"]["email"],
            reviewer=staff["reviewer"]["email"], reason="Allocate reserved demo-cycle staff")
    frappe.db.commit()
    return {"assigned": True}


def mail_body(email, reference_doctype, reference_name=None):
    import frappe
    filters = {"reference_doctype": reference_doctype}
    if reference_name:
        filters["reference_name"] = reference_name
    rows = frappe.get_all("Email Queue", filters=filters, fields=["name", "message"], order_by="creation desc", limit_page_length=50)
    for row in rows:
        queue = frappe.get_doc("Email Queue", row.name)
        if email not in {r.recipient for r in queue.recipients}:
            continue
        mime = message_from_string(row.message)
        for part in mime.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8"), queue
    raise RuntimeError("Reserved fixture email message is missing.")


def evidence(run, name):
    import frappe
    from ia_maturity.grc import scope
    doc = frappe.get_doc("IA Maturity Assessment", name)
    reserved(doc.respondent, run)
    queues = frappe.get_all("Email Queue", filters={"reference_doctype": "IA Maturity Assessment", "reference_name": name},
        fields=["name", "message"], order_by="creation desc", limit_page_length=20)
    release = frappe.db.get_value("GRC Report Release", {"assessment": name}, "name")
    if release:
        queues += frappe.get_all("Email Queue", filters={"reference_doctype": "GRC Report Release", "reference_name": release},
            fields=["name", "message"], order_by="creation desc", limit_page_length=20)
    attachment, recipient, queue_id, accepted = False, None, None, False
    from importlib.util import spec_from_file_location, module_from_spec
    module_spec = spec_from_file_location("local_demo_smtp", ROOT / "apps/ia_maturity/scripts/serve_demo_acceptance.py")
    transport = module_from_spec(module_spec); module_spec.loader.exec_module(transport)
    for row in queues:
        queue = frappe.get_doc("Email Queue", row.name)
        if {r.recipient for r in queue.recipients} != {doc.respondent}:
            continue
        with ExitStack() as stack:
            transport.transport_patches(stack)
            queue.send()
        queue.reload()
        mime = message_from_string(queue.message)
        attachment = any(p.get_content_type() == "application/pdf" and (p.get_payload(decode=True) or b"").startswith(b"%PDF-") for p in mime.walk())
        recipient, queue_id, accepted = doc.respondent, queue.name, queue.status == "Sent"
        if attachment:
            break
    return {"score": doc.overall_score, "section_codes": sorted(scope.codes(doc) or {a.section_code for a in doc.answers}),
        "report_id": doc.grc_report_id, "queue_has_pdf_attachment": attachment,
        "recipient": recipient, "transport_accepted": accepted,
        "profile_snapshot": bool(doc.grc_profile_snapshot), "report_released": bool(frappe.db.exists("GRC Report Release", {"assessment": name}))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "assign", "code", "invite-link", "login-code", "evidence"])
    parser.add_argument("run")
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    state_path(args.run)
    os.chdir(ROOT / "sites")
    import frappe
    frappe.init(site="grc.local"); frappe.connect()
    try:
        local(); frappe.set_user("Administrator")
        if args.command == "setup":
            result = setup(args.run)
        elif args.command == "assign":
            result = assign(args.run, *args.args)
        elif args.command == "evidence":
            result = evidence(args.run, *args.args)
        else:
            email = args.args[0]; reserved(email, args.run)
            if args.command == "login-code":
                import pyotp
                from frappe.twofactor import get_otpsecret_for_
                result = {"code": pyotp.TOTP(get_otpsecret_for_(email)).now()}
            elif args.command == "code":
                registration = frappe.db.get_value("IA Maturity Registration", {"email": email, "status": "Pending"}, "name", order_by="creation desc")
                body, queue = mail_body(email, "IA Maturity Registration", registration)
                match = re.search(r">\s*([0-9]{6})\s*</p>", body)
                if not match or queue.status != "Sent":
                    raise RuntimeError("Immediately accepted verification code is missing.")
                result = {"code": match.group(1)}
            else:
                invitation = frappe.db.get_value("GRC Onboarding Invitation", {"email": email}, "name", order_by="creation desc")
                body, queue = mail_body(email, "GRC Onboarding Invitation", invitation)
                match = re.search(r'href="([^"]+/onboarding[?]token=[^"]+)"', body)
                if not match:
                    raise RuntimeError("Reserved invitation link is missing.")
                result = {"url": html.unescape(match.group(1))}
        frappe.db.commit()
        print(json.dumps(result, default=str))
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
