# Assessment type selection

[README](../README.md) · [Introduction](introduction.md#assessment-type-selection-v2150) · [Changelog](CHANGELOG.md) · [Release notes](RELEASE_v2.15.0.md)

Customers choose **Internal Audit** or **Governance, Risk and Compliance** on their dashboard, then continue to start an assessment. The template dropdown contains only active, published questionnaires assigned to that type. The start dialog also offers the type choice when opened from another assessment page. Existing assessments remain accessible regardless of classification changes.

GRC administrators and managers open **Audit packages**, select a published questionnaire version, choose **Assessment type**, and click **Save assessment type**. Classification is discovery metadata and can be corrected without changing published questions, scoring snapshots or released reports. Changes use optimistic concurrency and are audited. Package-management permission does not grant unrelated template-content editing rights.

Existing templates default to Internal Audit. Assign appropriate versions to GRC after upgrade. A type without available templates cannot start an assessment. Counts and report-release promises from design mockups are not hardcoded.

Run the normal site migration and frontend build during a separately authorized rollout. Setup fills missing legacy classifications only on GRC-enabled sites. `templates(assessment_type=...)` filters server-side; `start_assessment(..., assessment_type=...)` rejects a mismatched template. Existing API clients omitting type retain their previous behavior.


## Template availability and defaults

Admins and GRC managers open **Audit packages**, select a questionnaire version,
and use **Template availability and default**:

1. Choose Internal Audit or GRC.
2. Check **Active template** to offer it for new assessments; uncheck it to disable it.
3. Optionally check **Make default for this assessment type**.
4. Select **Save template settings**.

Each assessment type has its own default. Making a template default replaces only
that type's previous default. The default is labelled **Default** in the assessment
selector for every role. Only active, published templates appear there. Disabled
versions remain visible in management screens, labelled **Disabled**, so they can
be re-enabled.

Default templates can also be disabled. Disabling a default, or moving it to another
assessment type, removes its default status. No replacement is silently designated;
choose another active published template if needed. Without a configured default,
users can choose an active template explicitly. Existing assessments and their
saved scoring policies are unaffected. Cloned drafts do not inherit default status.

Migration preserves the previous active published default in its assessment type
once on GRC sites. It does not reactivate disabled templates.
