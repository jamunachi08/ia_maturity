# Audit packages and auditor-owned onboarding

[README](../README.md) · [Developer introduction](introduction.md) · [v2.14.0 release notes](RELEASE_v2.14.0.md) · [Changelog](CHANGELOG.md)

Package selection replaces mandatory all-section assessment only where a published scope configuration exists. The reference workbook is not imported. Existing assessments, questionnaire versions without a configuration, and released reports retain their previous behavior.

## Configure and assess

GRC managers and GRC app administrators open **Audit packages**, choose a published questionnaire version, mark required sections, and create packages with stable codes, bilingual labels and descriptions, and section mappings. Order packages with **Move up**. Use **Customer preview** to check combined coverage and question counts, then save a draft or publish. Publishing makes an immutable configuration available to future assessments. Subsequent edits create another version.

Customers confirm **What would you like assessed?** before answering. Coverage is the union of required sections and selected packages. Overlaps count once. Required sections alone are valid if they contain questions; empty scope is rejected. Each assessment stores its configuration, selected packages, resolved sections and confirmation metadata.

Only a GRC administrator can correct a confirmed, unsubmitted original draft. Open the assessment and choose **Correct assessment scope**, enter a reason and save. Concurrent changes require a reload. Removed answers and evidence remain as inactive history and return if their sections are restored. The customer must acknowledge the correction before answering or submitting again. Submitted and clarification assessments keep their scope; use a new assessment for different coverage.

The shared backend scope boundary controls question payloads, automatic answers, evidence validation, scoring, gating, findings and improvement actions. Frontend progress and live scoring receive the same filtered questions and section weights. Omitted questions contribute no denominator; included applicable section weights are normalized. Reports show selected packages and mark excluded sections **Not assessed**. Existing N/A, multi-select, rounding and results-visibility rules remain applicable.

## Invite and track

Auditors can open **Customer onboarding** before receiving customer assignments. **Invite customer** takes the recipient email and preferred language. The server records the authenticated inviter; no client-supplied auditor identity is accepted. Existing operational approval gates apply before invitation sending and organization activation.

The invitation uses a random opaque token, stored only as a hash in the invitation record. Its default lifetime is seven days. Email queue content necessarily includes the actionable link and retains the existing restricted mail-system permissions. Signup and verification store the invitation reference on the server; MFA and approval do not replace the inviter. The authenticated, verified email must match the recipient. Customers can sign in on another browser and explicitly resume their pending invitation.

Completion creates a **new** organization, membership, Consultant assignment, ownership and the snapshotted visibility lock in one transaction. The invitation row lock and a unique pending-recipient key prevent duplicate completion and competing active invitations. Existing organization names never authorize takeover. Opening a link does not consume it or count as progress.

The tracker shows status, recipient, reference, creation/sent/expiry dates, milestone timestamps, last meaningful activity, blockers and next action. Email states are **Queued**, **Sent by mail system**, and **Failed**; none prove receipt or reading. A pending approval has an administrator as next actor. Customer stages without progress for 48 hours default to **Needs attention**, configurable from 1 to 720 hours. Draft profile values, tokens, passwords and verification codes are excluded from staff tracker responses.

**Send reminder** and **Resend invitation** rotate the link and preserve the original inviter and completed milestones. Minimum interval: 60 seconds per invitation; maximum 10 messages per recipient per hour, in addition to existing mail safeguards. **Revoke** requires a reason. There are no scheduled customer reminders. Visible tracking pages and workspace notifications poll every 30 seconds; completion and recorded blockers also publish an owner notification event.

## Ownership and recovery

**Onboarding controls** sets auto-lock (on by default) and the inactivity threshold. Auto-lock is snapshotted when the invitation is issued; changing it does not alter existing invitations or customers. Existing customers are not retroactively locked.

Administrators open a customer and use **Auditor ownership and access** to transfer ownership, lock/unlock, or add named Consultant, Reviewer or Manager exceptions. Each change requires a reason and an optimistic concurrency check, and records before/after values. A transfer removes the former owner unless explicitly retained, moves live consultant allocations and lets existing revocation hooks flag other affected work for reassignment. Customer memberships remain independent.

Recovery procedures:

- Failed email: inspect existing email diagnostics/configuration, then resend. A failed/queued message is not customer progress.
- Expired invitation: resend after the cooldown. The old token becomes invalid.
- Disabled inviter: an administrator either restores the legitimate inviter's account/role or revokes the invitation and asks the intended active auditor to issue a new one. Never rewrite `invited_by`.
- Competing invitation: review the original request as administrator, revoke it with a reason if appropriate, and issue a new request from the correct auditor.
- Existing organization conflict: use authorized membership controls for that organization or correct the new organization name. Do not activate ownership based on an email/name match.
- Approval rejection: the customer can correct and resubmit organization details; rejected invitation approval closes the invitation. Revoked requests cannot activate through a later approval.
- Stale scope/ownership edit: reload, review current values, then retry with a reason.

## Help and rollout

Shared English/Arabic guide content lives in `grc/src/guide-content.json`. Help selects a distinct manager guide; managers may also read auditor guidance, and administrators may read all four guides. Contextual page tours use stable `data-tour` targets, preserve user preferences and opt-outs, and never execute mutations. PDFs are generated with `node grc/scripts/build-guides.mjs` (from the app root) into `ia_maturity/public/guides`.

New schema is synchronized by normal GRC-site migration. GRC defaults are idempotent and ownership fields default unlocked for legacy customers. On a disposable GRC site run the scope/onboarding, access, operations, notifications and presentation backend suites, HTTP acceptance scripts, relevant Playwright suites, lint/build and PDF visual review before release. This change does not deploy automatically or enable outbound email on the test site.
