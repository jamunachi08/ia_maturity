"""Guarded, disposable local performance site and production-style WSGI server.

Never run against production. The source is the existing muted grc.local fixture
site; the destination uses a separate database on sites/.grc-db/mysql.sock.
Secrets and measurements live outside the application repository.
"""
import argparse
import contextvars
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SITE = "grc-perf.local"
DATABASE = "grc_perf_local"
SOCKET = ROOT / "sites/.grc-db/mysql.sock"
SOURCE = ROOT / "sites/grc.local"
TARGET = ROOT / "sites" / SITE


def application_fingerprint(app_root=None):
    """Fingerprint runtime source/assets, excluding credentials and diagnostics."""
    candidate = Path(app_root or ROOT / "apps/ia_maturity")
    digest = hashlib.sha256()
    files = [p for directory in (candidate / "ia_maturity", candidate / "grc/src")
        for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    files.extend(p for p in (candidate / "grc/index.html", candidate / "grc/vite.config.ts") if p.is_file())
    for path in sorted(files):
        digest.update(str(path.relative_to(candidate)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def source_config():
    config = json.loads((SOURCE / "site_config.json").read_text())
    if not (config.get("db_name") == "grc_local" and config.get("mute_emails")
            and config.get("allow_tests") and config.get("db_socket") == str(SOCKET)):
        raise RuntimeError("Only the isolated muted grc.local fixture source is allowed.")
    return config


def guard():
    if os.geteuid() == 0:
        raise RuntimeError("Run as the frappe bench owner, not root.")
    config = json.loads((TARGET / "site_config.json").read_text())
    if not (config.get("db_name") == DATABASE and config.get("db_user") == DATABASE
            and config.get("mute_emails") and config.get("allow_tests")
            and config.get("db_socket") == str(SOCKET)
            and config.get("grc_performance_fixture") == 1):
        raise RuntimeError("Only the separate muted grc-perf.local fixture site is allowed.")
    return config


def prepare():
    """Clone once. Refuse to overwrite an unrecognized site/database."""
    import pymysql
    if os.geteuid() == 0:
        raise RuntimeError("Run as the frappe bench owner, not root.")
    config = source_config()
    if TARGET.exists():
        guard()
        print(json.dumps({"site": SITE, "existing": True}))
        return
    connection = pymysql.connect(user="frappe", unix_socket=str(SOCKET), autocommit=True)
    password = secrets.token_urlsafe(32)
    with connection.cursor() as cursor:
        cursor.execute("SHOW DATABASES LIKE %s", (DATABASE,))
        if cursor.fetchone():
            raise RuntimeError("Unrecognized existing performance database; refusing to overwrite it.")
        cursor.execute("CREATE DATABASE `grc_perf_local` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (DATABASE, password))
        cursor.execute("GRANT ALL PRIVILEGES ON `grc_perf_local`.* TO %s@'localhost'", (DATABASE,))
    connection.close()
    dump = subprocess.Popen(["mariadb-dump", "--no-defaults", "--user=frappe",
        "--socket=" + str(SOCKET), "--single-transaction", "--skip-lock-tables", "grc_local"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    restore = subprocess.run(["mariadb", "--no-defaults", "--user=frappe",
        "--socket=" + str(SOCKET), DATABASE], stdin=dump.stdout, capture_output=True)
    dump.stdout.close()
    dump.wait()
    if dump.returncode or restore.returncode:
        raise RuntimeError("Isolated clone failed; inspect the local database, do not publish dump output.")
    TARGET.mkdir(mode=0o700)
    for name in ("private", "public", "locks", "logs"):
        (TARGET / name).mkdir(mode=0o700)
    # Keep representative local fixture files available for authorized PDF checks.
    for name in ("private/files", "public/files"):
        if (SOURCE / name).exists():
            shutil.copytree(SOURCE / name, TARGET / name)
    config.update(db_name=DATABASE, db_user=DATABASE, db_password=password,
        mute_emails=1, allow_tests=1, pause_scheduler=1, grc_performance_fixture=1,
        host_name="http://127.0.0.1:8012")
    path = TARGET / "site_config.json"
    path.write_text(json.dumps(config, indent=2))
    path.chmod(0o600)
    print(json.dumps({"site": SITE, "created": True, "isolated_database": DATABASE}))


def connect():
    guard()
    os.chdir(ROOT / "sites")
    import frappe
    frappe.init(site=SITE)
    frappe.connect()
    frappe.set_user("Administrator")
    return frappe


def metadata():
    frappe = connect()
    import platform
    import importlib.metadata
    from ia_maturity import __version__
    try:
        counts = {doctype: frappe.db.count(doctype) for doctype in (
            "User", "IA Maturity Entity", "IA Maturity Assessment",
            "GRC Assessment Assignment", "GRC Activity", "IA Maturity Action")}
        result = {"site": SITE, "app_version": __version__, "frappe_version": frappe.__version__,
            "python": platform.python_version(), "gunicorn": importlib.metadata.version("gunicorn"),
            "logical_cpus": os.cpu_count(), "database_version": frappe.db.sql("select version()")[0][0],
            "counts": counts, "mail_muted": True, "environment": "local isolated synthetic fixture"}
        print(json.dumps(result))
    finally:
        frappe.destroy()


def serve(port, app_root, workers):
    guard()
    if not 8011 <= port <= 8014:
        raise ValueError("Use only dedicated loopback performance ports 8011-8014.")
    candidate = Path(app_root).resolve()
    allowed = {ROOT / "apps/ia_maturity", ROOT / "diagnostics/performance-20261113/baseline-app"}
    if candidate not in allowed or not (candidate / "ia_maturity/hooks.py").is_file():
        raise ValueError("Use only the current checkout or the retained local baseline snapshot.")
    sys.path.insert(0, str(candidate))
    os.chdir(ROOT / "sites")
    import frappe
    from frappe import app
    from frappe.database.database import Database
    from gunicorn.app.base import BaseApplication
    from werkzeug.middleware.shared_data import SharedDataMiddleware

    app._site = SITE
    app._sites_path = str(ROOT / "sites")
    measured = contextvars.ContextVar("grc_performance_sql", default=None)
    original_sql = Database.sql

    def sql(database, *args, **kwargs):
        stats = measured.get()
        started = time.perf_counter()
        try:
            return original_sql(database, *args, **kwargs)
        finally:
            if stats is not None:
                stats["queries"] += 1
                stats["database_ms"] += (time.perf_counter() - started) * 1000

    Database.sql = sql

    def instrument(environ, start_response):
        stats = {"queries": 0, "database_ms": 0.0}
        token = measured.set(stats)
        started = time.perf_counter()

        def response(status, headers, exc_info=None):
            headers.append(("X-GRC-Perf-SQL-Count", str(stats["queries"])))
            headers.append(("Server-Timing", "app;dur=%.3f, db;dur=%.3f" % (
                (time.perf_counter() - started) * 1000, stats["database_ms"])))
            return start_response(status, headers, exc_info)
        inner = None
        try:
            inner = app.application(environ, response)
            yield from inner
        finally:
            try:
                close = getattr(inner, "close", None)
                if close:
                    close()
            finally:
                measured.reset(token)

    application = SharedDataMiddleware(instrument, {"/assets": str(ROOT / "sites/assets")})
    application = SharedDataMiddleware(application, {"/assets/ia_maturity": str(candidate / "ia_maturity/public")})

    class Server(BaseApplication):
        def load_config(self):
            for key, value in {"bind": "127.0.0.1:" + str(port), "workers": workers,
                "worker_class": "sync", "timeout": 120, "accesslog": None,
                "errorlog": "-", "preload_app": True}.items():
                self.cfg.set(key, value)

        def load(self):
            return application

    print(json.dumps({"site": SITE, "port": port, "workers": workers,
        "app_root": str(candidate), "instrumentation": "local-only SQL count and timings"}), flush=True)
    runtime = ROOT / "diagnostics/performance-20261113"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / ("gunicorn-" + str(port) + ".pid")).write_text(str(os.getpid()))
    Server().run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "metadata", "serve"))
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--app-root", default=str(ROOT / "apps/ia_maturity"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "metadata":
        metadata()
    else:
        serve(args.port, args.app_root, args.workers)


if __name__ == "__main__":
    main()
