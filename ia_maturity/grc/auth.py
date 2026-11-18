"""Customer-only, single-use email verification. Staff use Frappe password + MFA."""
from contextlib import contextmanager
import hashlib
import re
import secrets
import frappe
from frappe import _
from frappe.utils import add_to_date, cint, escape_html, get_url, now_datetime, today
from ia_maturity.grc import security as sec
from ia_maturity.grc.email_policy import check_email

REG = "IA Maturity Registration"


@contextmanager
def verified_signup(email):
    previous = frappe.flags.get("grc_verified_signup_email")
    frappe.flags.grc_verified_signup_email = email
    try:
        yield
    finally:
        frappe.flags.grc_verified_signup_email = previous


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sign_up(email, full_name, redirect_to=None):
    if sec.enabled():
        frappe.throw(_("Use the GRC signup page and verify your email to create an account."), frappe.PermissionError)
    from frappe.core.doctype.user.user import sign_up as core_sign_up
    return core_sign_up(email, full_name, redirect_to)



def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def rate_limit_exceeded(seconds):
    # Return only a wait duration, never account eligibility or remaining attempts.
    frappe.local.response["retry_after_seconds"] = max(1, cint(seconds))
    frappe.throw(_("Too many attempts. Please try again later."), frappe.RateLimitExceededError)


def limit(kind, identifier, maximum, seconds=3600):
    if kind in {"request-ip", "verify-ip"}:
        from ia_maturity.grc.verification_limits import limit_enabled
        if not limit_enabled("ip"):
            return
    key = f"grc:{frappe.local.site}:{kind}:{digest(identifier)}"
    count = frappe.cache.incr(key)
    if count == 1:
        frappe.cache.expire(key, seconds)
    if count > maximum:
        rate_limit_exceeded(frappe.cache.ttl(key))


# Both email limits must be checked and reserved together. Rejected retries do
# not consume another hourly slot, and concurrent sends cannot both pass.
CODE_REQUEST_LIMIT = """
local count = tonumber(redis.call('GET', KEYS[1]) or '0')
local hourly_ttl = redis.call('TTL', KEYS[1])
if count >= 5 then
    if hourly_ttl < 0 then
        redis.call('EXPIRE', KEYS[1], 3600)
        hourly_ttl = 3600
    end
    return {0, math.max(1, hourly_ttl)}
end
if redis.call('EXISTS', KEYS[2]) == 1 then
    local cooldown_ttl = redis.call('TTL', KEYS[2])
    if cooldown_ttl < 0 then
        redis.call('EXPIRE', KEYS[2], 60)
        cooldown_ttl = 60
    end
    return {0, math.max(1, cooldown_ttl)}
end
count = redis.call('INCR', KEYS[1])
if count == 1 or hourly_ttl < 0 then redis.call('EXPIRE', KEYS[1], 3600) end
redis.call('SET', KEYS[2], 1, 'EX', 60)
return {1, 60}
"""


def code_request_limit(email):
    from ia_maturity.grc.verification_limits import limit_enabled
    if not limit_enabled("email"):
        return
    identity = digest(email)
    keys = [f"grc:{frappe.local.site}:{kind}:{identity}" for kind in ("request-email", "request-cooldown")]
    allowed, wait = frappe.cache.eval(CODE_REQUEST_LIMIT, 2, *keys)
    if not allowed:
        rate_limit_exceeded(wait)


def send_immediately(**kwargs):
    """Queue an email and deliver it before returning, so the caller can confirm it was sent.

    frappe.sendmail(now=True) used to send inside the call. Current Frappe v15/v16 defer it
    until after the transaction commits (frappe.db.after_commit), so the status read straight
    after the call was always "Not Sent" and every customer verification request failed.
    Queue the message, then run the queue's own send(): same SMTP path, retry bookkeeping and
    mute/suspend checks, just synchronous. A muted or suspended site leaves it unsent.
    """
    queue = frappe.sendmail(delayed=True, now=False, **kwargs)
    if isinstance(queue, list):
        queue = queue[0] if queue else None
    if queue:
        queue.send()
    return queue


@frappe.whitelist(allow_guest=True, methods=["POST"])
def request_code(email, purpose="Resume", full_name=None, language="en", consent=0, organization_name=None, organization_sector=None, onboarding_token=None, onboarding_invitation=None):
    if not sec.enabled():
        sec.deny()
    language = "ar" if language == "ar" else "en"
    email = check_email(email)
    limit("request-ip", getattr(frappe.local, "request_ip", None) or "local", 30)
    generic = {"message": _("If eligible, you will receive a verification email. Customers sign in with an email code. Staff must use staff sign-in."),
        "resend_after_seconds": 60, "expires_in_seconds": 900}
    exists = frappe.db.exists("User", email)
    if exists and (sec.account_type(email) != "Customer" or not frappe.db.get_value("User", email, "enabled")):
        code_request_limit(email)
        return generic
    if purpose != "Start" and not exists:
        code_request_limit(email)
        return generic
    from ia_maturity.grc import onboarding
    invitation = onboarding.registration_invitation(email, onboarding_token, onboarding_invitation)
    organization = None
    if purpose == "Start" and (not full_name or not cint(consent)):
        frappe.throw(_("Enter your name and accept the privacy notice and terms."))
    if purpose == "Start":
        check_email(email, new_account=not exists)
        from ia_maturity.grc.identity import validate_name
        validate_name(full_name.strip(), required=True, user=email if exists else None)
        from ia_maturity.grc.organizations import validate_signup_organization
        # Sector belongs to the workbook company profile, after email verification.
        # Older clients may still supply it; the organization service validates it.
        if not invitation:
            organization = validate_signup_organization(organization_name, organization_sector)
    # Invalid signup fields do not reserve an email slot. All requests still
    # count against the IP limit, and ineligible addresses keep neutral limits.
    code_request_limit(email)
    code, link = f"{secrets.randbelow(10**6):06d}", secrets.token_urlsafe(32)
    with frappe.cache.lock(f"grc:registration:{frappe.local.site}:{digest(email)}", timeout=15):
        for name in frappe.get_all(REG, filters={"email": email, "status": "Pending"}, pluck="name"):
            frappe.db.set_value(REG, name, "status", "Expired")
        reg = frappe.get_doc(dict(doctype=REG, email=email,
            full_name=(full_name or email.split("@")[0])[:140],
            entity_name=organization["entity_name"] if organization else "Pending organization setup",
            grc_organization_signup=int(bool(organization)),
            grc_organization_sector=organization["sector"] if organization else "",
            purpose="Start" if purpose == "Start" else "Resume", language=language,
            assessment_date=today(), consent=cint(consent), status="Pending",
            code_hash=digest(code), link_key_hash=digest(link), attempts=0,
            expires_on=add_to_date(now_datetime(), minutes=15),
            ip_address=getattr(frappe.local, "request_ip", None))).insert(ignore_permissions=True)
    # Native SMTP commits before delivery. Persist invitation binding first so
    # even a quickly opened email cannot take the public-signup path.
    onboarding.registration_started(invitation, reg)
    url = get_url("/login?verify=" + link, allow_header_override=False)
    intro = "رمز التحقق الخاص بك" if language == "ar" else "Your verification code"
    team = '<p>' + escape_html(onboarding.team_label(invitation)) + '</p>' if invitation else ''
    try:
        sent = send_immediately(recipients=[email], subject=f"AlphaX | {intro}",
        message=f'<div dir="{"rtl" if language == "ar" else "ltr"}"><h2>{intro}</h2>'
        + team +
        f'<p style="font-size:28px;letter-spacing:6px">{code}</p>'
        f'<p><a href="{escape_html(url)}">{"تأكيد البريد الإلكتروني والمتابعة" if language == "ar" else "Verify email and continue"}</a></p>'
        '<p>15 minutes · Single use / صالح لمدة 15 دقيقة ولمرة واحدة</p></div>',
        reference_doctype=REG, reference_name=reg.name)
        # EmailQueue.send updates the database, not the returned document's status.
        # Do not report success when site-wide muting/suspension skipped SMTP.
        if not sent:
            raise frappe.OutgoingEmailError("No verification email was created")
        sent.reload()
        if sent.status != "Sent":
            raise frappe.OutgoingEmailError("Verification email was not sent")
    except Exception:
        # Native SMTP sending commits the registration before contacting the mail
        # server. Persist invalidation even though the request raises, and prevent
        # scheduled retries from delivering a code the user was told had failed.
        frappe.db.set_value(REG, reg.name, "status", "Expired")
        frappe.db.set_value("Email Queue", {"reference_doctype": REG, "reference_name": reg.name,
            "status": ["in", ["Not Sent", "Partially Sent", "Error"]]}, "status", "Expired")
        frappe.db.commit()
        frappe.log_error(title="GRC verification email delivery failure")
        frappe.throw(_("Verification email could not be sent. Please try again later or contact support."), frappe.OutgoingEmailError)
    return generic


def consume(name, code=None, link_key=None):
    frappe.db.sql("select name from `tabIA Maturity Registration` where name=%s for update", name)
    reg = frappe.get_doc(REG, name)
    if reg.status != "Pending" or now_datetime() > reg.expires_on:
        frappe.throw(_("This verification has expired. Request a new code."))
    submitted = digest(link_key) if link_key else digest(code)
    expected = reg.link_key_hash if link_key else reg.code_hash
    if not secrets.compare_digest(submitted, expected or ""):
        attempts = cint(reg.attempts) + 1
        reg.db_set({"attempts": attempts, "status": "Blocked" if attempts >= 5 else "Pending"})
        frappe.db.commit()
        frappe.throw(_("The code is invalid or expired."))
    if frappe.db.exists("User", reg.email):
        if sec.account_type(reg.email) != "Customer" or not frappe.db.get_value("User", reg.email, "enabled"):
            sec.deny()
        user = reg.email
    else:
        check_email(reg.email, new_account=True)
        with sec.service_write(), verified_signup(reg.email):
            parts = reg.full_name.partition(" ")
            doc = frappe.get_doc(dict(doctype="User", email=reg.email, first_name=parts[0],
                last_name=parts[2], enabled=1, user_type="Website User",
                grc_account_type="Customer", grc_email_verified=1, send_welcome_email=0, language=reg.language,
                roles=[{"role": "GRC Customer"}, {"role": "IA Assessment Respondent"}]))
            doc.flags.no_welcome_mail = True
            doc.insert(ignore_permissions=True)
            user = doc.name
            from ia_maturity.grc.organizations import create_verified_signup_organization
            create_verified_signup_organization(reg, user)
    from ia_maturity.grc.onboarding import verified as onboarding_verified
    onboarding_verified(reg, user)
    frappe.db.set_value("User", user, "grc_email_verified", 1)
    frappe.clear_cache(user=user)
    reg.db_set({"status": "Verified", "user": user, "verified_on": now_datetime()})
    # No generic login_as endpoint: only a consumed customer verification can reach this.
    manager = getattr(frappe.local, "login_manager", None)
    previous = frappe.flags.get("grc_consumed_customer_otp")
    frappe.flags.grc_consumed_customer_otp = user
    try:
        if manager and getattr(frappe.local, "request", None):
            manager.login_as(user)
        else:
            frappe.set_user(user)
    finally:
        frappe.flags.grc_consumed_customer_otp = previous
    return {"redirect": "/grc/customer/onboarding" if reg.get("grc_onboarding_invitation") else "/grc/customer", "user": user}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_code(email, code):
    if not sec.enabled():
        sec.deny()
    email = (email or "").strip().lower()
    limit("verify-ip", getattr(frappe.local, "request_ip", None) or "local", 60)
    if not re.fullmatch(r"[0-9]{6}", str(code or "")):
        frappe.throw(_("Enter the six-digit verification code."))
    name = frappe.db.get_value(REG, {"email": email, "status": "Pending"}, "name", order_by="creation desc")
    if not name:
        frappe.throw(_("The code is invalid or expired."))
    return consume(name, code=code)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_link(link_key):
    if not sec.enabled():
        sec.deny()
    limit("verify-ip", getattr(frappe.local, "request_ip", None) or "local", 60)
    if not link_key or len(link_key) > 128:
        sec.deny()
    name = frappe.db.get_value(REG, {"link_key_hash": digest(link_key), "status": "Pending"}, "name")
    if not name:
        frappe.throw(_("This link is invalid or expired."))
    return consume(name, link_key=link_key)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password(new_password, logout_all_sessions=0, key=None, old_password=None):
    """Use native reset proof and password policy without creating a GRC session."""
    from frappe.core.doctype.user import user as core
    if not sec.enabled():
        return core.update_password(new_password, logout_all_sessions, key, old_password)
    if not key and not old_password:
        frappe.throw(_("A valid reset link or current password is required."), frappe.AuthenticationError)
    res = core._get_user_for_update_password(key, old_password)
    if res.get("message"):
        frappe.local.response.http_status_code = 410
        return res["message"]
    user = res["user"]
    if sec.account_type(user) == "Customer":
        frappe.throw(_("Customers sign in with an email verification code. Password access is disabled."), frappe.AuthenticationError)
    if sec.account_type(user) not in {"Customer", "Auditor"}:
        return core.update_password(new_password, logout_all_sessions, key, old_password)
    # Serialize single-use reset links and recheck their native expiry after locking.
    locked = frappe.db.sql("select reset_password_key from `tabUser` where name=%s for update", user)
    if key and (not locked or locked[0][0] != core.sha256_hash(key)):
        frappe.local.response.http_status_code = 410
        return _("The reset password link has either been used before or is invalid")
    res = core._get_user_for_update_password(key, old_password)
    if res.get("message"):
        frappe.local.response.http_status_code = 410
        return res["message"]
    if not isinstance(new_password, str) or not 10 <= len(new_password) <= core.MAX_PASSWORD_SIZE:
        frappe.throw(_("Use at least 10 characters within the maximum password length."))
    doc = frappe.get_doc("User", user)
    from ia_maturity.grc.identity import validate_password_name
    validate_password_name(doc, new_password)
    result = core.test_password_strength(new_password, user_data=(
        doc.first_name, doc.middle_name, doc.last_name, doc.email, doc.birth_date))
    feedback = result.get("feedback")
    if feedback and not feedback.get("password_policy_validation_passed", False):
        core.handle_password_test_fail(feedback)
    doc.validate_reset_password()
    from frappe.utils.password import update_password
    from frappe.sessions import clear_sessions
    from frappe.utils import today
    update_password(user, new_password, logout_all_sessions=True)
    frappe.db.set_value("User", user, {
        "reset_password_key": "", "redirect_url": "", "last_password_reset_date": today()})
    frappe.cache.hdel("redirect_after_login", user)
    clear_sessions(user=user, keep_current=False, force=True)
    if frappe.session.user == user:
        frappe.local.login_manager.logout()
    frappe.local.response.pop("home_page", None)
    frappe.local.response.pop("redirect_to", None)
    return "/login"


def enforce_staff_mfa(login_manager):
    """Validate and consume a native challenge before Frappe can make a session."""
    from ia_maturity.grc.mfa import required, validate_login_challenge
    if not sec.enabled():
        return
    if sec.account_type(login_manager.user) == "Customer":
        if frappe.flags.get("grc_consumed_customer_otp") != login_manager.user:
            frappe.throw(_("Customers sign in with an email verification code. Password access is disabled."), frappe.AuthenticationError)
        return
    if required(login_manager.user):
        validate_login_challenge(login_manager.user)


def require_customer_otp_session():
    """Reject customer passwords, tokens and sessions predating email-only login."""
    if not sec.enabled() or sec.account_type() != "Customer":
        return
    data = frappe.session.get("data") or {}
    if (not frappe.get_request_header("Authorization")
            and data.get("grc_customer_otp_user") == frappe.session.user
            and frappe.session.get("sid") not in {None, "Guest"}):
        return
    manager = getattr(frappe.local, "login_manager", None)
    if manager:
        manager.logout()
    path = getattr(getattr(frappe.local, "request", None), "path", "")
    if frappe.form_dict.get("cmd") in {"logout", "ia_maturity.grc.api.bootstrap"} or path in {
            "/login", "/signup", "/api/method/logout", "/api/method/ia_maturity.grc.api.bootstrap"}:
        return
    frappe.throw(_("Sign in again with an email verification code."), frappe.AuthenticationError)
