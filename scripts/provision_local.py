"""Create grc.local with an isolated development MariaDB, never other sites.

Run with bench Python as the frappe OS user. Database files live in sites/.grc-db.
This development instance uses local Unix-socket authentication and binds loopback.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import pymysql

BENCH = Path(__file__).resolve().parents[3]
SITE = "grc.local"


def start_database():
    directory = BENCH / "sites" / ".grc-db"
    directory.mkdir(mode=0o700, exist_ok=True)
    socket = str(directory / "mysql.sock")
    if not (directory / "mysql").exists():
        subprocess.run(["mariadb-install-db", "--no-defaults", f"--datadir={directory}",
            "--auth-root-authentication-method=socket", "--auth-root-socket-user=frappe",
            "--skip-test-db"], check=True, stdout=subprocess.DEVNULL)
    try:
        connection = pymysql.connect(user="frappe", unix_socket=socket, connect_timeout=2, read_timeout=2)
        connection.close()
        return socket
    except pymysql.Error:
        pass
    log = open(directory / "launcher.log", "ab")
    process = subprocess.Popen(["mariadbd", "--no-defaults", f"--datadir={directory}",
        f"--socket={socket}", "--port=13306", "--bind-address=127.0.0.1",
        f"--pid-file={directory / 'mariadb.pid'}", f"--log-error={directory / 'error.log'}",
        "--character-set-server=utf8mb4", "--collation-server=utf8mb4_unicode_ci",
        "--skip-name-resolve", "--innodb-buffer-pool-size=256M"],
        stdout=log, stderr=log, start_new_session=True)
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError("Local database did not start; inspect sites/.grc-db/error.log")
        try:
            connection = pymysql.connect(user="frappe", unix_socket=socket, connect_timeout=1, read_timeout=1)
            connection.close()
            return socket
        except pymysql.Error:
            time.sleep(1)
    raise RuntimeError("Local database startup timed out")


def main():
    if os.geteuid() == 0:
        raise SystemExit("Run as frappe, not root.")
    os.chdir(BENCH / "sites")
    socket = start_database()
    target = BENCH / "sites" / SITE
    if target.exists():
        print("grc.local already exists; started its local database without changing the site.")
        return
    import frappe
    from frappe.installer import _new_site
    password = secrets.token_urlsafe(24)
    # Save the generated secret before installation so interrupted provisioning is recoverable.
    secret = BENCH / "sites" / ".grc-db" / "credentials.json"
    secret.write_text(json.dumps({"site": SITE, "Administrator": password}, indent=2))
    secret.chmod(0o600)
    frappe.init(site=SITE, new_site=True)
    _new_site(db_name="grc_local", site=SITE, db_root_username="frappe",
        db_root_password="unix-socket-auth", admin_password=password, db_socket=socket,
        install_apps=["erpnext", "ia_maturity"])
    credentials = target / "private" / "grc-local-credentials.json"
    credentials.write_text(secret.read_text())
    credentials.chmod(0o600)
    frappe.destroy()
    print("Created grc.local on its isolated database; credentials saved privately.")


if __name__ == "__main__":
    main()
