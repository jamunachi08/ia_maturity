"""Local-only browser acceptance server with a non-network SMTP sink.

This is a test runner, never a product mail fallback. It does not change any
site/email configuration. Native queue construction, immediate send and status
updates still execute; only SMTP transport is replaced for reserved test users.
Use the regular server and a real outgoing account for actual inbox delivery.
"""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
RESERVED = re.compile(r"(?:grc-journey-[a-z0-9-]+@example\.test|(?:auditor|reviewer|admin|unassigned)@grc\.example\.test)\Z")


def require_local():
    import frappe
    if not (frappe.local.site == "grc.local" and frappe.conf.db_name == "grc_local"
            and frappe.conf.get("mute_emails") and frappe.conf.get("allow_tests")
            and frappe.conf.db_socket == str(ROOT / "sites/.grc-db/mysql.sock")):
        raise RuntimeError("Only the isolated muted grc.local acceptance site is allowed.")


class ReservedSMTP:
    def sendmail(self, from_addr, to_addrs, msg):
        require_local()
        recipients = [to_addrs] if isinstance(to_addrs, str) else list(to_addrs)
        if not recipients or any(not RESERVED.fullmatch(email) for email in recipients):
            raise RuntimeError("The local SMTP sink rejects non-fixture recipients.")
        if not isinstance(msg, bytes):
            raise TypeError("Native SMTP MIME bytes required.")
        # SMTP success, never network delivery. The native Email Queue retains
        # the actual MIME for the guarded verification/PDF assertion helpers.
        return {}


def transport_patches(stack):
    import frappe
    from frappe.email.doctype.email_account.email_account import EmailAccount

    def account(*args, **kwargs):
        require_local()
        return frappe.get_doc({"doctype": "Email Account", "name": "_Test Demo SMTP Sink",
            "email_id": "verification@example.test", "enable_outgoing": 1,
            "default_outgoing": 1, "append_emails_to_sent_folder": 0})

    def unmuted():
        require_local()
        return False

    def smtp(self):
        require_local()
        return SimpleNamespace(session=ReservedSMTP())

    def email_ready():
        # The reserved transport is configured for this test process only.
        # Keep the persisted site muted and preserve the real product readiness
        # check everywhere outside this explicitly guarded acceptance runner.
        require_local()
        return True

    stack.enter_context(patch.object(EmailAccount, "find_outgoing", staticmethod(account)))
    stack.enter_context(patch.object(EmailAccount, "get_smtp_server", smtp))
    stack.enter_context(patch("frappe.are_emails_muted", unmuted))
    stack.enter_context(patch("ia_maturity.grc.mfa_policy.email_ready", email_ready))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--deliver", help="Deliver one reserved fixture Email Queue record to the local sink.")
    args = parser.parse_args()
    if os.geteuid() == 0 or not 8006 <= args.port <= 8010:
        raise SystemExit("Run as frappe on a dedicated local acceptance port 8006-8010.")
    os.chdir(ROOT / "sites")
    import frappe
    frappe.init(site="grc.local")
    frappe.connect()
    require_local()
    if args.deliver:
        with ExitStack() as stack:
            transport_patches(stack)
            queue = frappe.get_doc("Email Queue", args.deliver)
            if not queue.recipients or any(not RESERVED.fullmatch(r.recipient) for r in queue.recipients):
                raise RuntimeError("Only reserved fixture messages may be delivered.")
            queue.send()
            queue.reload()
            if queue.status != "Sent":
                raise RuntimeError("Fixture message was not accepted by the local SMTP sink.")
            print("Reserved fixture email accepted by the local SMTP sink.")
        frappe.destroy()
        return
    frappe.destroy()
    from frappe import app
    from werkzeug.serving import run_simple
    app._site = "grc.local"
    app._sites_path = str(ROOT / "sites")
    # Silence URLs containing private invitation/verification tokens in test logs.
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    with ExitStack() as stack:
        transport_patches(stack)
        print("Local acceptance server: reserved SMTP sink, site remains muted, no external delivery.", flush=True)
        run_simple("127.0.0.1", args.port, app.application_with_statics(),
                   threaded=True, use_reloader=False, use_debugger=False)


if __name__ == "__main__":
    main()
