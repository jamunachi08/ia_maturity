"""Approved-copy revalidation is isolated from personal and preview responses."""
import unittest
from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response
from ia_maturity.grc.response_cache import apply_headers, PUBLIC_CONTENT


class TestResponseCache(unittest.TestCase):
    def response(self, path, body='{"message":{"title":"Approved"}}', etag=None, method="GET", status=200, user="Guest"):
        headers = {"If-None-Match": etag} if etag else {}
        request = Request(EnvironBuilder(path=path, method=method, headers=headers).get_environ())
        response = Response(body, status=status, mimetype="application/json")
        with patch.object(frappe.local, "request", request, create=True), patch.object(
                frappe.local, "form_dict", frappe._dict()), patch.object(
                frappe.local, "session", frappe._dict(user=user)):
            apply_headers(response)
        return response

    def test_current_approved_copy_revalidates_and_new_publication_changes_etag(self):
        first = self.response(PUBLIC_CONTENT)
        self.assertIn("private", first.headers["Cache-Control"])
        self.assertNotIn("public", first.headers["Cache-Control"])
        self.assertEqual(self.response(PUBLIC_CONTENT, etag=first.headers["ETag"]).status_code, 304)
        published = self.response(PUBLIC_CONTENT, body='{"message":{"title":"New approved copy"}}', etag=first.headers["ETag"])
        self.assertEqual(published.status_code, 200)
        self.assertNotEqual(first.headers["ETag"], published.headers["ETag"])

    def test_private_preview_auth_and_error_responses_never_use_public_revalidation(self):
        for path in ("/api/method/ia_maturity.grc.api.bootstrap", "/api/method/ia_maturity.grc.api.dashboard",
                "/api/method/ia_maturity.grc.api.site_content_revision", "/private/files/report.pdf",
                "/login", "/grc-site", "/api/method/login"):
            with self.subTest(path=path):
                result = self.response(path, etag='"stale"')
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.headers["Cache-Control"], "no-store")
                self.assertNotIn("ETag", result.headers)
        result = self.response(PUBLIC_CONTENT, status=403)
        self.assertEqual(result.headers["Cache-Control"], "no-store")

    def test_fingerprinted_asset_delivery_remains_owned_by_reverse_proxy(self):
        self.assertNotIn("Cache-Control", self.response("/assets/ia_maturity/grc/assets/index-hash.js").headers)

    def test_error_fallbacks_and_other_authenticated_pages_are_not_cached(self):
        for status in (403, 404, 500):
            with self.subTest(status=status):
                self.assertEqual(self.response("/assets/ia_maturity/grc/assets/missing-abcdefgh.js",
                    status=status).headers["Cache-Control"], "no-store")
        self.assertEqual(self.response("/custom-erp-page", user="erp@example.test").headers["Cache-Control"], "no-store")
