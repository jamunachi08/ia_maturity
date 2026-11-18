"""Real HTTP acceptance on grc.local only; creates isolated demonstration records."""
import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
BASE = "http://127.0.0.1:8005"
os.chdir(ROOT / "sites")
import frappe
import pyotp
from frappe.twofactor import get_otpsecret_for_
from frappe.utils.password import update_password
from ia_maturity.grc import assessments, security as sec
from ia_maturity.install import SEED_TEMPLATE

frappe.init(site="grc.local")
frappe.connect()
assert frappe.conf.grc_enabled and frappe.conf.db_name == "grc_local"
assert frappe.conf.mute_emails, "Do not send real customer email during this test."
frappe.set_user("Administrator")
credentials = json.loads((ROOT / "sites/grc.local/private/grc-local-credentials.json").read_text())
suffix = secrets.token_hex(4)
customer = "scope-http-" + suffix + "@example.test"
password = secrets.token_urlsafe(24)
with sec.service_write():
    frappe.get_doc({"doctype": "User", "email": customer, "first_name": "HTTP Scope Customer",
        "send_welcome_email": 0, "grc_email_verified": 1, "roles": [{"role": "GRC Customer"}]}).insert(ignore_permissions=True)
update_password(customer, password)
template = frappe.copy_doc(frappe.get_doc("IA Maturity Template", SEED_TEMPLATE))
template.template_name = "_Test HTTP Packages " + suffix
template.grc_published, template.grc_policy = 0, ""
template.insert(ignore_permissions=True)
template = assessments.publish(template.name)
required = template.questions[0].section_code
optional = next(q.section_code for q in template.questions if q.section_code != required)
old_policy = frappe.db.get_single_value("GRC Operations Policy", "policies")
frappe.db.set_single_value("GRC Operations Policy", "policies", "{}")
frappe.db.commit()


def call(client, method, values=None, expected=200, get=False):
    url = BASE + "/api/method/" + (method if "." in method or method == "login" else "ia_maturity.grc.api." + method)
    response = client.get(url, params=values or {}) if get else client.post(url, json=values or {})
    assert response.status_code == expected, (method, response.status_code, response.text[:180])
    return response.json().get("message") if expected == 200 and method != "login" else response


def login(email, pwd):
    client = requests.Session()
    response = call(client, "login", {"usr": email, "pwd": pwd}).json()
    if response.get("tmp_id"):
        otp = pyotp.TOTP(get_otpsecret_for_(email)).now()
        call(client, "login", {"usr": email, "pwd": pwd, "tmp_id": response["tmp_id"], "otp": otp})
    return client


try:
    admin = login("admin@grc.example.test", credentials["admin@grc.example.test"])
    auditor = login("auditor@grc.example.test", credentials["auditor@grc.example.test"])
    client = login(customer, password)
    unrelated = login("customer@alpha.example.test", credentials["customer@alpha.example.test"])
    created = call(auditor, "create_onboarding_invitation", {"email": customer})
    assert created["invited_by"] == "auditor@grc.example.test"
    assert created["delivery_status"] in {"Queued", "Failed"}  # SMTP is muted; neither state proves receipt.
    call(unrelated, "resume_onboarding", {"name": created["name"]}, expected=403)
    call(client, "onboarding_detail", {"name": created["name"]}, expected=403)
    resumed = login(customer, password)  # A new cookie jar proves cross-browser resume.
    call(resumed, "resume_onboarding", {"name": created["name"]})
    completion = {"name": created["name"], "organization_name": "_Test HTTP Invited " + suffix, "sector": "Other"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        completed = list(pool.map(lambda session: call(session, "complete_onboarding", completion), [client, resumed]))
    entity = completed[0]["entity"]
    assert completed[1]["entity"] == entity, "Concurrent completion created duplicate customers"
    assert call(resumed, "complete_onboarding", {"name": created["name"], "organization_name": "ignored", "sector": "Other"})["entity"] == entity
    controls = call(admin, "customer_ownership", {"entity": entity}, get=True)
    assert controls["auditor"] == created["invited_by"] and controls["locked"]
    assert call(auditor, "onboarding_detail", {"name": created["name"]}, get=True)["status"] == "Completed"
    call(unrelated, "organization_detail", {"name": entity}, expected=403)
    configuration = {"required_sections": [required], "packages": [{"code": "extra", "label": "Additional audit", "label_ar": "تدقيق إضافي", "description": "Additional coverage", "description_ar": "تغطية إضافية", "sections": [optional]}]}
    call(auditor, "scope_configurations", {"template": template.name}, expected=403)
    saved = call(admin, "save_scope_configuration", {"template": template.name, "configuration": configuration})
    call(admin, "publish_scope_configuration", saved)
    started = call(resumed, "start_assessment", {"entity": entity, "template": template.name})
    doc = call(resumed, "assessment", {"name": started["name"]}, get=True)
    assert not doc["editable"] and not doc["scope"]["confirmed"]
    doc = call(resumed, "confirm_assessment_scope", {"name": doc["name"], "packages": [], "modified": doc["modified"]})
    assert {q["section_code"] for q in doc["questions"]} == {required}
    omitted = next(q.question_code for q in template.questions if q.section_code == optional)
    call(resumed, "save_assessment", {"name": doc["name"], "answers": {omitted: {"selected_option": "D"}}, "modified": doc["modified"]}, expected=417)
    doc = call(resumed, "save_assessment", {"name": doc["name"], "answers": {q["question_code"]: {"selected_option": "D"} for q in doc["questions"]}, "modified": doc["modified"]})
    # Respect customer results-visibility policy; the authorized admin sees the backend score.
    assert call(admin, "assessment", {"name": doc["name"]}, get=True)["overall_score"] == 100
    corrected = call(admin, "correct_assessment_scope", {"name": doc["name"], "packages": ["extra"], "modified": doc["modified"], "reason": "HTTP draft correction"})
    assert corrected["scope"]["acknowledgement_required"] and not corrected["editable"]
    call(resumed, "save_assessment", {"name": doc["name"], "answers": {}, "modified": corrected["modified"]}, expected=417)
    doc = call(resumed, "confirm_assessment_scope", {"name": doc["name"], "packages": ["extra"], "modified": corrected["modified"]})
    assert doc["editable"] and not doc["scope"]["acknowledgement_required"]
    doc = call(resumed, "save_assessment", {"name": doc["name"], "answers": {q["question_code"]: {"selected_option": "D"} for q in doc["questions"]}, "modified": doc["modified"]})
    call(resumed, "submit_assessment", {"name": doc["name"]})
    for action in ("start_review", "approve", "release"):
        report = call(admin, "transition", {"name": doc["name"], "action": action})
    assert report["overall_score"] == 100 and report["report"]["overall"] == 100
    assert len(report["report"]["audit_scope"]["selected_sections"]) == 2
    pdf = admin.get(BASE + "/api/method/ia_maturity.grc.api.download_report", params={"name": doc["name"]})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    Path("/tmp/grc-scoped-http-report.pdf").write_bytes(pdf.content)
    # Restore a former-owner visibility check on the same authenticated cookie.
    call(admin, "set_customer_ownership", {"entity": entity, "auditor": "admin@grc.example.test", "locked": 1, "exceptions": [], "reason": "HTTP transfer acceptance", "modified": controls["modified"]})
    call(auditor, "onboarding_detail", {"name": created["name"]}, expected=403)
    call(auditor, "assessment", {"name": doc["name"]}, expected=403)
    call(auditor, "organization_detail", {"name": entity}, expected=403)
    assert entity not in [r["name"] for r in call(auditor, "organizations", get=True)]
    assert all("token_hash" not in r and "events" not in r for r in call(admin, "onboarding_invitations", get=True))
    print("PASS: HTTP inviter attribution, cross-browser resume, recipient isolation, concurrent/idempotent completion, locked ownership, scoped questions/scoring/PDF release, rejected excluded writes and immediate transfer revocation.")
finally:
    frappe.db.rollback()
    frappe.set_user("Administrator")
    frappe.db.set_single_value("GRC Operations Policy", "policies", old_policy or "{}")
    frappe.db.commit()
    frappe.destroy()
