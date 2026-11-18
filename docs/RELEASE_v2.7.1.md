# v2.7.1 — Reference report typography

The report renderer now embeds the legacy assessment font families instead of depending on installed server fonts. It uses the GRC reference's landscape page geometry, section chart, table, summary and scoring-method structure. The portal previews the authorized PDF used for downloading.

Upgrade: migrate the site and build frontend assets using Node 24. Existing released report files remain frozen; the refined layout applies to new preliminary reports and future releases. Question extras remain off unless a GRC admin enables them. The PDF stores outlined text, so the editable source remains helpful when assessing individual glyph edges across rendering engines.

Validation: 72 backend integration tests, 3 policy/PDF tests and 2 Playwright scenarios; production build and lint. [Configuration and workflow](GRC_ASSESSMENT_PRESENTATION.md) · [Changelog](CHANGELOG.md) · [README](../README.md).
