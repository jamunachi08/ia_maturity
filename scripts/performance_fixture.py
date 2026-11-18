"""Create reserved users/data only on the separate muted performance site.

The private state contains passwords and session cookies. Never publish it.
Customer sessions are obtained through the real single-use verify_code API;
the fixture creates a pending challenge locally instead of sending SMTP mail.
"""
import argparse
import json
import secrets
import time

from performance_environment import SITE, TARGET, connect, guard

STATE = TARGET / "private/performance-fixture.json"
PREFIX = "grc-perf-"


def save(state):
    STATE.write_text(json.dumps(state, indent=2))
    STATE.chmod(0o600)


def seed(scale):
    if scale not in (1, 5):
        raise ValueError("Use only the documented 1x or 5x fixture scale.")
    frappe = connect()
    from ia_maturity.grc import security as sec, departments, assessments as svc
    from ia_maturity.grc import administration, ownership, operations
    from frappe.utils.password import update_password
    state = json.loads(STATE.read_text()) if STATE.exists() else {"site": SITE, "users": {}}
    # Seeding is additive. A later 1x invocation must not relabel retained 5x data.
    scale = max(scale, int(state.get("scale", scale)))
    try:
        specifications = [("admin", "GRC App Admin"), ("erp", "System Manager")]
        for department in ("ia", "grc"):
            specifications.extend((department + "_" + role, "GRC " + role.title())
                for role in ("customer", "consultant", "reviewer", "manager"))
        counts = {"customer": 10, "consultant": 6, "reviewer": 2, "manager": 1, "admin": 1, "erp": 1}
        expanded = []
        for role_key, role in specifications:
            for number in range(1, counts[role_key.split("_")[-1]] + 1):
                expanded.append((role_key if number == 1 else role_key + "_" + str(number), role_key, role))
        for key, role_key, role in expanded:
            email = PREFIX + key.replace("_", "-") + "@example.test"
            if key not in state["users"]:
                if frappe.db.exists("User", email):
                    raise RuntimeError("Unrecognized existing reserved fixture user.")
                password = secrets.token_urlsafe(24)
                with sec.service_write():
                    user = frappe.get_doc({"doctype": "User", "email": email,
                        "first_name": "Performance", "last_name": role_key.replace("_", " "),
                        "roles": [{"role": role}], "send_welcome_email": 0,
                        "grc_mfa_policy": "Disabled", "grc_email_verified": 1})
                    user.flags.no_welcome_mail = True
                    user.insert(ignore_permissions=True)
                update_password(email, password)
                state["users"][key] = {"email": email, "password": password, "role_key": role_key}
                frappe.db.commit()
                save(state)
            state["users"][key]["role_key"] = role_key
            if role_key.split("_")[-1] in {"consultant", "reviewer", "manager"}:
                department = "Internal Audit" if role_key.startswith("ia_") else "GRC"
                departments.save_department_staff(email, department, role_key.split("_")[-1].title())
        for short, department, template in (
            ("ia", "Internal Audit", "IIA GIAS Maturity Assessment (20Q)"),
            ("grc", "GRC", "GRC Maturity Assessment (46Q) v1.0"),
        ):
            entity = "_Performance " + department
            if not frappe.db.exists("IA Maturity Entity", entity):
                with sec.service_write():
                    frappe.get_doc({"doctype": "IA Maturity Entity", "entity_name": entity}).insert(ignore_permissions=True)
            departments.grant(entity, department, "Reserved isolated performance fixture")
            customer = state["users"][short + "_customer"]["email"]
            for account in state["users"].values():
                if account["role_key"] == short + "_customer" and not frappe.db.exists("GRC Organization Membership", {"entity": entity, "user": account["email"]}):
                    with sec.service_write():
                        frappe.get_doc({"doctype": "GRC Organization Membership", "entity": entity,
                            "user": account["email"], "membership_role": "Organization Admin", "active": 1}).insert(ignore_permissions=True)
            with ownership.writing(), operations.writing(apply=True):
                for account in state["users"].values():
                    if account["role_key"] not in {short + "_" + role for role in ("consultant", "reviewer", "manager")}:
                        continue
                    result = administration.assign_customer(entity, account["email"], account["role_key"].split("_")[-1].title())
                    row = frappe.get_doc("Auditor Customer Assignment", result["name"])
                    row.grc_lock_exception = 1
                    row.save(ignore_permissions=True)
            current = frappe.db.count("GRC Assessment Assignment", {"entity": entity})
            for number in range(current, 22 * scale):
                doc = svc.new_assessment(entity, template, respondent=customer, assessment_type=department)
                administration.assign_assessment(doc.grc_assignment,
                    consultant=state["users"][short + "_consultant"]["email"],
                    reviewer=state["users"][short + "_reviewer"]["email"], reason="Reserved performance dataset")
                for _ in range(9):
                    sec.log("Assessment started", entity, doc.grc_assignment, doc.name, internal=False)
                if number % 10 == 0:
                    frappe.db.commit()
            state.setdefault("entities", {})[short] = entity
        state["scale"] = scale
        state["fixture_assignments"] = 44 * scale
        frappe.db.commit()
        save(state)
        print(json.dumps({"site": SITE, "scale": scale, "users": len(state["users"]),
            "fixture_assignments": state["fixture_assignments"], "credentials": "private fixture state only"}))
    finally:
        frappe.destroy()


def sessions(base_url):
    from urllib.parse import urlparse
    import requests
    guard()
    url = urlparse(base_url)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or url.port not in (8011, 8012, 8013, 8014):
        raise ValueError("Only dedicated loopback performance servers are allowed.")
    state = json.loads(STATE.read_text())
    for key, account in state["users"].items():
        client = requests.Session()
        client.get(base_url + "/login", timeout=120)
        if account.get("role_key", key).endswith("customer"):
            frappe = connect()
            from ia_maturity.grc.auth import digest
            from frappe.utils import now_datetime, add_to_date, today
            code = f"{secrets.randbelow(10**6):06d}"
            frappe.get_doc({"doctype": "IA Maturity Registration", "email": account["email"],
                "full_name": "Performance Customer", "entity_name": "Reserved performance fixture",
                "purpose": "Resume", "language": "en", "assessment_date": today(), "consent": 1,
                "status": "Pending", "code_hash": digest(code), "link_key_hash": digest(secrets.token_urlsafe(32)),
                "expires_on": add_to_date(now_datetime(), minutes=15)}).insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.destroy()
            response = client.post(base_url + "/api/method/ia_maturity.grc.auth.verify_code",
                json={"email": account["email"], "code": code}, timeout=120)
        else:
            response = client.post(base_url + "/api/method/login",
                json={"usr": account["email"], "pwd": account["password"]}, timeout=120)
            if response.status_code == 200 and response.json().get("verification"):
                frappe = connect()
                from frappe.twofactor import get_otpsecret_for_
                import pyotp
                code = pyotp.TOTP(get_otpsecret_for_(account["email"])).now()
                frappe.destroy()
                response = client.post(base_url + "/api/method/login", json={"usr": account["email"],
                    "pwd": account["password"], "tmp_id": response.json()["tmp_id"], "otp": code}, timeout=120)
        if response.status_code != 200 or client.cookies.get("sid") in (None, "Guest"):
            raise RuntimeError("Reserved fixture authentication failed for role " + key)
        account["cookies"] = client.cookies.get_dict()
        check = client.get(base_url + "/api/method/ia_maturity.grc.api.bootstrap", timeout=120)
        if check.status_code != 200:
            raise RuntimeError("Reserved fixture bootstrap failed for role " + key)
        account["home"] = check.json()["message"]["home"]
        account["kind"] = check.json()["message"]["kind"]
        account["authenticated_at"] = int(time.time())
        save(state)
    print(json.dumps({"site": SITE, "authenticated_roles": list(state["users"]), "external_email": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "sessions"))
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    args = parser.parse_args()
    seed(args.scale) if args.command == "seed" else sessions(args.base_url)


if __name__ == "__main__":
    main()
