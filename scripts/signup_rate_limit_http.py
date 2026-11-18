"""No-email HTTP verification of signup throttling on the disposable grc.local site."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT / "sites")
import frappe
from ia_maturity.grc.auth import digest

frappe.init(site="grc.local")
frappe.connect()
assert frappe.conf.grc_enabled and frappe.conf.db_name == "grc_local"
assert frappe.conf.mute_emails
email = f"signup-http-{uuid4().hex}@example.test"
ip = f"signup-http-{uuid4().hex}"
assert not frappe.db.exists("User", email)
keys = [f"grc:grc.local:{kind}:{digest(email)}" for kind in ("request-email", "request-cooldown")]
ip_key = f"grc:grc.local:request-ip:{digest(ip)}"
url = "http://127.0.0.1:8005/api/method/ia_maturity.grc.auth.request_code"
values = dict(email=email, purpose="Start", full_name="HTTP Customer", consent=1,
    organization_name="_Test HTTP Signup", organization_sector="Healthcare")


def post(payload):
    return requests.post(url, json=payload, headers={"X-Forwarded-For": ip}, timeout=20)


try:
    for _ in range(6):
        assert post({**values, "organization_name": ""}).status_code == 417
    assert frappe.cache.get(keys[0]) is None
    # An unknown Resume address gets the same public response and quotas, but no email.
    assert post({"email": email, "purpose": "Resume"}).status_code == 200
    response = post(values)
    assert response.status_code == 429
    assert 0 < response.json()["retry_after_seconds"] <= 60
    assert int(frappe.cache.get(keys[0])) == 1
    frappe.cache.setex(keys[0], 125, 8)
    response = post(values)
    assert response.status_code == 429
    assert 115 < response.json()["retry_after_seconds"] <= 125
    assert int(frappe.cache.get(keys[0])) == 8
    frappe.cache.delete(*keys)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post({"email": email, "purpose": "Resume"}), range(2)))
    assert sorted(row.status_code for row in responses) == [200, 429]
    assert int(frappe.cache.get(keys[0])) == 1
    assert not frappe.db.exists("IA Maturity Registration", {"email": email})
    print("PASS: invalid signup retries, JSON retry duration, unchanged hourly cap and concurrent HTTP requests; no email sent.")
finally:
    frappe.cache.delete(*keys, ip_key)
    frappe.db.rollback()
    frappe.destroy()
