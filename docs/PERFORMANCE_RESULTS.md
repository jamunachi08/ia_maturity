# IA/GRC local performance evidence — 13 November 2026

[Measurement and operations guide](PERFORMANCE_OPERATIONS.md) · [README](../README.md)

Tracking: [IA/GRC Performance epic](https://app.notion.com/p/4175dea8d7ef812fa173ebcd0c7889b6).
This epic remains separate from feature-compliance completion counts.

All 640 browser observations pass the final candidate's timing/layout gates, and
the asserted 50-client, 30-minute sustained read test passed without errors.
Desktop cold-login delay and initial Arabic layout were corrected before final
acceptance. This document does
not certify the migrated sandbox, production capacity or real-user Core Web Vitals.

## Test conditions and preserved workflows

The immutable baseline is app commit `0caa550`. Baseline and optimized builds use
the same isolated `grc-perf.local` database, four Gunicorn 23.0.0 sync workers,
Frappe 15.118.0, Python 3.11.14 and MariaDB 10.6.22 on the same 12-logical-CPU WSL
host. Both browser cohorts use the same actual gzip level-5 loopback proxy.
Production-built assets are served; development-server timings are excluded.

Desktop Chromium uses a 1440×1000 viewport, 20 ms network latency, 80 Mbps download
and native CPU speed. Mobile uses 390×844, 150 ms latency, 4 Mbps download and 4×
CPU slowdown. Each group has ten cache-disabled cold and ten warm loads. Page-ready
time ends when authorized cards, the first record page and controls are usable;
LCP/CLS are read after fonts settle. Navigation timing ends after the destination
record page is usable. These are controlled lab measurements, not field percentiles.

The isolated clone contains 184 users, 47 entities, 276 assessments, 264 assignments,
4,177 activity records and 17 actions. The reserved synthetic slice grows from
44 assignments at 1× to 220 at 5×, evenly split across IA and GRC. Existing cloned
workflow records remain. “5×” describes that slice, not every table in the database.
Mail stays muted and the scheduler stays paused. Credentials, OTP challenge state
and native session cookies remain in the site's private directory outside Git.
The public fixture has only a 79-byte published-override response, so landing
timings exercise the built-in EN/AR copy with minimal overrides. Retained tests
cover published-content behavior; large destination CMS payloads require their
own deployment measurement.

Retained functional evidence is separate from timing acceptance: 227 backend tests,
101 mocked browser tests and 13 native browser journeys passed on the final build.
The native journeys cover customer/staff authentication, profile/scope, assessment
save/resume and clarification, manager approval/release, PDF behavior, routing and
preferences. Backend suites cover permission/revocation and response equivalence.
Local reserved OTP challenges exercise the native verification API without sending
email. External inbox delivery requires the designated deployment environment.

## Browser budgets

| Final cohort | Observations | Worst public/login LCP p75 | Worst GRC dashboard ready p95 | Worst internal navigation p95 | Worst CLS p75 |
|---|---:|---:|---:|---:|---:|
| English, full 12-role/route × 2-device matrix | 480 | 1,204 ms | 2,040.4 ms | 130.3 ms | 0.09114109 |
| Arabic, representative 4-route × 2-device matrix | 160 | 1,212 ms | 2,163.9 ms | 134 ms | 0.09155707 |
| Acceptance budget | ≥20 per group | ≤2,500 ms | ≤3,000 ms | ≤1,000 ms | ≤0.1 |

Every applicable group passed. English covers anonymous landing, login, GRC admin,
ordinary ERP and IA/GRC customer, consultant, reviewer and manager. Arabic covers
anonymous landing, login, GRC customer and IA manager on desktop/mobile, including
RTL and Arabic fonts. It is not an all-role Arabic timing matrix. Neither cohort
reported a failed resource request.

The ordinary ERP fixture reaches the native ERPNext organization-setup screen
because setup is incomplete. ERP routing/layout preservation passed; ERP dashboard
speed is not certified. Its driver timings remain diagnostic and are excluded
from the GRC dashboard gate.

Safe language-toggle and navigation interactions produced 620 distinct Event Timing
interactions across 440 English loads (maximum 64 ms) and 200 across 160 Arabic
loads (maximum 40 ms). The p95 of observed per-load maxima was 24 ms in both
cohorts. Other loads
are labeled below the browser's 16 ms observation threshold, unsupported or native
ERP setup not sampled. None is recorded as a measured zero. Field INP was not measured.

The compressed baseline has only two observations per group (48 total). It is
diagnostic comparison evidence, not a statistically strong baseline p95. The earlier
uncompressed optimized mobile-admin run failed: p95 ready 4,043 ms, with cold loads
around 3.5 seconds despite backend work near 100 ms. That failure is retained.
Actual compression and correct asset delivery are required in deployment; the
loopback helper does not certify destination nginx configuration.

### Role-specific native dashboard comparison

Both cohorts use the same native-ready predicate and stylesheet-settlement
barrier. Baseline cold/warm entries are one observation each; they are diagnostic
raw values, not baseline percentiles. Final p95 uses 20 observations per group.

| Role | Profile | Baseline cold / warm ready ms (N=1 each) | Final ready p95 ms (N=20) | Final navigation p95 ms |
|---|---|---:|---:|---:|
| admin | desktop | 6475.2 / 6729.9 | 629.2 | 66.0 |
| admin | mobile | 7869.6 / 6835.5 | 2040.4 | 130.3 |
| ia_customer | desktop | 4157.7 / 3912.9 | 642.0 | 66.1 |
| ia_customer | mobile | 5201.5 / 4463.3 | 2017.1 | 98.3 |
| ia_consultant | desktop | 10156.2 / 9763.4 | 627.4 | 65.9 |
| ia_consultant | mobile | 11282.7 / 9880.2 | 2021.4 | 111.6 |
| ia_reviewer | desktop | 9872.7 / 9280.2 | 642.9 | 65.9 |
| ia_reviewer | mobile | 11221.9 / 10246.0 | 2021.6 | 99.7 |
| ia_manager | desktop | 12691.6 / 11577.6 | 691.3 | 66.0 |
| ia_manager | mobile | 13290.0 / 12814.0 | 2035.3 | 116.0 |
| grc_customer | desktop | 4324.5 / 4427.2 | 641.8 | 65.7 |
| grc_customer | mobile | 5587.6 / 4729.6 | 2006.5 | 98.4 |
| grc_consultant | desktop | 10622.7 / 9927.3 | 697.7 | 66.0 |
| grc_consultant | mobile | 12020.9 / 11030.1 | 2020.8 | 99.2 |
| grc_reviewer | desktop | 10255.0 / 10462.5 | 641.9 | 65.9 |
| grc_reviewer | mobile | 11750.3 / 10978.7 | 2003.6 | 98.1 |
| grc_manager | desktop | 9733.3 / 9993.7 | 672.8 | 65.9 |
| grc_manager | mobile | 11374.2 / 10705.1 | 2017.3 | 114.6 |

### Matching final login LCP comparison

The repeated baseline and final EN login cohorts each have ten cold and ten warm
observations per device, using the same stylesheet barrier and LCP observer.
These supersede intermediate early-paint comparisons. All four LCP p75 groups
improved; this is a controlled local comparison, not a real-user field result.

| Profile | Browser cache | Baseline LCP p75 ms (N=10) | Final LCP p75 ms (N=10) | Change |
|---|---|---:|---:|---:|
| desktop | cold | 152 | 88 | -42.1% |
| desktop | warm | 104 | 52 | -50.0% |
| mobile | cold | 1112 | 752 | -32.4% |
| mobile | warm | 392 | 248 | -36.7% |

### Readiness measurement correction

A later eager-login cohort retained two IA-customer driver outliers of 4,240 and
3,340 ms, causing its driver p95 gate to fail. Their dashboard resources completed
at 1,941 and 879 ms, LCP was 1,996 and 928 ms and neither had a browser long task.
The failed 480-observation report is retained as
`browser-eager-driver-polling-failure.json`.

The final portal clock uses browser-native observation of the complete authorized
first page, enabled controls, pagination, no blocking overlay and stable layout
across two full frame intervals. Navigation begins on the actual link event and
requires the new destination DOM. Driver timings and outliers are retained in
separate fields; none is removed from the raw data. Nineteen negative/positive
browser instrumentation guards passed. A targeted 40-observation IA-customer
cohort measured native p95 ready of 659.5 ms desktop and 2,050 ms mobile, while
the retained driver p95 was 928 and 3,180 ms.

The helper is specific to the nonempty seeded fixture with Organization and
Status controls; empty/error journeys have separate functional coverage. Earlier
driver-based ready times must not be compared directly with final browser-native
ready times. The fresh baseline diagnostic above used the same final observer
after capacity/recovery. LCP and direct API comparisons retain
their own unchanged clocks.

The final LCP/CLS capture also waits for the actual font-stylesheet load/error
event before `document.fonts.ready`, followed by two paints and an observer flush.
A controlled delayed-CSS probe demonstrated that FontFaceSet alone could report
ready at 190 ms with CSS still pending; stylesheet settlement completed at 886 ms.
That control is diagnostic, not an acceptance timing. The earlier 458-observation
cohort was stopped and retained as `browser-rtl-before-font-barrier-en.json`.
Final gates require the expected active stylesheet, registered sheet and successful
terminal load; missing ResourceTiming can only be explained with that explicit
sheet/event proof. Native-ready timing remains independent of font settlement.

## API, capacity and recovery

The final asserted CLI exited successfully after 60 seconds of ramp and 1,800
seconds of steady load: 86,519 requests including ramp, 85,036 steady requests,
zero HTTP/semantic errors or redirects, and worst role/route p95 of 168.047 ms.
Elapsed monotonic time was 1,862.6 seconds; workload phase durations use this
clock rather than wall-clock timestamps. The mix was 40 distinct authenticated
accounts plus 10 anonymous virtual clients, with 0.8–1.2-second think time.
Protected bootstrap requests checked expected kind/user during ramp and initial
cycles; no sessions were renewed during the timed workload.

One coordinated eight-observation admin/IA-manager desktop/mobile cohort added
browser traffic during steady state. Every observation had native complete-page
and settled-font proof; maximum dashboard ready was 2,206.3 ms and navigation
132.4 ms. This is a small under-load spotcheck, not p95 acceptance evidence.
The independent 640-observation matrix supplies the isolated browser percentiles.

Recovery completed 160 requests (32 role/routes × 5) without HTTP/semantic errors;
the slowest recovery route p95 was 159.585 ms. All 13 source/assets/cache/rollback
checks passed: 353 source files and 55 assets matched the frozen manifest, 483
baseline files matched commit `0caa550`, and gzip parity, public-content 304,
private/error `no-store`, muted mail and paused scheduler remained correct.
Main JavaScript measured 518,970 decoded bytes and 161,684 actual gzip bytes.
This wire measurement uses proxy level 5; build gzip estimates use another level.

The runtime source/assets digest stayed unchanged throughout the run. The final
manifest's source digest is `e8e61b10c37aad3d8fd2d0ccdd3469c46e3cb1d913c3e851404328256f1132ab`
and asset digest is `7baf03088d7b0cddefccef9b3a7845d3574c6aaafcdea1feb76ead709c39cb25`.
The measured build had app version metadata 3.0.1. Release 3.0.2 changes version
metadata and documentation after testing; the measured source/asset hashes above
identify the exact tested build. Destination deployment remains unverified.

There were 64 infrastructure snapshots spanning start, 30-second intervals and
end. Maximum observed interval-average host CPU was 32.36%, peak one-minute load
2.942 and minimum available memory 25,392.3 MiB. The four optimized workers began
at 107.45–109.39 MiB RSS, ended at 106.35–110.23 MiB and peaked at 113.93 MiB.
Database `SELECT 1` RTT p95/max was 0.130/0.434 ms; Redis connection/PING p95/max
was 0.234/0.840 ms. Observed database connections peaked at 5 and running queries
at 3, including the diagnostic connection; the slow-query counter did not increase.
These are local-host observations, not destination sizing recommendations.

The earlier 86,263-request run remains archived as intermediate evidence under
`intermediate-cookie-fix-pre-eager-login/`; it is not substituted for this final run.

Paired direct-Gunicorn probes use five baseline and five optimized requests per
role/endpoint on the same 5× fixture. This is a repeated local diagnostic, not a
field p95 claim. All nine dashboard response hashes and decoded sizes match
exactly. All nine dashboard API medians improved in this diagnostic set; it is
not a universal timing claim for every workflow. Backend source is byte-identical
after both the eager-login and RTL corrections, as recorded in the functional
manifest. The 227 backend checks apply through that verified continuity; all
101 mocked and 13 native browser checks were rerun on the final frontend.

| Dashboard role | Baseline median | Optimized median | Baseline SQL count p95 | Optimized SQL count p95 |
|---|---:|---:|---:|---:|
| GRC admin | 6,676.132 ms | 91.447 ms | 9,599 | 189 |
| IA customer | 3,961.236 ms | 97.024 ms | 9,057 | 144 |
| IA consultant | 10,343.693 ms | 97.821 ms | 34,128 | 163 |
| IA reviewer | 9,652.957 ms | 94.798 ms | 33,798 | 162 |
| IA manager | 11,525.122 ms | 111.905 ms | 40,991 | 270 |
| GRC customer | 4,518.455 ms | 110.225 ms | 9,102 | 189 |
| GRC consultant | 10,233.642 ms | 117.193 ms | 34,173 | 208 |
| GRC reviewer | 10,176.842 ms | 116.207 ms | 33,843 | 207 |
| GRC manager | 9,647.273 ms | 120.040 ms | 33,033 | 245 |

The original single-baseline/five-optimized diagnostic remains retained separately;
its baseline is not represented as a repeated measurement or baseline p95.

### Desktop cold-login comparison and correction

Matching repeated baseline and intermediate cohorts contain ten cold and ten warm
loads per device. Desktop cold-login LCP p75 increased from 184 to 404 ms, exceeding
the 10% comparison rule despite meeting the absolute budget. In-page heading paint
medians increased from 171 to 403 ms, so the regression is real. Playwright's
heading assertion added polling delay to some ready-time samples and is reported
separately from browser paint.

The paired font-CSS medians were both approximately 37 ms, DOMContentLoaded improved
from 90 to 77 ms and no long tasks occurred in representative desktop samples.
In one optimized sample, the login module completed at 128 ms and all resources by
173 ms, but the heading painted at 396 ms. Installed React DOM 19.3.1 explicitly
throttles some Suspense fallback completions to 300 ms; this matches the measured
delay after the new lazy login boundary. Warm median LCP remained 104 ms, while
mobile cold p75 improved from 1,112 to 908 ms.

The correction keeps the small login screen eager and retains lazy loading for
portal/provider screens. An intermediate 40-observation early-paint cohort measured
desktop cold/warm LCP p75 of 132/52 ms versus baseline 184/104 ms, and mobile
cold/warm 748/244 ms versus 1,112/396 ms. Desktop cold heading paint median fell
from 171 to 96 ms. These observations predate the stylesheet-settlement correction
and are retained as diagnostic history, not final before/after CWV evidence.
Intermediate source/assets and raw evidence are preserved
under `intermediate-cookie-fix-pre-eager-login/`.

### Arabic initial layout correction

The eager-login Arabic cohort subsequently exposed desktop login CLS p75 of
0.8879 and mobile warm CLS of 0.1429. The initial document direction was applied
in a React effect after the faster login screen could paint. The visual language
and direction update now runs before paint; cookie/local-storage persistence
keeps its existing effect. A strict corrected 40-observation Arabic-login cohort
passed: desktop LCP p75 88 ms and CLS p75 0.00223436; mobile LCP p75 740 ms and CLS
p75 0.00312749. The failed 160-observation cohort and its exact assets
remain under `intermediate-eager-login-pre-rtl-layout/` and
`browser-eager-rtl-cls-failure.json`. No capacity run began on this failed stage.

### Steady-state route evidence

All rows have zero HTTP/semantic errors and no redirects. API route aliases:
`bootstrap` = `/api/method/ia_maturity.grc.api.bootstrap`; `dashboard` =
`/api/method/ia_maturity.grc.api.dashboard`; `site_content` =
`/api/method/ia_maturity.grc.public.site_content`. Bytes are decoded response bytes.

| Role | Route | Steady samples | p95 ms | SQL count p95 | Bytes p95 |
|---|---|---:|---:|---:|---:|
| admin | `bootstrap` | 562 | 79.645 | 35 | 14,013 |
| admin | `dashboard` | 562 | 135.572 | 189 | 145,327 |
| admin | `/grc/auditor` | 561 | 75.241 | 43 | 1,318 |
| anonymous | `site_content` | 5,876 | 44.253 | 4 | 79 |
| anonymous | `/grc-site` | 5,875 | 63.283 | 16 | 1,318 |
| anonymous | `/login` | 5,873 | 57.390 | 16 | 1,318 |
| erp | `bootstrap` | 874 | 46.309 | 3 | 60 |
| erp | `/app/home` | 875 | 83.465 | 71 | 221,444 |
| grc_consultant | `bootstrap` | 3,351 | 82.138 | 54 | 1,263 |
| grc_consultant | `dashboard` | 3,353 | 154.649 | 208 | 41,064 |
| grc_consultant | `/grc/auditor` | 3,352 | 79.905 | 43 | 1,318 |
| grc_customer | `bootstrap` | 5,615 | 74.200 | 36 | 1,137 |
| grc_customer | `dashboard` | 5,616 | 149.440 | 189 | 39,504 |
| grc_customer | `/grc/customer` | 5,617 | 75.071 | 26 | 1,318 |
| grc_manager | `bootstrap` | 558 | 89.449 | 77 | 4,420 |
| grc_manager | `dashboard` | 558 | 168.047 | 245 | 46,453 |
| grc_manager | `/grc/auditor` | 558 | 74.089 | 43 | 1,318 |
| grc_reviewer | `bootstrap` | 1,119 | 79.999 | 54 | 1,233 |
| grc_reviewer | `dashboard` | 1,119 | 156.772 | 207 | 41,064 |
| grc_reviewer | `/grc/auditor` | 1,119 | 77.850 | 43 | 1,318 |
| ia_consultant | `bootstrap` | 3,368 | 80.721 | 54 | 1,348 |
| ia_consultant | `dashboard` | 3,369 | 136.310 | 163 | 145,034 |
| ia_consultant | `/grc/auditor` | 3,369 | 81.375 | 43 | 1,318 |
| ia_customer | `bootstrap` | 5,638 | 75.105 | 36 | 1,212 |
| ia_customer | `dashboard` | 5,640 | 133.108 | 144 | 112,544 |
| ia_customer | `/grc/customer` | 5,638 | 75.219 | 26 | 1,318 |
| ia_manager | `bootstrap` | 552 | 109.107 | 122 | 10,293 |
| ia_manager | `dashboard` | 551 | 150.941 | 270 | 145,381 |
| ia_manager | `/grc/auditor` | 552 | 80.244 | 43 | 1,318 |
| ia_reviewer | `bootstrap` | 1,122 | 84.128 | 54 | 1,307 |
| ia_reviewer | `dashboard` | 1,122 | 137.584 | 162 | 145,034 |
| ia_reviewer | `/grc/auditor` | 1,122 | 81.352 | 43 | 1,318 |

## Evidence and deployment boundaries

Sanitized raw artifacts live under the bench's ignored
`diagnostics/performance-20261113/` directory. They contain timing/status/query
counts, bounded aggregates, resource measurements and response/source hashes;
they do not contain cookies, credentials, OTP values, private response bodies or
SQL text. The private fixture file must never accompany these reports.

| Evidence | Artifact |
|---|---|
| English strict browser matrix | `browser-optimized-gzip-20-final.json`, `browser-english-summary.json` |
| Arabic strict representative cohort | `browser-arabic-gzip-20-final.json`, `browser-arabic-summary.json` |
| Comparable native/settled-font baseline diagnostic | `browser-baseline-native-final.json`, `browser-baseline-native-summary.json` |
| Matching settled-font login baseline | `browser-login-baseline-settled-final.json` (versus login rows in final English matrix) |
| Retained failed uncompressed budget | `browser-uncompressed-budget-failure.json` |
| Readiness driver-delay failure and guard evidence | `browser-eager-driver-polling-failure.json`, `readiness-native-guards.json`, `browser-native-readiness-ia-targeted.json` |
| Retained Arabic initial-layout failure | `browser-eager-rtl-cls-failure.json` |
| Under-load UI spotcheck | `browser-under-load-eager-final.json`, `under-load-ui-window-eager-final.json` |
| Sustained authenticated read workload | `load-50-30min-final.json` |
| Recovery and source/cache/rollback proof | `recovery-final.json`, `rollback-and-delivery-final.json`, `final-post-capacity-timeline.json` |
| Infrastructure measurements | 64 full-window samples inside `load-50-30min-final.json`; earlier partial companion retained only as intermediate evidence |
| Repeated paired API diagnostics | `baseline-5x-repeated-final.json`, `optimized-5x-repeated-final.json`, `api-comparison-repeated-final.json` |
| Application/asset and functional manifests | `final-source-manifest.json`, `functional-verification-manifest.json` |
| Verified helper cleanup | `harness-cleanup-final.json` |

After measurements, the four verified harness servers on ports 8011–8014 were
stopped. Existing preview 8007 still listened; database/Redis services, muted
fixture sites and private credentials were preserved. The operations guide's
commands reproduce the local lab without changing production services.

DevOps must run the read-only destination diagnostics and cache/compression checks
in [the operations guide](PERFORMANCE_OPERATIONS.md), then measure actual host
capacity and field/browser timings after deployment. Hosting changes, production
rollout, business UAT, external mail delivery and real-user INP remain deployment
acceptance items. No production configuration or data was changed by this lab.
