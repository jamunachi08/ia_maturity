"""Integration coverage for central policies and native email/authenticator proof."""
import json
import secrets
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
import pyotp
from frappe.utils.password import encrypt, update_password
from frappe.twofactor import set_default, two_factor_is_enabled_for_
from werkzeug.wrappers import Response

from ia_maturity.grc import security as sec
from ia_maturity.grc.account_security import MFA_ROLE, set_mfa_policy, set_role_mfa_policy
from ia_maturity.grc.mfa import (required, status, remember_login_challenge,
    validate_login_challenge, challenge_key, begin_authenticator, confirm_authenticator,
    frappe_2fa_value, forget_frappe_2fa)
from ia_maturity.grc.mfa_policy import (save_mfa_settings, security_mfa_settings,
    set_optional_mfa, PLATFORM_ROLE)

ADMIN = "grc-central-admin@example.test"
CUSTOMER = "grc-central-customer@example.test"
STAFF = "grc-central-auditor@example.test"
ERP = "grc-central-erp@example.test"


class TestCentralMFA(unittest.TestCase):
    def setUp(self):
        assert frappe.conf.get("grc_enabled"), "Use an isolated GRC test site."
        frappe.set_user("Administrator")
        frappe.flags.in_test = True
        frappe.flags.pop("grc_validated_mfa_user", None)
        frappe.db.set_single_value("GRC Settings", {"mfa_policy": "", "mfa_method": "",
            "mfa_revision": "", "mfa_preserve_platform": 0, "mfa_role_policies": ""})
        frappe.db.set_single_value("System Settings", {"enable_two_factor_auth": 1,
                                                       "two_factor_method": "OTP App"})
        frappe.db.set_value("Role", "All", "two_factor_auth", 0)
        self.password = secrets.token_urlsafe(24)
        self.secret = pyotp.random_base32()
        self.ids = []
        for email, role in [(ADMIN,"GRC App Admin"), (CUSTOMER,"GRC Customer"),
                            (STAFF,"GRC Auditor"), (ERP,"System Manager")]:
            if not frappe.db.exists("User", email):
                with sec.service_write():
                    frappe.get_doc({"doctype":"User", "email":email, "first_name":"Central Fixture",
                        "send_welcome_email":0, "roles":[{"role":role}]}).insert(ignore_permissions=True)
            with sec.service_write():
                doc = frappe.get_doc("User", email)
                doc.grc_mfa_policy = "Default"
                doc.grc_mfa_opt_in = 0
                doc.set("roles", [{"role": role}])
                doc.save(ignore_permissions=True)
            update_password(email, self.password)
            set_default(email + "_otpsecret", encrypt(self.secret))
            set_default(email + "_otplogin", 0)
        from ia_maturity.grc.auth import digest
        for user in (ADMIN,CUSTOMER,STAFF,ERP):
            for kind in ("mfa-policy-admin", "mfa-enrollment", "mfa-confirm"):
                frappe.cache.delete(f"grc:{frappe.local.site}:{kind}:{digest(user)}")
        frappe.set_user(ADMIN)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for tmp in self.ids:
            forget_frappe_2fa(tmp)
            frappe.cache.delete_value(challenge_key(tmp))
        frappe.flags.pop("grc_validated_mfa_user", None)
        frappe.clear_cache()

    def configure(self, policy, method="OTP App"):
        frappe.set_user(ADMIN)
        # Frappe runs the unrelated Contact synchronization job inline in tests.
        # Keep bulk MFA synchronization scoped to users/roles/native login state.
        with patch("ia_maturity.grc.mfa_policy.email_ready", return_value=True), patch(
                "frappe.core.doctype.user.user.create_contact"):
            return save_mfa_settings(policy, method, self.password)

    def challenge(self, user=STAFF, email=False):
        from frappe.twofactor import authenticate_for_2factor
        form = frappe._dict(usr=user,pwd=self.password)
        with patch.object(frappe.local, "form_dict", form), patch("frappe.sendmail") as send:
            authenticate_for_2factor(user)
            tmp = frappe.local.response["tmp_id"]
            self.ids.append(tmp)
            token = frappe_2fa_value(tmp, "_token")
            code = pyotp.HOTP(self.secret).at(int(token)) if email else pyotp.TOTP(self.secret).now()
            response = Response(json.dumps({"tmp_id":tmp,
                "verification":frappe.local.response["verification"]}), mimetype="application/json")
            remember_login_challenge(response)
            if email:
                self.assertEqual(send.call_count, 1)
                self.assertIn(code, send.call_args.kwargs["message"])
            self.assertIn("no-store", response.headers["Cache-Control"])
        return tmp, code

    def test_only_admin_with_current_password_can_save(self):
        for user in ("Guest", CUSTOMER, STAFF, ERP):
            frappe.set_user(user)
            with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):
                save_mfa_settings("Disabled","Email",self.password)
            with self.assertRaises((frappe.PermissionError,frappe.AuthenticationError)):
                security_mfa_settings()
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.AuthenticationError):
            save_mfa_settings("Disabled","OTP App","wrong-password")
        with self.assertRaises(frappe.ValidationError):
            save_mfa_settings("Invalid","SMS",self.password)
        self.assertFalse(security_mfa_settings()["centralized"])

    def test_disabled_replaces_blanket_rule_and_preserves_platform_accounts(self):
        frappe.db.set_value("Role","All","two_factor_auth",1)
        operator_native_before = two_factor_is_enabled_for_("Administrator")
        result = self.configure("Disabled")
        self.assertTrue(result["reauthenticate"])
        self.assertFalse(frappe.db.get_value("Role","All","two_factor_auth"))
        for user in (CUSTOMER,STAFF,ADMIN):
            self.assertFalse(required(user))
            self.assertFalse(two_factor_is_enabled_for_(user))
        self.assertTrue(two_factor_is_enabled_for_(ERP))
        # Preserve the installed Frappe version's native operator requirement;
        # app policy must not invent an exemption or weaken platform coverage.
        self.assertEqual(two_factor_is_enabled_for_("Administrator"), operator_native_before)
        self.assertEqual(sec.account_type("Administrator"), "ERP")
        self.assertIn(PLATFORM_ROLE, frappe.get_roles(ERP))
        self.assertTrue(frappe.db.get_single_value("System Settings","enable_two_factor_auth"))
        with sec.service_write():
            user=frappe.get_doc({"doctype":"User","email":"grc-central-new-erp@example.test",
                "first_name":"New ERP Fixture","send_welcome_email":0,"roles":[{"role":"System Manager"}]})
            user.insert(ignore_permissions=True)
        self.assertTrue(two_factor_is_enabled_for_(user.name))

    def test_customer_otp_is_invariant_under_staff_default_and_legacy_settings(self):
        frappe.db.set_value("User",CUSTOMER,"grc_mfa_policy","Disabled")
        frappe.db.set_single_value("GRC Settings","mfa_role_policies",
                                   json.dumps({"GRC Customer":"Disabled"}))
        self.configure("Enforced")
        for user in (STAFF,ADMIN):
            self.assertTrue(required(user))
            self.assertTrue(two_factor_is_enabled_for_(user))
        # Customer email OTP is invariant even under legacy or central staff MFA.
        self.assertFalse(required(CUSTOMER))
        self.assertFalse(two_factor_is_enabled_for_(CUSTOMER))
        frappe.set_user(CUSTOMER)
        self.assertTrue(status()["customer_otp_only"])
        self.assertFalse(status()["can_enroll"])
        with self.assertRaises(frappe.PermissionError):
            set_optional_mfa(1,self.password)
        frappe.set_user(ADMIN)
        with self.assertRaises(frappe.ValidationError):
            set_mfa_policy(CUSTOMER,"Disabled",self.password)
        with self.assertRaises(frappe.ValidationError):
            set_role_mfa_policy("GRC Customer","Disabled",self.password)

    def test_optional_email_enrollment_and_withdrawal(self):
        self.configure("Enabled","Email")
        frappe.set_user(STAFF)
        self.assertFalse(required())
        self.assertTrue(status()["can_enroll"])
        with patch("ia_maturity.grc.mfa_policy.email_ready",return_value=True):
            set_optional_mfa(1,self.password)
        self.assertTrue(required())
        self.assertTrue(status()["optional_enrolled"])
        set_optional_mfa(0,self.password)
        self.assertFalse(required())
        self.configure("Enforced","Email")
        frappe.set_user(STAFF)
        with self.assertRaises(frappe.PermissionError):
            set_optional_mfa(0,self.password)
        frappe.set_user(CUSTOMER)
        self.assertTrue(status()["customer_otp_only"])
        for value in (0,1):
            with self.assertRaises(frappe.PermissionError):
                set_optional_mfa(value,self.password)

    def test_optional_authenticator_requires_valid_setup(self):
        self.configure("Enabled")
        frappe.set_user(STAFF)
        with self.assertRaises(frappe.ValidationError):
            set_optional_mfa(1,self.password)
        pending=begin_authenticator(self.password)
        from ia_maturity.grc.mfa import pending_key
        from frappe.utils.password import decrypt
        secret=decrypt(frappe.cache.get_value(pending_key())["secret"])
        result=confirm_authenticator(pending["setup_token"],pyotp.TOTP(secret).now())
        self.assertTrue(result["enabled"])
        self.assertTrue(required())
        self.assertTrue(frappe.db.get_value("User",STAFF,"grc_mfa_opt_in"))
        set_optional_mfa(0,self.password)
        self.assertFalse(required())

    def test_policy_change_invalidates_pending_authenticator_setup(self):
        self.configure("Enabled")
        frappe.set_user(STAFF)
        pending=begin_authenticator(self.password)
        self.configure("Disabled")
        frappe.set_user(STAFF)
        with self.assertRaises((frappe.PermissionError,frappe.ValidationError)):
            confirm_authenticator(pending["setup_token"],"123456")

    def test_override_writes_work_with_central_policy_and_recheck_locked_settings(self):
        self.configure("Disabled")
        with patch("ia_maturity.grc.auth.limit"):
            frappe.db.value_cache["GRC Settings"]["mfa_policy"] = None
            set_role_mfa_policy("GRC Auditor", "Required", self.password)
            self.assertTrue(required(STAFF))
            self.assertTrue(two_factor_is_enabled_for_(STAFF))
            frappe.db.value_cache["GRC Settings"]["mfa_policy"] = None
            set_mfa_policy(STAFF, "Disabled", self.password)
        self.assertFalse(required(STAFF))
        self.assertFalse(two_factor_is_enabled_for_(STAFF))

    def test_unconfigured_staff_default_is_password_only_even_with_old_enrollment(self):
        from frappe.twofactor import confirm_otp_token
        from ia_maturity.grc.auth import enforce_staff_mfa
        settings = security_mfa_settings()
        self.assertEqual(settings["policy"], "Disabled")
        self.assertFalse(settings["centralized"])
        # Retaining an old authenticator secret/enrollment must not make it mandatory.
        set_default(STAFF + "_otplogin", 1)
        self.assertFalse(required(STAFF))
        self.assertFalse(two_factor_is_enabled_for_(STAFF))
        with patch.object(frappe.local, "form_dict", frappe._dict(), create=True):
            self.assertTrue(confirm_otp_token(SimpleNamespace(user=STAFF)))
            enforce_staff_mfa(SimpleNamespace(user=STAFF))
        frappe.set_user(STAFF)
        self.assertEqual(status()["policy"], "Disabled")
        self.assertFalse(status()["can_enroll"])

    def test_user_and_role_overrides_take_precedence_over_each_global_default(self):
        from ia_maturity.grc.account_security import security_accounts
        with patch("ia_maturity.grc.auth.limit"), patch("frappe.sessions.clear_sessions") as clear:
            self.configure("Disabled")
            set_role_mfa_policy("GRC Auditor", "Required", self.password)
            self.assertTrue(required(STAFF))
            self.assertTrue(two_factor_is_enabled_for_(STAFF))
            clear.assert_any_call(user=STAFF, keep_current=False, force=True)
            set_mfa_policy(STAFF, "Disabled", self.password)
            self.assertFalse(required(STAFF))
            self.assertFalse(two_factor_is_enabled_for_(STAFF))
            for default in ("Enabled", "Enforced", "Disabled"):
                self.configure(default)
                self.assertFalse(required(STAFF))
                self.assertFalse(two_factor_is_enabled_for_(STAFF))
            staff_row = next(row for row in security_accounts(search=STAFF)["rows"] if row["name"] == STAFF)
            self.assertEqual(staff_row["policy"], "Disabled")
            self.assertEqual(staff_row["effective_policy"], "Disabled")
            set_mfa_policy(STAFF, "Default", self.password)
            self.assertTrue(required(STAFF))
            self.assertTrue(two_factor_is_enabled_for_(STAFF))
            self.configure("Enforced")
            set_role_mfa_policy("GRC Auditor", "Disabled", self.password)
            self.assertFalse(required(STAFF))
            set_mfa_policy(STAFF, "Required", self.password)
            self.assertTrue(required(STAFF))
            self.assertTrue(two_factor_is_enabled_for_(STAFF))

    def test_multiple_roles_require_mfa_until_individual_override_disables_it(self):
        with patch("ia_maturity.grc.auth.limit"):
            self.configure("Disabled")
            with sec.service_write():
                doc = frappe.get_doc("User", STAFF)
                doc.append("roles", {"role": "GRC Reviewer"})
                doc.save(ignore_permissions=True)
            set_role_mfa_policy("GRC Auditor", "Required", self.password)
            set_role_mfa_policy("GRC Reviewer", "Disabled", self.password)
            self.assertTrue(required(STAFF))
            set_mfa_policy(STAFF, "Disabled", self.password)
            self.assertFalse(required(STAFF))
            set_mfa_policy(STAFF, "Default", self.password)
            self.assertTrue(required(STAFF))

    def test_legacy_ia_staff_role_controls_native_mfa_and_allows_user_override(self):
        from ia_maturity.grc.account_security import security_role_policies
        self.configure("Disabled")
        with sec.service_write():
            doc = frappe.get_doc("User", STAFF)
            doc.set("roles", [{"role": "IA Maturity Reviewer"}])
            doc.save(ignore_permissions=True)
        self.assertEqual(sec.account_type(STAFF), "Auditor")
        self.assertIn("IA Maturity Reviewer", {row["role"] for row in security_role_policies()})
        self.assertFalse(two_factor_is_enabled_for_(STAFF))
        with patch("ia_maturity.grc.auth.limit"):
            set_role_mfa_policy("IA Maturity Reviewer", "Required", self.password)
            self.assertTrue(required(STAFF))
            self.assertTrue(two_factor_is_enabled_for_(STAFF))
            set_mfa_policy(STAFF, "Disabled", self.password)
            self.assertFalse(required(STAFF))
            self.assertFalse(two_factor_is_enabled_for_(STAFF))
            set_mfa_policy(STAFF, "Default", self.password)
            self.assertTrue(two_factor_is_enabled_for_(STAFF))
            set_role_mfa_policy("IA Maturity Reviewer", "Default", self.password)
            self.assertFalse(required(STAFF))
            self.assertFalse(two_factor_is_enabled_for_(STAFF))

    def test_individual_and_role_changes_end_the_affected_admin_http_session(self):
        self.configure("Disabled")
        with patch("ia_maturity.grc.auth.limit"):
            for source in ("user", "role"):
                frappe.set_user(ADMIN)
                logout = Mock(side_effect=lambda: frappe.set_user("Guest"))
                with patch.object(frappe.local, "request", object(), create=True), patch.object(
                        frappe.local, "login_manager", SimpleNamespace(logout=logout), create=True):
                    if source == "user":
                        result = set_mfa_policy(ADMIN, "Required", self.password)
                    else:
                        result = set_role_mfa_policy("GRC App Admin", "Required", self.password)
                logout.assert_called_once_with()
                self.assertTrue(result["reauthenticate"])
                self.assertEqual(frappe.session.user, "Guest")
                self.assertTrue(two_factor_is_enabled_for_(ADMIN))
                # Prepare the second independent policy source without an HTTP request.
                frappe.set_user(ADMIN)
                with patch("ia_maturity.grc.mfa_policy.logout_current_request"):
                    if source == "user":
                        set_mfa_policy(ADMIN, "Default", self.password)
                    else:
                        set_role_mfa_policy("GRC App Admin", "Default", self.password)
                self.assertFalse(required(ADMIN))

    def test_centralized_overrides_require_admin_and_current_password(self):
        self.configure("Disabled")
        for user in ("Guest", CUSTOMER, STAFF, ERP):
            frappe.set_user(user)
            with self.assertRaises((frappe.PermissionError, frappe.AuthenticationError)):
                set_mfa_policy(STAFF, "Required", self.password)
            with self.assertRaises((frappe.PermissionError, frappe.AuthenticationError)):
                set_role_mfa_policy("GRC Auditor", "Required", self.password)
        frappe.set_user(ADMIN)
        for password in ("", "wrong-password"):
            with self.assertRaises((frappe.ValidationError, frappe.AuthenticationError)):
                set_mfa_policy(STAFF, "Required", password)
            with self.assertRaises((frappe.ValidationError, frappe.AuthenticationError)):
                set_role_mfa_policy("GRC Auditor", "Required", password)
        self.assertFalse(required(STAFF))
        self.assertFalse(two_factor_is_enabled_for_(STAFF))

    def test_admin_override_blocks_optional_self_enrollment_and_withdrawal(self):
        self.configure("Enabled", "Email")
        with patch("ia_maturity.grc.auth.limit"), patch("ia_maturity.grc.mfa_policy.email_ready", return_value=True):
            for source, policy in (("role", "Required"), ("role", "Disabled"),
                                   ("user", "Required"), ("user", "Disabled")):
                frappe.set_user(ADMIN)
                if source == "role":
                    set_role_mfa_policy("GRC Auditor", policy, self.password)
                else:
                    set_mfa_policy(STAFF, policy, self.password)
                frappe.set_user(STAFF)
                self.assertFalse(status()["can_enroll"])
                for enabled in (0, 1):
                    with self.assertRaises(frappe.PermissionError):
                        set_optional_mfa(enabled, self.password)
                self.assertEqual(required(), policy == "Required")

    def test_cached_policy_cannot_override_a_newer_locked_policy(self):
        self.configure("Enabled","Email")
        self.configure("Disabled","Email")
        frappe.set_user(STAFF)
        frappe.db.value_cache["GRC Settings"]["mfa_policy"]="Enabled"
        with self.assertRaises(frappe.PermissionError):
            set_optional_mfa(0,self.password)
        self.assertFalse(required())

    def test_email_requires_delivery_configuration(self):
        # Other fixture staff may have explicit requirements. Adopt the method
        # while delivery is available, then test rejection when it is unavailable.
        self.configure("Disabled", "Email")
        with patch("ia_maturity.grc.mfa_policy.email_ready",return_value=False):
            for policy in ("Enabled","Enforced"):
                with self.assertRaises(frappe.ValidationError):
                    save_mfa_settings(policy,"Email",self.password)
            with self.assertRaises(frappe.ValidationError):
                set_mfa_policy(STAFF, "Required", self.password)
            with self.assertRaises(frappe.ValidationError):
                set_role_mfa_policy("GRC Auditor", "Required", self.password)
            self.assertFalse(required(STAFF))
        with patch("ia_maturity.grc.auth.limit"):
            set_role_mfa_policy("GRC Auditor", "Disabled", self.password)
            self.configure("Enforced", "Email")
            # Inheriting a required default also activates MFA and needs delivery.
            with patch("ia_maturity.grc.mfa_policy.email_ready", return_value=False):
                with self.assertRaises(frappe.ValidationError):
                    set_role_mfa_policy("GRC Auditor", "Default", self.password)

    def test_unrelated_role_requirement_is_not_silently_removed(self):
        frappe.db.set_value("Role","System Manager","two_factor_auth",1)
        with sec.service_write():
            doc=frappe.get_doc("User",STAFF)
            doc.append("roles",{"role":"System Manager"})
            doc.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            self.configure("Disabled")
        self.assertTrue(frappe.db.get_value("Role","System Manager","two_factor_auth"))

    def test_settings_cannot_bypass_synchronization_service(self):
        doc=frappe.get_single("GRC Settings")
        doc.mfa_policy="Disabled"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_real_native_email_code_is_accepted_after_core_consumes_counter(self):
        from frappe.twofactor import confirm_otp_token
        self.configure("Enforced","Email")
        tmp,code=self.challenge(email=True)
        with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=code)):
            manager=SimpleNamespace(user=STAFF)
            self.assertTrue(confirm_otp_token(manager))
            self.assertIsNone(frappe_2fa_value(tmp,"_token"))
            validate_login_challenge(STAFF)
            self.assertEqual(frappe.flags.grc_validated_mfa_user,STAFF)
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(STAFF)

    def test_email_rejects_wrong_code_cross_account_expired_and_missing_proof(self):
        self.configure("Enforced","Email")
        tmp,code=self.challenge(email=True)
        with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=code)):
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(CUSTOMER)
            frappe.form_dict.otp=("0" if code[0]!="0" else "1")+code[1:]
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(STAFF)
            frappe.form_dict.otp=code
            frappe.cache.delete_value(challenge_key(tmp))
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(STAFF)
        tmp,code=self.challenge(email=True)
        # Expire the cached password in both Frappe storage styles.
        frappe.cache.delete(tmp+"_pwd"); frappe.cache.delete_value(tmp+"_pwd")
        with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=code)):
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(STAFF)

    def test_email_challenge_attempts_are_limited(self):
        self.configure("Enforced","Email")
        tmp,code=self.challenge(email=True)
        wrong=("0" if code[0]!="0" else "1")+code[1:]
        with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=wrong)):
            for _ in range(5):
                with self.assertRaises(frappe.AuthenticationError):
                    validate_login_challenge(STAFF)
            frappe.form_dict.otp=code
            with self.assertRaises(frappe.RateLimitExceededError):
                validate_login_challenge(STAFF)

    def test_method_change_invalidates_previous_challenges(self):
        self.configure("Enforced","Email")
        tmp,code=self.challenge(email=True)
        self.configure("Enforced","OTP App")
        with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=code)):
            with self.assertRaises(frappe.AuthenticationError):
                validate_login_challenge(STAFF)

    def test_native_authenticator_proof_still_works_and_is_single_use(self):
        self.configure("Enforced")
        for user in (STAFF,):
            set_default(user+"_otplogin",1)
        # Keep minting and verification in one clock step for this replay test.
        with patch.object(pyotp.TOTP, "timecode", return_value=12345678):
            tmp,code=self.challenge()
            with patch.object(frappe.local,"form_dict",frappe._dict(tmp_id=tmp,otp=code)):
                validate_login_challenge(STAFF)
                self.assertEqual(frappe.flags.grc_validated_mfa_user,STAFF)
                with self.assertRaises(frappe.AuthenticationError):
                    validate_login_challenge(STAFF)

    def test_save_repairs_an_unsupported_native_method(self):
        self.configure("Disabled")
        frappe.db.set_single_value("System Settings","two_factor_method","SMS")
        result=self.configure("Disabled")
        self.assertEqual(frappe.db.get_single_value("System Settings","two_factor_method"),"OTP App")
        self.assertGreater(result["affected"],0)

    def test_migration_preserves_central_method_and_policy(self):
        self.configure("Disabled","Email")
        from ia_maturity.grc.setup import setup
        frappe.set_user("Administrator")
        setup()
        self.assertEqual(frappe.db.get_single_value("GRC Settings","mfa_policy"),"Disabled")
        self.assertEqual(frappe.db.get_single_value("System Settings","two_factor_method"),"Email")

    def test_central_change_ends_the_active_http_session(self):
        logout = Mock(side_effect=lambda: frappe.set_user("Guest"))
        with patch.object(frappe.local, "request", object(), create=True), patch.object(
                frappe.local, "login_manager", SimpleNamespace(logout=logout), create=True):
            result = self.configure("Disabled")
        logout.assert_called_once_with()
        self.assertTrue(result["reauthenticate"])
        self.assertEqual(frappe.session.user, "Guest")

    def test_unchanged_central_policy_keeps_the_active_session(self):
        self.configure("Disabled")
        logout = Mock()
        with patch.object(frappe.local, "request", object(), create=True), patch.object(
                frappe.local, "login_manager", SimpleNamespace(logout=logout), create=True):
            result = self.configure("Disabled")
        logout.assert_not_called()
        self.assertFalse(result["reauthenticate"])

    def test_optional_change_ends_the_active_http_session(self):
        self.configure("Enabled", "Email")
        frappe.set_user(STAFF)
        logout = Mock(side_effect=lambda: frappe.set_user("Guest"))
        with patch("ia_maturity.grc.mfa_policy.email_ready", return_value=True), patch.object(
                frappe.local, "request", object(), create=True), patch.object(
                frappe.local, "login_manager", SimpleNamespace(logout=logout), create=True):
            result = set_optional_mfa(1, self.password)
        logout.assert_called_once_with()
        self.assertEqual(result["redirect"], "/login")
        self.assertEqual(frappe.session.user, "Guest")
