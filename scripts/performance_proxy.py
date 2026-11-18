"""Local-only gzip/static-cache delivery rehearsal in front of Gunicorn.

This unprivileged loopback proxy is a test helper, not a production nginx
replacement. It has fixed local upstreams, no response cache and no request logs.
It preserves private cache policy and never sends traffic to external servers.
"""
import argparse
import gzip
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from urllib.parse import urlsplit

from performance_environment import ROOT, guard

HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade"}
FINGERPRINTED = re.compile(r"^/assets/ia_maturity/grc/assets/[^/]+-[A-Za-z0-9_-]{8,}\.(?:js|css)$")
COMPRESSIBLE = {"text/html", "text/css", "text/javascript", "application/javascript",
    "application/json", "image/svg+xml"}


def serve(port):
    guard()
    if port not in (8013, 8014):
        raise ValueError("Only loopback delivery-rehearsal ports 8013 and 8014 are allowed.")
    upstream = 8012 if port == 8013 else 8011

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass  # Authentication bodies/URLs/headers must never enter logs.

        def handle_request(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 20 * 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(length) if length else None
            headers = {key: value for key, value in self.headers.items()
                if key.lower() not in HOP_HEADERS and key.lower() != "host"}
            headers["Host"] = "127.0.0.1:" + str(upstream)
            headers["X-Forwarded-Host"] = "127.0.0.1:" + str(port)
            headers["X-Forwarded-Proto"] = "http"
            connection = HTTPConnection("127.0.0.1", upstream, timeout=120)
            try:
                connection.request(self.command, self.path, body=body, headers=headers)
                response = connection.getresponse()
                data = response.read()
                supplied = response.getheaders()
                content_type = (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
                encoded = response.getheader("Content-Encoding")
                compress = (self.command != "HEAD" and response.status == 200 and len(data) >= 1024
                    and content_type in COMPRESSIBLE and not encoded
                    and "gzip" in self.headers.get("Accept-Encoding", "").lower())
                if compress:
                    data = gzip.compress(data, compresslevel=5, mtime=0)
                upstream_cache = response.getheader("Cache-Control", "").lower()
                fingerprinted = (bool(FINGERPRINTED.fullmatch(urlsplit(self.path).path))
                    and response.status == 200
                    and content_type in {"text/css", "text/javascript", "application/javascript"}
                    and not any(key.lower() == "set-cookie" for key, _ in supplied)
                    and "private" not in upstream_cache and "no-store" not in upstream_cache)
                self.send_response_only(response.status, response.reason)
                vary = response.getheader("Vary", "")
                for key, value in supplied:
                    name = key.lower()
                    if name in HOP_HEADERS or name in {"content-length", "vary"}:
                        continue
                    if fingerprinted and name in {"cache-control", "expires"}:
                        continue
                    if compress and name == "etag" and not value.startswith("W/"):
                        value = "W/" + value
                    self.send_header(key, value)
                if content_type in COMPRESSIBLE:
                    vary = ", ".join(dict.fromkeys([v.strip() for v in vary.split(",") if v.strip()] + ["Accept-Encoding"]))
                if vary:
                    self.send_header("Vary", vary)
                if compress:
                    self.send_header("Content-Encoding", "gzip")
                if fingerprinted:
                    self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                if response.status not in (204, 304):
                    self.send_header("Content-Length", response.getheader("Content-Length", "0") if self.command == "HEAD" else str(len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)
            except (ConnectionError, OSError):
                self.close_connection = True
            finally:
                connection.close()

        do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_OPTIONS = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(json.dumps({"port": port, "upstream": upstream, "gzip_level": 5,
        "response_cache": False, "fingerprinted_assets": "public immutable", "scope": "local delivery rehearsal"}), flush=True)
    runtime = ROOT / "diagnostics/performance-20261113"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / ("proxy-" + str(port) + ".pid")).write_text(str(os.getpid()))
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    serve(parser.parse_args().port)
