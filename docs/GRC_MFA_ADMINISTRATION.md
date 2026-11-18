# GRC MFA administration and access recovery

[README](../README.md) · [Operations](GRC_OPERATIONS.md)

## Central policy and verification method

Sign in with a GRC App Admin account and open **Administration → Account security**. Staff 2FA is disabled by default. Choose a default for staff, including consultants, reviewers, managers and app administrators. Customers always use emailed OTP on every sign-in, without a password option; these staff settings do not change customer authentication.

| Policy | Behavior |
| --- | --- |
| Enabled | MFA is available. Users opt in or turn optional MFA off from their profile after confirming their password. |
| Disabled | Staff MFA is off by default and self-enrollment is unavailable. An admin can require it for specific roles or usernames. |
| Enforced | Staff use password and a second factor by default. An admin can exempt specific roles or usernames. |

In **Staff role policies**, edit a role and choose Default, Required or Disabled.
In **Individual staff policies**, search by name/email and edit the user's policy.
Every save requires your current password. The individual policy takes precedence
over roles; Required wins among multiple roles; role policies take precedence over
the central default. Default inherits. Legacy IA reviewer/manager roles are included.
Customer rows are read-only Email OTP. Changes are audited and sign affected staff
out; a change affecting your own account returns you to sign-in.

Select **Authenticator app** or **Email code**, enter your own current password and save. The method is centralized in Frappe and also applies to non-GRC accounts that require MFA. Email codes are sent after the password is accepted; they are distinct from passwordless customer registration/verification codes. MFA-required accounts cannot bypass it with a registration link or password reset.

Email MFA needs a configured default outgoing Email Account with outgoing mail enabled and credentials ready. Muted or suspended mail blocks activation. Verify delivery to a test mailbox before enabling it on production. Authenticator users enroll through Frappe's normal first-sign-in email/QR setup, or optionally from their profile when policy is Enabled. Users without a password must set one through password recovery first.

Changes are audited and revoke affected sessions, including the app administrator's session. Policy or method changes invalidate outstanding login and enrollment challenges. Codes are short-lived, password/account-bound, rate-limited and single-use.

## Upgrade existing sites

Run the normal site backup, app deployment, `bench --site SITE migrate`, frontend build, and service restart procedure. Migration adds the central fields and optional enrollment flag. It preserves the selected method on sites already using central MFA.

Existing explicit role/account policies remain active when the central default changes. New staff inherit the disabled default unless an admin configures a requirement. Existing native enrollment alone does not make 2FA mandatory. Role and username controls remain available with every central default. Migration synchronizes the derived authentication role while retaining stored authenticator secrets.

## Resolve the inherited All-role requirement

Enabling two-factor authentication through native System Settings sets MFA on role **All**, which every user inherits. This was the source of the v2.4.0 disable error.

Saving central settings removes that blanket role requirement from GRC users. If All previously enforced MFA, existing non-GRC accounts keep that protection through the authentication-only **GRC Platform MFA** role. New non-GRC accounts inherit the preserved requirement. System Settings MFA stays enabled so those independent requirements continue to work. GRC enforcement uses **GRC Account MFA**.

The built-in Administrator retains Frappe's own platform/recovery behavior. Other independently protected roles are not silently weakened: if they would prevent Enabled or Disabled from working for a GRC user, the save reports the conflicting roles for a platform administrator to review.

If a platform operator later disables and re-enables MFA through native System Settings, Frappe can set All again. The Account security screen detects it; saving central settings reconciles it while preserving platform coverage.

## Recover access

The built-in Frappe Administrator is a platform account and normally opens Desk, not the GRC administrator workspace. Use a separate GRC App Admin account for routine policy management.

If an app administrator loses their authenticator, use the platform's trusted MFA recovery process. Another app administrator can update that username's policy after confirming their own password. Changing the central method affects every MFA-protected account. Ensure mail delivery works before switching to Email code.

## Validation

On a staging restore, verify all three policies, both methods, optional enrollment and withdrawal, new customer/staff inheritance, current-password validation, expired/wrong/replayed codes, method changes, account isolation, session revocation, non-GRC MFA preservation and migration persistence.

The integration tests are in `ia_maturity.grc.test_mfa_policy`; existing MFA regression coverage remains in `ia_maturity.grc.test_access`. Browser coverage is in `grc/tests/central-mfa.spec.ts`. Browser mocks verify UI behavior; backend tests exercise native Frappe email generation and verification with the outgoing transport intercepted. They do not establish production inbox delivery.
