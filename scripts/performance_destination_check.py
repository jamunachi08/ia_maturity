"""Read-only, sanitized DevOps diagnostics for one explicitly named site.

Run with that server's bench Python as its owner. It prints selected operational
flags, aggregate counts and timings, never config credentials, SQL text, cookies
or response bodies. It does not send email, change settings or generate load.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--public-url", help="Optional anonymous HTTPS /grc-site or /login check; no query string.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if not args.site or Path(args.site).name != args.site or args.site in {".", ".."}:
        raise ValueError("Provide one exact site directory name.")
    os.chdir(root / "sites")
    import frappe
    frappe.init(site=args.site)
    frappe.connect()
    try:
        from ia_maturity import __version__
        from frappe.utils import cint
        conf = frappe.conf
        hostname = urlparse(str(conf.get("host_name") or ""))
        public_host = (hostname.scheme + "://" + hostname.hostname
            + (":" + str(hostname.port) if hostname.port else "")) if hostname.hostname else None
        result = {"site": args.site, "app_version": __version__, "frappe_version": frappe.__version__,
            "python": platform.python_version(), "logical_cpus": os.cpu_count(),
            "selected_config": {**{key: cint(conf.get(key)) for key in (
                "grc_enabled", "mute_emails", "pause_scheduler")}, "host_name": public_host,
                "gunicorn_workers": conf.get("gunicorn_workers") if isinstance(conf.get("gunicorn_workers"), int) else None}}
        try:
            result["gunicorn_version"] = importlib.metadata.version("gunicorn")
        except importlib.metadata.PackageNotFoundError:
            result["gunicorn_version"] = None
        result["counts"] = {doctype: frappe.db.count(doctype) if frappe.db.table_exists(doctype) else None
            for doctype in ("User", "IA Maturity Entity", "IA Maturity Assessment", "GRC Assessment Assignment", "GRC Activity", "IA Maturity Action")}
        started = time.perf_counter()
        frappe.db.sql("select 1")
        result["database_roundtrip_ms"] = round((time.perf_counter() - started) * 1000, 3)
        if conf.get("db_type", "mariadb") == "mariadb":
            result["database_version"] = frappe.db.sql("select version()")[0][0]
            result["database_global_status"] = dict(frappe.db.sql("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_running','Threads_connected','Slow_queries','Questions')"))
        try:
            started = time.perf_counter()
            frappe.cache.ping()
            result["redis_cache_roundtrip_ms"] = round((time.perf_counter() - started) * 1000, 3)
        except Exception:
            result["redis_cache_roundtrip_ms"] = None
        if args.public_url:
            import requests
            url = urlparse(args.public_url)
            configured = urlparse(str(conf.get("host_name") or ""))
            if (url.scheme != "https" or not url.hostname or url.username or url.password
                    or url.query or url.fragment or url.path not in {"/", "/grc-site", "/login"}
                    or configured.hostname and configured.hostname != url.hostname):
                raise ValueError("Use an anonymous HTTPS page on the configured site hostname, without query/auth data.")
            started = time.perf_counter()
            response = requests.get(args.public_url, timeout=30, allow_redirects=False)
            result["anonymous_http"] = {"path": url.path, "status": response.status_code,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "decoded_bytes": len(response.content), "headers": {key: response.headers.get(key)
                    for key in ("Content-Type", "Content-Encoding", "Cache-Control", "ETag", "Vary")}}
        print(json.dumps(result, indent=2))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
