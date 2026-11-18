# Customer and auditor oversight

[README](../README.md) · [Operations](GRC_OPERATIONS.md) · [Website editor](GRC_SITE_CONTENT.md)

## Access and reporting

Open **Customer and auditor overview** in the auditor workspace. GRC App Admins see the complete portfolio. A manager sees only customers with an active **Manager** responsibility in Auditor Customer Assignment; holding a role alone does not grant customer access. Ordinary auditors and customers cannot open the oversight APIs.

Customers and Auditors provide searchable, paginated lists. **View overview** opens profiles, customer memberships and units, active responsibilities, assessment allocations, assigned actions, follow-ups and activity. Each work section can be searched and exported as CSV. Activity includes actor, date, customer, event and details, with event totals. Manager exports use the same customer scope; auditor reports show only that auditor's allocated work and activity in permitted customers.

## Configure approvals

Approval requirements default to disabled to preserve existing behavior on upgrade. Administrators open **Global workflow** to enable onboarding and/or assignment approvals. A customer row's **Workflow** button sets its customer-specific override; administrators and that customer's managers can configure it. Overrides replace the customer policy, leaving the global policy unchanged.

Choose one to five ordered stages: **GRC Manager** or **GRC App Admin**. A global workflow uses administrator stages because new customers lack assigned managers. Example customer policy: Manager, then App administrator. An administrator can act at a manager stage; managers require a current Manager assignment for that customer. Requesters cannot decide their own requests unless **Allow requester to approve own request** was enabled at submission.

Requests freeze their stages and self-approval rule at submission. Later changes affect new requests. Disable an approval category to apply subsequent ordinary changes immediately. Manager requests for new auditor accounts always require approval.

## Covered requests

| Category | Trigger | Final approval applies |
| --- | --- | --- |
| Customer onboarding | New organization, including verified signup | Creates organization and requester's organization-admin membership or authorized staff responsibility |
| Auditor onboarding | Admin adds new staff; manager requests a new auditor | Creates separate staff account; manager requests also assign it to the selected customer |
| Customer invitation | Invite customer organization member | Creates and sends invitation; recipient still verifies and accepts |
| Customer membership | Change member role or active state | Applies reviewed membership values |
| Customer assignment | Assign or revoke staff responsibility | Grants or revokes responsibility |
| Assessment assignment | Change consultant, reviewer, owner or deadlines | Applies reviewed allocation |

Already-issued invitations retain their acceptance and expiry behavior. Existing staff and organization profile edits remain immediate; onboarding controls apply to creating organizations/accounts and issuing invitations.

## Review and audit

Open **Approvals**, choose **Review request**, inspect proposed values and history, then submit a decision. Approve advances one stage; final approval applies the change atomically. Rejection and cancellation require reasons and preserve existing access. App administrators can cancel any pending request; managers can cancel their own scoped requests. Correct rejected proposals by submitting the original form again.

No account, membership or allocation change applies while pending. Customer onboarding users see a waiting screen until approval. The portal shows a submission notice for queued changes. New staff set passwords through recovery after approval; MFA follows the separate security policy.

Assignment and membership requests retain previous values and refuse final application if those records changed. Reviewers must still hold the required role or responsibility, and requesters must remain active. Request records resist ordinary saves/deletes. Decisions and configuration changes appear in GRC Activity. Service application events may name Administrator as executor; request and decision events retain actual requesters/reviewers.

## Deployment and validation

Back up the target site, deploy, run bench --site SITE migrate, build assets and restart services. Migration adds GRC Operations Policy and GRC Operations Request. Approval flags default to disabled.

On an isolated site: bench --site grc.local run-tests --module ia_maturity.grc.test_operations --skip-test-records --skip-before-tests.

Verify manager scope, unrelated customers, both onboarding paths, ordered approval, rejection/cancellation and allocation changes before enabling policies in production.
