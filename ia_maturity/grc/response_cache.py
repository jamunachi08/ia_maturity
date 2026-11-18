"""Browser revalidation for approved public copy; private responses never cached."""
import hashlib

import frappe


PUBLIC_CONTENT = "/api/method/ia_maturity.grc.public.site_content"


def apply_headers(response):
    request = getattr(frappe.local, "request", None)
    if not request:
        return
    path = request.path.rstrip("/") or "/"
    if (path == PUBLIC_CONTENT and request.method == "GET"
            and response.status_code == 200 and response.mimetype == "application/json"):
        # No shared/CDN caching: the normal Frappe cookie lifecycle remains intact.
        # Each revalidation computes the current approved body, so publication is
        # visible immediately and never depends on a TTL or cached draft data.
        response.headers["Cache-Control"] = "private, no-cache, must-revalidate"
        response.set_etag(hashlib.sha256(response.get_data()).hexdigest())
        response.make_conditional(request)
    elif (response.status_code >= 400 or frappe.session.user != "Guest"
            or path.startswith(("/api/", "/private/files/", "/grc/", "/grc-site/"))
            or path in {"/", "/grc", "/grc-site", "/login", "/signup", "/update-password", "/onboarding"}
            or frappe.form_dict.get("cmd")):
        response.headers["Cache-Control"] = "no-store"
