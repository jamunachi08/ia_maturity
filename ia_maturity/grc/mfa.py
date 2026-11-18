"""Staff MFA using native OTP secrets; customers always use email OTP."""
import hashlib
import re
import secrets
import frappe
from frappe import _
from frappe.utils import cint
from ia_maturity.grc import security as sec

from ia_maturity.grc.account_security import MFA_ROLE


def required(user=None):
    user = user or frappe.session.user
    kind = sec.account_type(user)
    # Customers use email OTP exclusively. Retain historic authenticator secrets
    # without allowing old password/MFA policy to redirect them to a password.
    if kind == "Customer":
        return False
    if kind not in {"Customer", "Auditor"}:
        return False
    from ia_maturity.grc.account_security import desired
    from frappe.twofactor import two_factor_is_enabled_for_
    return desired(frappe.get_doc("User", user)) or bool(two_factor_is_enabled_for_(user))


def configured():
    return bool(cint(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))
        and frappe.db.get_single_value("System Settings", "two_factor_method") in {"OTP App", "Email"})


def status():
    if sec.account_type() == "Customer":
        return {"available": False, "required": False, "enrolled": False,
            "method": "Email OTP", "centralized": False, "optional_enrolled": False,
            "policy": "Email OTP", "can_enroll": False, "customer_otp_only": True}
    from frappe.twofactor import get_default
    from ia_maturity.grc.account_security import effective_policy
    from ia_maturity.grc.mfa_policy import policy as central_policy, method
    doc = frappe.get_doc("User", frappe.session.user)
    central = central_policy()
    override = effective_policy(doc)
    effective = override if override != "Default" else central or "Disabled"
    needs = required()
    return {"available": configured(), "required": needs,
        "enrolled": bool(cint(get_default(frappe.session.user + "_otplogin"))),
        "method": method(), "centralized": bool(central),
        "optional_enrolled": bool(cint(doc.get("grc_mfa_opt_in"))),
        "policy": effective,
        "can_enroll": sec.account_type() == "Auditor" and configured() and not needs
                       and effective == "Enabled"}


def pending_key():
    identity = frappe.local.site + ":" + frappe.session.user + ":" + str(frappe.session.sid)
    return "grc:mfa-enrollment:" + hashlib.sha256(identity.encode()).hexdigest()


def require_customer():
    sec.require_login()
    if sec.account_type() == "Customer":
        frappe.throw(_("Customers sign in with an email verification code. Authenticator setup is not required."), frappe.PermissionError)
    from ia_maturity.grc.mfa_policy import policy as central_policy, method
    central = central_policy()
    if not sec.enabled() or sec.account_type() != "Auditor":
        sec.deny()
    from ia_maturity.grc.account_security import effective_policy
    if central != "Enabled" or effective_policy(frappe.get_doc("User", frappe.session.user)) != "Default":
        frappe.throw(_("Your administrator manages MFA for this account."), frappe.PermissionError)
    if not configured() or method() != "OTP App":
        frappe.throw(_("Authenticator enrollment requires OTP App MFA in System Settings."))
    if required():
        frappe.throw(_("An authenticator is already required. Contact your administrator for recovery."))


@frappe.whitelist(methods=["POST"])
def begin_authenticator(current_password):
    require_customer()
    from ia_maturity.grc.auth import limit
    from frappe.utils.password import check_password, encrypt
    from frappe.twofactor import get_qr_svg_code
    import pyotp
    limit("mfa-enrollment", frappe.session.user, 5, seconds=900)
    if not current_password:
        frappe.throw(_("Enter your current password."))
    check_password(frappe.session.user, current_password, delete_tracker_cache=False)
    from ia_maturity.grc.mfa_policy import revision
    # Pending secrets are encrypted, session-bound and expire before they affect login.
    secret = pyotp.random_base32()
    token = secrets.token_urlsafe(32)
    frappe.cache.set_value(pending_key(), {"secret": encrypt(secret), "token": token, "revision": revision()}, expires_in_sec=600)
    issuer = frappe.db.get_single_value("System Settings", "otp_issuer_name") or "AlphaX GRC"
    uri = pyotp.TOTP(secret).provisioning_uri(frappe.session.user, issuer_name=issuer)
    return {"qr_code": "data:image/svg+xml;base64," + get_qr_svg_code(uri).decode(),
        "setup_token": token, "expires_in": 600}


@frappe.whitelist(methods=["POST"])
def confirm_authenticator(setup_token, code):
    require_customer()
    from ia_maturity.grc.auth import limit
    from frappe.utils.password import decrypt, encrypt
    from frappe.twofactor import set_default
    from frappe.sessions import clear_sessions
    import pyotp
    limit("mfa-confirm", frappe.session.user, 8, seconds=900)
    key = pending_key()
    with frappe.cache.lock(key + ":lock", timeout=15):
        pending = frappe.cache.get_value(key)
        if not pending or not secrets.compare_digest(str(setup_token or ""), pending["token"]):
            frappe.throw(_("Authenticator setup expired. Start again."))
        from ia_maturity.grc.mfa_policy import revision
        if pending.get("revision", "") != revision():
            frappe.throw(_("Authenticator setup expired. Start again."))
        secret = decrypt(pending["secret"])
        if not re.fullmatch(r"[0-9]{6}", str(code or "")) or not pyotp.TOTP(secret).verify(str(code)):
            frappe.throw(_("Enter the current six-digit authenticator code."))
        user = frappe.session.user
        from ia_maturity.grc.mfa_policy import lock_settings
        lock_settings()
        require_customer()
        if pending.get("revision", "") != revision():
            frappe.throw(_("Authenticator setup expired. Start again."))
        frappe.db.sql("select name from `tabUser` where name=%s for update", user)
        # Another session may have completed enrollment while this one was open.
        if required():
            frappe.throw(_("An authenticator is already required. Contact your administrator for recovery."))
        with sec.service_write():
            doc = frappe.get_doc("User", user)
            from ia_maturity.grc.mfa_policy import policy as central_policy
            if central_policy():
                doc.grc_mfa_opt_in = 1
            else:
                doc.grc_mfa_policy = "Required"
            doc.append("roles", {"role": MFA_ROLE})
            doc.save(ignore_permissions=True)
        # These are Frappe's own encrypted defaults consumed by native password MFA.
        set_default(user + "_otpsecret", encrypt(secret))
        set_default(user + "_otplogin", 1)
        frappe.clear_cache(user=user)
        frappe.cache.delete_value(key)
        sec.log("Authenticator enabled", details={"user": user})
        clear_sessions(user=user, keep_current=False, force=True)
        manager = getattr(frappe.local, "login_manager", None)
        if manager and getattr(frappe.local, "request", None):
            manager.logout()
        return {"enabled": True, "redirect": "/login?mfa=1"}


FRAPPE_2FA_SUFFIXES = ("_usr", "_pwd", "_otp_secret", "_token")


def frappe_2fa_value(tmp_id, suffix):
    """Read a value Frappe cached for a pending 2FA login (see frappe.twofactor.cache_2fa_data).

    Current Frappe v15/v16 store these with cache.set_value (site-prefixed and serialised);
    older releases used raw cache.set. Reading only the raw key returns None on current
    releases, which rejected every staff MFA login. expires=True keeps the value out of the
    per-request local cache so a consumed challenge cannot be read back.
    """
    key = tmp_id + suffix
    value = frappe.cache.get_value(key, expires=True)
    if value is None:
        value = frappe.cache.get(key)
    return frappe.safe_decode(value) if isinstance(value, bytes) else value


def forget_frappe_2fa(tmp_id):
    """Consume a 2FA challenge in both storage styles so it can never be replayed."""
    keys = [tmp_id + suffix for suffix in FRAPPE_2FA_SUFFIXES]
    frappe.cache.delete_value(keys)
    frappe.cache.delete(*keys)


def challenge_key(tmp_id):
    return "grc:mfa-challenge:" + frappe.local.site + ":" + tmp_id


def remember_login_challenge(response):
    """Retain server proof before core consumes an email HOTP counter.

    Frappe verifies the emailed code before on_login and deletes its counter.
    A separate, expiring server-only record allows our hook to verify it again
    under the same one-use lock as authenticator challenges.
    """
    if getattr(response, "status_code", 200) != 200 or frappe.form_dict.get("otp"):
        return
    payload = response.get_json(silent=True) if getattr(response, "mimetype", "") == "application/json" else None
    if not isinstance(payload, dict) or not payload.get("verification"):
        return
    tmp_id = payload.get("tmp_id")
    if not isinstance(tmp_id, str) or not re.fullmatch(r"[A-Za-z0-9]{8}", tmp_id):
        return
    user = frappe_2fa_value(tmp_id, "_usr")
    if not user or sec.account_type(user) not in {"Customer", "Auditor"}:
        return
    from ia_maturity.grc.mfa_policy import method, revision
    token = frappe_2fa_value(tmp_id, "_token")
    selected = method()
    if selected not in {"OTP App", "Email"} or (selected == "Email" and token is None):
        return
    frappe.cache.set_value(challenge_key(tmp_id), {
        "user": user, "method": selected, "revision": revision(),
        "token": int(token) if token is not None else None,
    }, expires_in_sec=300 if selected == "Email" else 180)
    response.headers["Cache-Control"] = "no-store"


def validate_login_challenge(user):
    """Validate password-bound, unexpired, single-use authenticator/email proof."""
    from frappe.twofactor import get_default
    from frappe.utils.password import decrypt
    from ia_maturity.grc.identity import matches_password
    from ia_maturity.grc.mfa_policy import policy as central_policy, method, revision
    from ia_maturity.grc.auth import limit
    import pyotp
    tmp_id = frappe.form_dict.get("tmp_id")
    code = frappe.form_dict.get("otp")

    def reject():
        frappe.throw(_("This account must sign in using a password and valid verification code."),
                     frappe.AuthenticationError)

    if not configured() or not isinstance(tmp_id, str) or not re.fullmatch(r"[A-Za-z0-9]{8}", tmp_id):
        reject()
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
        reject()
    limit("mfa-challenge", tmp_id, 5, seconds=300)
    with frappe.cache.lock(challenge_key(tmp_id) + ":lock", timeout=15):
        proof = frappe.cache.get_value(challenge_key(tmp_id))
        selected = method()
        if proof:
            if proof.get("user") != user or proof.get("method") != selected or proof.get("revision") != revision():
                reject()
        elif central_policy() or selected == "Email":
            reject()
        cached_user = frappe_2fa_value(tmp_id, "_usr")
        cached_password = frappe_2fa_value(tmp_id, "_pwd")
        cached_secret = frappe_2fa_value(tmp_id, "_otp_secret")
        stored_secret = get_default(user + "_otpsecret")
        if (cached_user != user or not isinstance(cached_password, str) or not cached_password
                or not isinstance(cached_secret, str) or not cached_secret or not stored_secret):
            reject()
        if not secrets.compare_digest(cached_secret, decrypt(stored_secret)):
            reject()
        if not matches_password(user, cached_password):
            reject()
        if selected == "Email":
            token = proof.get("token")
            if token is None or not pyotp.HOTP(cached_secret).verify(code, int(token)):
                reject()
        elif not pyotp.TOTP(cached_secret).verify(code):
            reject()
        forget_frappe_2fa(tmp_id)
        frappe.cache.delete_value(challenge_key(tmp_id))
        frappe.flags.grc_validated_mfa_user = user


def stamp_session(login_manager):
    """Persist only server-validated proof in the native session, never a browser flag."""
    if sec.enabled() and sec.account_type(login_manager.user) == "Customer":
        if frappe.flags.get("grc_consumed_customer_otp") != login_manager.user:
            login_manager.logout()
            frappe.throw(_("Sign in again with an email verification code."), frappe.AuthenticationError)
        frappe.session.data.grc_customer_otp_user = login_manager.user
        frappe.local.session_obj.update(force=True)
        return
    if not sec.enabled() or not required(login_manager.user):
        return
    if frappe.flags.get("grc_validated_mfa_user") != login_manager.user:
        login_manager.logout()
        frappe.throw(_("Sign in again and validate your verification code."), frappe.AuthenticationError)
    frappe.session.data.grc_validated_mfa_user = login_manager.user
    frappe.local.session_obj.update(force=True)
    frappe.flags.pop("grc_validated_mfa_user", None)


def require_verified_session():
    """No API-key/OAuth or older unverified session may bypass required portal MFA."""
    if sec.account_type() == "Customer":
        from ia_maturity.grc.auth import require_customer_otp_session
        return require_customer_otp_session()
    if not required():
        return
    if frappe.get_request_header("Authorization"):
        frappe.throw(_("This account requires a password and verified MFA session."), frappe.AuthenticationError)
    data = frappe.session.get("data") or {}
    if data.get("grc_validated_mfa_user") == frappe.session.user and frappe.session.get("sid") not in {None, "Guest"}:
        return
    frappe.local.login_manager.logout()
    if frappe.form_dict.get("cmd") == "ia_maturity.grc.api.bootstrap" or frappe.request.path in {
            "/login", "/api/method/ia_maturity.grc.api.bootstrap", "/api/method/logout"}:
        return
    frappe.throw(_("Sign in again and validate your verification code."), frappe.AuthenticationError)
