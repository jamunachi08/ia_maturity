# AlphaX IA Maturity v3.2.1

Patch release. No database changes, no patches, no new settings.

## Why

Deploying to a Frappe Cloud bench with Node 18.16 stopped at the asset build step:

```
$ npm --prefix grc run build
SyntaxError: The requested module 'node:util' does not provide an export named 'styleText'
```

Vite 8 (in the portal since 3.1.0) requires Node 20.19 or later. Benches on Node 20+ were unaffected.

## What changed

| File | Change |
|---|---|
| `grc/package.json` | `vite` ~6.4.6 (was ^8.3.4), `@vitejs/plugin-react` ^4.7.0 (was ^6.1.2), `engines.node` >= 18.16 |
| `grc/package-lock.json` | regenerated |
| `grc/vite.config.ts` | path alias via `fileURLToPath(import.meta.url)` instead of `import.meta.dirname` |
| `.github/workflows/ci.yml` | new job: portal build on Node 18.16, 20, 22, 24 |

## Verified

- Clean checkout, Node 18.16.0 / npm 9.5.1 (the versions in the failing log): `npm --prefix grc ci` and `npm --prefix grc run build` succeed.
- Node 22: build, `tsc --noEmit`, oxlint and Prettier pass.
- Portal output is the same app; no backend files changed.

## Deploy

Push and deploy as usual. Frappe Cloud runs `bench build --app ia_maturity`; no migrate step is needed for this release, though running one is harmless.

## Follow-up

`npm audit` reports high-severity advisories in development-only build tooling. None ship in the built portal. Review them when the benches move to Node 20+, at which point Vite can be raised again.
