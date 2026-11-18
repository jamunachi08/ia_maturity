# Performance measurement, hosting and rollout

[README](../README.md) · [Architecture](introduction.md) · [Operations](GRC_OPERATIONS.md)

The performance work preserves the existing authentication, role/tenant boundary,
assessment workflow and immutable report history. Lab evidence is not proof of
real-user Core Web Vitals or of the moved sandbox's hosting capacity.

## Repeatable isolated lab

Use the bench owner in WSL `alphax_bench`, the bench Python environment and Node 24.
The tools refuse production URLs and operate only on a separate, muted
`grc-perf.local` database on `sites/.grc-db/mysql.sock`. `grc.local` is only the
initial local fixture source. Existing customer/staff workflows are not driven
against the live sandbox by these scripts.

```bash
./env/bin/python apps/ia_maturity/scripts/provision_local.py
./env/bin/python apps/ia_maturity/scripts/performance_environment.py prepare
./env/bin/python apps/ia_maturity/scripts/performance_fixture.py seed --scale 1
./env/bin/python apps/ia_maturity/scripts/performance_environment.py metadata
```

`prepare` clones the known muted local fixture database once. It creates its own
database account and site configuration, retains the original local encryption
key and refuses to overwrite an unrecognized site or database. Its credentials,
native session cookies and generated reports remain outside the app repository.
The performance site has mail muted and its scheduler paused.

The fixture creates 40 distinct accounts: 20 customers, 12 consultants, 4 reviewers,
2 managers, 1 GRC app admin and 1 ordinary ERP user. Each department has 22 synthetic
draft assignments at 1x and 110 at 5x, with related activity. The cloned site also
retains the existing fixture workflow states and reports. This measures the
growth of dashboard/activity reads; it is not a replacement for complete native
assessment, approval and release regression suites.

### Servers and baseline revision

Capture an immutable app snapshot and its matching built assets before modifying
code. The accepted initial snapshot for this cycle is app commit `0caa550` under
`diagnostics/performance-20261113/baseline-app`. The helper only accepts that
snapshot or the current app checkout. Never update baseline assets after changes.

Run two separate terminals, using the same worker count and database:

```bash
./env/bin/python apps/ia_maturity/scripts/performance_environment.py serve \
  --port 8011 --workers 4 \
  --app-root /home/frappe/frappe-bench/diagnostics/performance-20261113/baseline-app
./env/bin/python apps/ia_maturity/scripts/performance_environment.py serve \
  --port 8012 --workers 4
```

These are loopback-only Gunicorn sync workers, not the Werkzeug development
server. The dedicated lab middleware serves the selected revision's assets and
adds local-only `Server-Timing` and `X-GRC-Perf-SQL-Count` headers. It records query
count and duration without logging SQL text, passwords, tokens or response bodies.
It does not simulate the destination reverse proxy's compression or cache policy.
Restart the optimized workers after changing imported Python code.
After rebuilding assets, restart them as well so cached generated templates cannot
reference deleted chunk names. Keep the retained baseline revision untouched.

Freeze the app and production-built assets, archive any previous cohort evidence,
then stamp the exact final files before acceptance:

```bash
./env/bin/python apps/ia_maturity/scripts/performance_manifest.py \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/final-source-manifest.json
```

The manifest separately hashes source-file and built-asset SHA256 mappings.
Capacity's `application_source_sha256` is a different runtime drift digest over
file paths and bytes, including generated assets. Compare each digest with its
own before/after value; these two algorithms are intentionally distinct.

### Compressed-delivery rehearsal

The local bench has no nginx binary. For the deployment rehearsal, use the
unprivileged loopback helper in front of each Gunicorn revision:

```bash
./env/bin/python apps/ia_maturity/scripts/performance_proxy.py --port 8014
./env/bin/python apps/ia_maturity/scripts/performance_proxy.py --port 8013
```

Port 8014 forwards only to baseline 8011; port 8013 forwards only to optimized
8012. Both apply actual gzip level 5 to eligible HTML/JS/CSS/JSON, preserve private
response policy, add `Vary: Accept-Encoding`, and give only fingerprinted static
assets a public immutable lifetime. There is no private response cache and no
request logging. Verify decoded payload hashes, `Content-Length`, cookies,
conditional public-content 304 responses and cache headers before measurement.
The helper is not a production nginx replacement or nginx capacity certification.

Use 8014/8013 for paired browser and capacity acceptance, and 8011/8012 for direct
backend diagnostics. The initial uncompressed optimized run exceeded the mobile
dashboard budget even though backend work was near 100 ms; its failure evidence
is retained. Compression and correct static delivery are deployment requirements,
not optional assumptions hidden in a passing result.

Authenticate fixture accounts through native password login or the real customer
`verify_code` endpoint before measurement:

```bash
./env/bin/python apps/ia_maturity/scripts/performance_fixture.py sessions \
  --base-url http://127.0.0.1:8011
```

For customer fixtures, the guarded helper creates a pending single-use challenge
locally rather than sending SMTP mail, then calls the normal verification API.
The session is genuine, but this does not demonstrate inbox delivery. Staff use
their actual password/MFA path. The 40 account records and cookies are private.

### HTTP, database and browser measurements

Run baseline and optimized probes sequentially on the same dataset. Do not run
heavy tests or another load generator at the same time as an acceptance run.

```bash
./env/bin/python apps/ia_maturity/scripts/performance_probe.py probe \
  --base-url http://127.0.0.1:8011 --label baseline-1x --repetitions 10 \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/baseline-1x.json
./env/bin/python apps/ia_maturity/scripts/performance_probe.py probe \
  --base-url http://127.0.0.1:8012 --label optimized-1x --repetitions 10 \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/optimized-1x.json
```

Repeat after `performance_fixture.py seed --scale 5`; seeding adds reserved data
only, and rerunning 1x does not delete 5x data. Record the actual row counts and
fixture scale with every result. The probe records the first request separately
from later samples; it does not pretend that a running worker's caches are cold.
Response hashes compare API contents without retaining response bodies. An
unordered `managed_entities` array may vary between worker processes; compare
its membership separately from ordered table rows and response fields.

For browser measurements, from `apps/ia_maturity/grc`:

```bash
GRC_RUN_PERFORMANCE_LIVE=1 \
GRC_BASE_URL=http://127.0.0.1:8013 \
GRC_PERFORMANCE_ITERATIONS=10 GRC_PERFORMANCE_ASSERT_BUDGETS=1 \
GRC_PERFORMANCE_BROWSER_OUTPUT=/home/frappe/frappe-bench/diagnostics/performance-20261113/browser-optimized.json \
npx playwright test tests/performance-live.spec.ts
```

The test covers public landing/login, IA/GRC customer/consultant/reviewer/manager,
GRC admin and ordinary ERP. Each route has a browser-cache-disabled cold load and
a warm load. The desktop profile uses 20 ms latency, 80 Mbps download and no CPU
slowdown; mobile uses 150 ms latency, 4 Mbps download and 4x CPU slowdown. It records
usable-content time, LCP, layout shifts, resource transfer sizes and warm internal
navigation. No browser trace, video or secret-bearing screenshot is saved.
Portal ready time uses the browser's navigation-origin clock. A requestAnimationFrame
observer requires all four numeric cards, the complete first table page determined
from pagination total, complete table cells, usable search and both Organization
and Status selectors, laid-out pagination and no loading or blocking overlay. The
geometry stays stable for three callbacks, covering two full frame intervals.
Rows below the mobile fold are allowed and disabled Previous-page buttons are
legitimate. This predicate applies to the nonempty seeded fixture with two filters;
empty/error states retain separate functional coverage.

Internal navigation starts at the actual link event timestamp. It requires the
expected destination URL and Assessments heading, removed dashboard cards and the
same complete table/toolbar predicate. `driver_ready_ms` and
`driver_navigation_ms` retain Playwright timing separately. Driver assertion
polling can lag an already usable page; it is not the primary portal timer.
Interaction samples are not field INP. The default two cold/warm samples per route
are diagnostic only. Set `GRC_PERFORMANCE_ITERATIONS=10` for 20 observations per
route/profile, and `GRC_PERFORMANCE_ASSERT_BUDGETS=1` to enforce the p75 LCP/CLS and
p95 dashboard/navigation budgets. Neither setting turns lab data into field data.
LCP and CLS are read after the font stylesheet's actual load/error event, then
`document.fonts.ready`, two browser paints and an observer flush. This ordering
matters because an asynchronous stylesheet can still be pending when the initial
FontFaceSet reports ready. The report records stylesheet event, registered-sheet
and resource-timing proof; strict GRC gates require the one expected active font
stylesheet to load successfully. Native portal readiness retains its independent
navigation clock. Each
sample then performs a safe language toggle or portal navigation and records
Event Timing observations, when the browser exposes them. An absent event above
the 16 ms observation threshold is recorded explicitly; it is not a measured
zero or a field INP value. Native ERP setup does not have an interaction gate.

Repeat the absolute budgets on the representative Arabic public/login, GRC
customer and IA manager routes in both device profiles:

```bash
GRC_RUN_PERFORMANCE_LIVE=1 GRC_BASE_URL=http://127.0.0.1:8013 \
GRC_PERFORMANCE_LANGUAGE=ar \
GRC_PERFORMANCE_ROLES=anonymous,login,grc_customer,ia_manager \
GRC_PERFORMANCE_ITERATIONS=10 GRC_PERFORMANCE_ASSERT_BUDGETS=1 \
GRC_PERFORMANCE_BROWSER_OUTPUT=/home/frappe/frappe-bench/diagnostics/performance-20261113/browser-arabic.json \
npx playwright test tests/performance-live.spec.ts
```

This is a representative Arabic cohort, not an all-role Arabic timing matrix.
Ordinary ERP navigation is also checked, but a clone with incomplete ERPNext
setup measures the native setup screen and cannot certify ERP dashboard speed.

### 50 concurrent clients

The load mix is 10 anonymous clients plus 40 distinct authenticated accounts across
all roles. Each virtual client cycles page/bootstrap/dashboard GETs with 0.8–1.2 s
think time. A 60-second ramp is excluded from steady-state percentile summaries.
This is an authenticated application-read capacity test; browser asset transfer,
SMTP and assessment-writing/review flows have separate acceptance evidence.

```bash
./env/bin/python apps/ia_maturity/scripts/performance_probe.py load \
  --base-url http://127.0.0.1:8013 --label optimized-5x-50clients \
  --duration 1800 --ramp 60 --assert-acceptance \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/load-50-30min.json
```

The report is provisional until `complete` is true and elapsed time includes the
entire 30-minute steady state. Require zero unexpected statuses/timeouts, inspect
the 95th percentile by role and route, and run a recovery probe after completion.
Do not label a short smoke run as 30-minute acceptance. Capture host CPU/memory,
database/Redis latency and worker saturation alongside the result. Preserve a
failing report instead of overwriting it as success.
`--assert-acceptance` exits nonzero for an incomplete/short run, wrong client count,
HTTP/semantic failures (including ramp), source drift or failed timing/resource
gates. Omit it only for explicitly labeled short diagnostic smokes.
The runner captures CPU/load, available memory, each lab worker's RSS and CPU,
database connection/activity counters and Redis round-trip time every 30 seconds.
It stamps the application-source digest before and after the run and records the
release source-manifest digest. Protected APIs must return the expected session
kind and response shape; a login redirect or HTTP 200 error envelope is counted
as a failure. Reports contain status/error categories and hashes, not bodies or
credentials.

Coordinate one small browser cohort during steady state to check usable UI
under the 50-client read workload. Record its window as extra traffic and keep
its eight cold/warm observations separate from the isolated percentile gates.
Do not run PDF generation, builds or unrelated regression suites during this
capacity window. Afterward, run a quiet recovery probe before baseline or other
heavy comparisons. The read workload does not represent 50 simultaneous browser
logins, OTP requests or assessment writes.

After recovery, verify source/assets, real compressed-body parity, conditional
public-content responses, private/error cache policy and the retained baseline
build without changing the database or switching any live traffic:

```bash
./env/bin/python apps/ia_maturity/scripts/performance_verify.py \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/rollback-and-delivery-final.json
./env/bin/python apps/ia_maturity/scripts/performance_report.py \
  --browser /home/frappe/frappe-bench/diagnostics/performance-20261113/browser-optimized.json \
  --load /home/frappe/frappe-bench/diagnostics/performance-20261113/load-50-30min.json \
  --output /home/frappe/frappe-bench/diagnostics/performance-20261113/summary.json
```

The rollback helper verifies all archived tracked files against the retained Git
commit and serves its matching baseline HTML/static asset on the separate local
port. It is a code/asset rollback rehearsal, not a production service-manager,
database-restore or DNS-switch rehearsal. No new database index migration is
required by this optimization; retain the normal backup/restore release process.

## Destination-server verification for DevOps

Run on the moved sandbox before production acceptance. Record app commit,
Frappe/Python/MariaDB versions, host region/resources, worker count, installed
frontend assets and actual data volumes. Confirm the correct site's
`grc_enabled` and `host_name` following the README setup checklist.

After placing the diagnostic helper from this revision on the destination bench,
DevOps can run these read-only diagnostics from that bench directory:

```bash
git -C apps/ia_maturity rev-parse HEAD
./env/bin/python apps/ia_maturity/scripts/performance_destination_check.py \
  --site YOUR_GRC_SITE --public-url https://your-grc-domain.example/grc-site
ps -eo pid,comm,pcpu,pmem,rss | grep -E 'gunicorn|python'
```

The helper emits only selected non-secret settings, versions, aggregate row
counts, database/Redis round-trip timings and selected anonymous response headers.
The optional HTTP check makes one anonymous request without redirects. Remove
`--public-url` for database/Redis-only diagnostics. It neither sends email nor
changes configuration. Do not substitute `show-config`, raw environment dumps,
cookie-bearing headers or private response bodies when sharing evidence.

1. Measure browser DNS/TLS/TTFB, connection latency, compressed transfer sizes
   and the request waterfall for public, login and each role's dashboard.
2. Inspect Gunicorn/web-worker queueing and CPU/memory, MariaDB slow queries and
   execution plans, Redis latency and whether other sites compete for resources.
   Increase workers only after measuring CPU/memory and database capacity.
3. Verify gzip or Brotli for JS/CSS/JSON through the actual proxy. The local
   direct Gunicorn lab serves uncompressed assets. The loopback gzip proxy is a
   delivery rehearsal; neither proves destination compression is configured.
4. Give content-hashed Vite JS/CSS under
   `/assets/ia_maturity/grc/assets/` a long public immutable lifetime at the
   reverse proxy. Apply this only to fingerprinted static files; HTML entry
   points and unversioned files must not inherit that rule. Integrate with the
   existing generated Frappe nginx configuration instead of replacing it.
5. Verify authenticated HTML, authentication responses, private files and normal
   app API responses use `Cache-Control: no-store`. Approved public-content JSON
   may revalidate with a site/published-content ETag and `private, no-cache`;
   a matching conditional request may return 304. Private preview/draft content
   must never share a public-content cache entry. Verify publication invalidates
   the ETag and revoked access is denied on the next protected request.
6. Compare deployment and warm-navigation timings to the fixed lab profiles.
   Review network/hosting differences explicitly rather than attributing every
   delay to app code. Confirm actual customer OTP and PDF email delivery in the
   designated deployment environment; never unmute the local fixture sites.

## Rollout and rollback

First replay the original backend/security/browser journeys and compare response
contents, counts, ordering, access revocation and frozen reports. Rehearse any
index migration on a restored isolated copy; inspect `EXPLAIN` before/after.
This performance change must not silently alter response contracts or publish
draft content, modify questionnaire/scoring snapshots or rebuild released PDFs.

Deploy in reviewable batches through the established release process. Back up the
database, files and encryption key, retain the prior app revision and its built
assets, clear only the relevant caches and restart web/worker processes. Verify
public landing, native customer/staff/ERP sign-in, role dashboards, autosave,
review/release, private downloads and mail after switching traffic.

Monitor per-route response percentiles, error/timeouts, database slow-query counts,
worker saturation and cache/publication behavior. An unexpected permission/data
exposure, changed score/report output, broken workflow or unexplained critical
route regression above 10% blocks rollout. Revert code and matching assets through
the service manager; restore a rehearsed backup if a migration cannot be safely
reversed. Do not disable `grc_enabled` as an access-control rollback.

Local evidence and deployment acceptance remain separate. Production rollout,
business UAT, external inbox delivery and real-user CWV/INP must not be marked
complete based on synthetic lab measurements.
