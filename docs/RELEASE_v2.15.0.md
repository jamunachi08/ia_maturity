# v2.15.0 — Assessment type selection

**Date:** 2026-11-11

Customers choose Internal Audit or Governance, Risk and Compliance before selecting a questionnaire. The template dropdown lists only matching active, published versions. Administrators and GRC managers classify published questionnaires in **Audit packages → Questionnaire version → Assessment type**.

[README](../README.md) · [Configuration guide](GRC_ASSESSMENT_TYPES.md) · [Introduction and diagrams](introduction.md#assessment-type-selection-v2150) · [Changelog](CHANGELOG.md)

## Upgrade and compatibility

Back up the intended site, deploy the release, run `bench --site SITE migrate`, rebuild frontend assets with Node 24 and restart backend services through the established [operations procedure](GRC_OPERATIONS.md). Migration adds `IA Maturity Template.assessment_type`; GRC setup fills missing values with Internal Audit and preserves existing mappings. Map the relevant published questionnaire versions to GRC after upgrade.

Classification changes are audited and reject stale saves. They affect future template discovery without changing historical assessments, question/scoring snapshots or released reports. Existing API clients may omit the optional assessment-type argument. The new frontend supplies it and the server rejects mismatches. Report-release and onboarding approval policies remain in effect; the design reference's fixed question counts and instant-result text are not adopted as policy.

This release preparation does not deploy automatically or modify production data.

## Validation

- Disposable GRC-site migration completed successfully.
- Three backend tests passed for manager classification, customer filtering, creation mismatch rejection, forbidden customer edits, invalid types and stale writes.
- Six browser tests passed covering customer type selection, matching dropdown choices, mobile width and existing audit-package/onboarding flows.
- Frontend build and lint passed with zero errors and three existing warnings. GRC Python modules parsed successfully; the actual template API was checked after integration.
