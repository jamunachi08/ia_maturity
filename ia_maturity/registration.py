"""Public landing-page sign-up: details -> e-mailed 6-digit code (or link) -> signed in -> pre-filled draft.

Security notes
* The code and the link key are stored only as SHA-256 hashes; codes expire (default 30 minutes) and a
  registration is blocked after 5 wrong codes.
* Requests are rate-limited per e-mail address and per IP address.
* Free e-mail providers can be refused (work e-mail only) and IA Maturity Settings > Allowed Email Domains
  is enforced.
* Accounts with desk access (staff) are never signed in through this flow; they use the normal login.
* Responses never reveal whether an e-mail address already has an account.
"""

import hashlib
import re
import secrets

import frappe
from frappe.utils import add_to_date, cint, escape_html, get_url, getdate, now_datetime, today, validate_email_address

from ia_maturity import i18n
from ia_maturity.branding import get_brand
from ia_maturity.permissions import RESPONDENT, email_domain_allowed

DOCTYPE = "IA Maturity Registration"
MAX_ATTEMPTS = 5
PER_EMAIL_PER_HOUR = 5
PER_IP_PER_HOUR = 30
FIELD_LIMITS = {"full_name": 140, "job_title": 140, "entity_name": 140, "respondent_role": 80}

MESSAGES = {
	"en": {
		"invalid_email": "Enter a valid work e-mail address.",
		"free_email": "Please use your work e-mail address (personal e-mail providers are not accepted).",
		"domain": "This assessment is limited to approved company e-mail domains.",
		"required": "Please complete all required fields.",
		"consent": "Please accept the privacy notice to continue.",
		"too_many": "Too many requests. Please wait a few minutes and try again.",
		"disabled": "Online sign-up is not available. Please contact IRSAA.",
		"staff": "This e-mail belongs to a staff account. Please sign in with your password.",
		"bad_code": "The code is not correct. Please check the e-mail and try again.",
		"expired": "This code has expired. Please request a new one.",
		"blocked": "Too many wrong attempts. Please request a new code.",
		"send_failed": "We could not send the e-mail right now. Please try again shortly.",
		"subject": "AlphaX | Your verification code: {0}",
		"mail_intro": "Use this code to continue to your Internal Audit Maturity Assessment:",
		"mail_or": "Or open your assessment directly:",
		"mail_button": "Continue to my assessment",
		"mail_expiry": "The code is valid for {0} minutes. If you did not request it, you can ignore this e-mail.",
	},
	"ar": {
		"invalid_email": "أدخل بريد عمل إلكترونياً صحيحاً.",
		"free_email": "يُرجى استخدام بريد العمل الإلكتروني (لا تُقبل عناوين البريد الشخصية).",
		"domain": "يقتصر هذا التقييم على نطاقات البريد المعتمدة للجهات.",
		"required": "يُرجى تعبئة جميع الحقول المطلوبة.",
		"consent": "يُرجى الموافقة على إشعار الخصوصية للمتابعة.",
		"too_many": "عدد كبير من الطلبات. يُرجى الانتظار بضع دقائق ثم المحاولة مرة أخرى.",
		"disabled": "التسجيل الإلكتروني غير متاح حالياً. يُرجى التواصل مع IRSAA.",
		"staff": "هذا البريد مرتبط بحساب موظف. يُرجى تسجيل الدخول بكلمة المرور.",
		"bad_code": "الرمز غير صحيح. يُرجى مراجعة البريد والمحاولة مرة أخرى.",
		"expired": "انتهت صلاحية الرمز. يُرجى طلب رمز جديد.",
		"blocked": "محاولات خاطئة كثيرة. يُرجى طلب رمز جديد.",
		"send_failed": "تعذّر إرسال البريد حالياً. يُرجى المحاولة بعد قليل.",
		"subject": "AlphaX | رمز التحقق: {0}",
		"mail_intro": "استخدم هذا الرمز لمتابعة تقييم نضج التدقيق الداخلي:",
		"mail_or": "أو افتح التقييم مباشرة:",
		"mail_button": "المتابعة إلى التقييم",
		"mail_expiry": "الرمز صالح لمدة {0} دقيقة. إذا لم تطلبه فيمكنك تجاهل هذه الرسالة.",
	},
}


def _msg(lang, key, *args):
	text = MESSAGES[i18n.norm_lang(lang)][key]
	return text.format(*args) if args else text


def _hash(value):
	return hashlib.sha256(str(value).encode()).hexdigest()


def _settings():
	return frappe.get_cached_doc("IA Maturity Settings")


def _ip():
	return getattr(frappe.local, "request_ip", None) or "unknown"


def _rate_limit(key, limit):
	"""Simple fixed-window limiter (1 hour) in Redis. Raises when the limit is exceeded."""
	cache_key = f"ia_maturity:rl:{key}"
	count = cint(frappe.cache.get_value(cache_key)) + 1
	frappe.cache.set_value(cache_key, count, expires_in_sec=3600)
	return count <= limit


def free_email_domains():
	raw = _settings().free_email_domains or ""
	return {d.strip().lower().lstrip("@") for d in re.split(r"[\s,;]+", raw) if d.strip()}


def check_email(email, lang):
	email = (email or "").strip().lower()
	if not email or not validate_email_address(email) or len(email) > 140:
		frappe.throw(_msg(lang, "invalid_email"))
	domain = email.split("@")[-1]
	if cint(_settings().block_free_email_domains) and domain in free_email_domains():
		frappe.throw(_msg(lang, "free_email"))
	if not email_domain_allowed(email):
		frappe.throw(_msg(lang, "domain"))
	return email


def _is_staff_account(email):
	if not frappe.db.exists("User", email):
		return False
	if frappe.db.get_value("User", email, "user_type") == "System User":
		return True
	return False


# --------------------------------------------------------------------------- step 1: request a code
@frappe.whitelist(allow_guest=True, methods=["POST"])
def request_code(email, purpose="Start", full_name=None, job_title=None, respondent_role=None,
				 entity_name=None, assessment_date=None, language="en", consent=0):
	lang = i18n.norm_lang(language)
	settings = _settings()
	if not cint(settings.enable_landing_signup):
		frappe.throw(_msg(lang, "disabled"))
	email = check_email(email, lang)
	purpose = "Resume" if purpose == "Resume" else "Start"
	if not (_rate_limit(f"ip:{_ip()}", PER_IP_PER_HOUR) and _rate_limit(f"email:{email}", PER_EMAIL_PER_HOUR)):
		frappe.throw(_msg(lang, "too_many"), frappe.RateLimitExceededError)
	if _is_staff_account(email):
		frappe.throw(_msg(lang, "staff"))

	values = {"full_name": full_name, "job_title": job_title, "respondent_role": respondent_role,
			  "entity_name": entity_name}
	values = {k: (v or "").strip()[: FIELD_LIMITS[k]] for k, v in values.items()}
	if purpose == "Start":
		if not values["full_name"] or not values["entity_name"]:
			frappe.throw(_msg(lang, "required"))
		if not cint(consent):
			frappe.throw(_msg(lang, "consent"))
	else:
		values["full_name"] = values["full_name"] or email.split("@")[0]
		values["entity_name"] = values["entity_name"] or "-"

	# supersede earlier pending codes for this address
	for name in frappe.get_all(DOCTYPE, filters={"email": email, "status": "Pending"}, pluck="name"):
		frappe.db.set_value(DOCTYPE, name, "status", "Expired", update_modified=False)

	code = f"{secrets.randbelow(10**6):06d}"
	link_key = secrets.token_urlsafe(32)
	minutes = cint(settings.verification_code_minutes) or 30
	reg = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"email": email,
			**values,
			"assessment_date": getdate(assessment_date) if assessment_date else today(),
			"language": lang,
			"purpose": purpose,
			"status": "Pending",
			"consent": 1 if purpose == "Start" else 0,
			"code_hash": _hash(code),
			"link_key_hash": _hash(link_key),
			"expires_on": add_to_date(now_datetime(), minutes=minutes),
			"attempts": 0,
			"ip_address": _ip(),
		}
	).insert(ignore_permissions=True)

	if not _send_code_email(email, code, link_key, lang, minutes, reg.name):
		frappe.throw(_msg(lang, "send_failed"))
	return {"registration": reg.name, "email": email, "expires_in_minutes": minutes}


def _send_code_email(email, code, link_key, lang, minutes, reference):
	brand = get_brand()
	link = get_url(f"/ia-assessment?verify={link_key}")
	rtl = lang == "ar"
	body = f"""
	<div dir="{'rtl' if rtl else 'ltr'}" style="font-family:Helvetica,Arial,sans-serif;color:{brand.ink};max-width:560px;text-align:{'right' if rtl else 'left'}">
	 <div style="background:{brand.ink};padding:14px 18px;border-radius:8px 8px 0 0">
	  <img src="{brand.images.logo_white}" alt="{brand.product}" height="40" style="height:40px;width:auto;display:block">
	 </div>
	 <div style="height:4px;background:{brand.primary}"></div>
	 <div style="padding:18px 4px">
	  <p>{escape_html(_msg(lang, 'mail_intro'))}</p>
	  <p style="font-size:30px;font-weight:700;letter-spacing:8px;margin:14px 0;color:{brand.primary};direction:ltr;text-align:center">{code}</p>
	  <p>{escape_html(_msg(lang, 'mail_or'))}</p>
	  <p><a href="{link}" style="display:inline-block;background:{brand.primary};color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:600">{escape_html(_msg(lang, 'mail_button'))}</a></p>
	  <p style="font-size:12px;color:{brand.slate}">{escape_html(_msg(lang, 'mail_expiry', minutes))}</p>
	 </div>
	 <div style="border-top:1px solid #D9E1E6;padding-top:12px;font-size:12px;color:{brand.slate}">
	  {brand.product_title} · {brand.company} · <a href="mailto:{brand.support_email}" style="color:{brand.primary}">{brand.support_email}</a>
	 </div>
	</div>"""
	try:
		frappe.sendmail(
			recipients=[email],
			subject=_msg(lang, "subject", code),
			message=body,
			reference_doctype=DOCTYPE,
			reference_name=reference,
			now=not frappe.flags.in_test,
			delayed=False,
		)
		return True
	except Exception:
		frappe.log_error(title="IA Maturity: verification e-mail failed")
		return False


# --------------------------------------------------------------------------- step 2: verify
@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_code(email, code, language="en"):
	lang = i18n.norm_lang(language)
	email = (email or "").strip().lower()
	if not _rate_limit(f"verify-ip:{_ip()}", PER_IP_PER_HOUR * 2):
		frappe.throw(_msg(lang, "too_many"), frappe.RateLimitExceededError)
	name = frappe.db.get_value(DOCTYPE, {"email": email, "status": "Pending"}, "name", order_by="creation desc")
	if not name:
		frappe.throw(_msg(lang, "expired"))
	reg = frappe.get_doc(DOCTYPE, name)
	if now_datetime() > reg.expires_on:
		reg.db_set("status", "Expired")
		frappe.throw(_msg(lang, "expired"))
	if not secrets.compare_digest(_hash(re.sub(r"\D", "", str(code or ""))), reg.code_hash or ""):
		attempts = cint(reg.attempts) + 1
		reg.db_set({"attempts": attempts, "status": "Blocked" if attempts >= MAX_ATTEMPTS else "Pending"})
		frappe.db.commit()  # keep the failed-attempt count even though we raise
		frappe.throw(_msg(lang, "blocked" if attempts >= MAX_ATTEMPTS else "bad_code"))
	return complete(reg)


def verify_link(link_key):
	"""Used by the portal page for the one-click link in the e-mail. Returns the redirect URL or None."""
	if not link_key or not _rate_limit(f"verify-ip:{_ip()}", PER_IP_PER_HOUR * 2):
		return None
	name = frappe.db.get_value(DOCTYPE, {"link_key_hash": _hash(link_key), "status": "Pending"}, "name")
	if not name:
		return None
	reg = frappe.get_doc(DOCTYPE, name)
	if now_datetime() > reg.expires_on:
		reg.db_set("status", "Expired")
		return None
	return complete(reg)["redirect"]


# --------------------------------------------------------------------------- step 3: sign in + draft
def _ensure_user(reg):
	if frappe.db.exists("User", reg.email):
		user = frappe.get_doc("User", reg.email)
		if user.user_type == "System User":
			frappe.throw(_msg(reg.language, "staff"))
		if not user.enabled:
			frappe.throw(_msg(reg.language, "disabled"))
	else:
		first, _sep, last = (reg.full_name or reg.email.split("@")[0]).partition(" ")
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": reg.email,
				"first_name": first,
				"last_name": last,
				"user_type": "Website User",
				"send_welcome_email": 0,
				"language": "ar" if reg.language == "ar" else None,
			}
		)
		user.flags.ignore_permissions = True
		user.flags.no_welcome_mail = True
		user.insert()
	if RESPONDENT not in frappe.get_roles(user.name):
		user.flags.ignore_permissions = True
		user.add_roles(RESPONDENT)
	return user.name


def _login(user):
	login_manager = getattr(frappe.local, "login_manager", None)
	if login_manager and getattr(frappe.local, "request", None):
		login_manager.login_as(user)
	else:  # tests / background
		frappe.set_user(user)


def complete(reg):
	user = _ensure_user(reg)
	reg.db_set({"status": "Verified", "verified_on": now_datetime(), "user": user})
	_login(user)

	redirect = "/ia-assessment"
	if reg.purpose == "Start":
		from ia_maturity.api import save_assessment

		data = {
			"job_title": reg.job_title,
			"respondent_role": reg.respondent_role,
			"assessment_date": str(reg.assessment_date or today()),
			"language": reg.language,
		}
		existing = frappe.db.exists("IA Maturity Entity", reg.entity_name)
		data["entity" if existing else "new_entity"] = reg.entity_name
		try:
			doc = save_assessment(data)
			reg.db_set("assessment", doc["name"])
			redirect = f"/ia-assessment?name={doc['name']}"
		except frappe.ValidationError:
			# e.g. entity registration disabled: the user lands on the portal home to pick an entity
			frappe.clear_messages()
	frappe.db.commit()
	return {"redirect": redirect, "user": user}
