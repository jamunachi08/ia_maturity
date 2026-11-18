# v2.13.0 — Scrollable questionnaire and focus controls

Fullscreen customers can independently hide/show the section overview and progress indicators. Controls preserve answers and section navigation. Normal view restores configured progress/overview visibility.

Long questions and answer options wrap and remain scrollable in both modes, including narrow/mobile and short landscape screens. Normal section navigation scrolls to the new questions.

Deploy and rebuild frontend assets, then clear caches. No schema change is introduced.

[Presentation and flow](GRC_ASSESSMENT_PRESENTATION.md#questionnaire-scrolling-and-focus-controls-v2130) · [Introduction](introduction.md) · [Changelog](CHANGELOG.md).

## Validation

- Isolated staged production build and TypeScript checks passed.
- Lint passed with zero errors and two existing warnings (PageTour and Templates).
- All 43 Playwright checks passed, including long content in normal/focus modes at 1440×900, 320×640 and 740×360; mouse and keyboard scrolling; actual Chromium fullscreen; final-option and N/A selection; independent show/hide controls; and answer preservation across navigation/mode changes.
- Seven Python presentation unit tests passed. Backend behavior and schema are unchanged.
- Desktop, narrow mobile and short landscape screenshots reviewed. Fullscreen uses a dedicated keyboard-focusable question scroller between toolbar and footer so controls cannot cover answer text.
