# AlphaX GRC frontend

Doppio-scaffolded React + TypeScript + Vite + Tailwind application. Authentication and authorization are enforced by `ia_maturity.grc`; client route guards are presentation only.

Run `npm ci`, then `npm run build` or the bench-level `bench build --app ia_maturity`. Node 24 is the validated toolchain. Use `npm run lint` and `npm run test:e2e` for local checks.

See [architecture and workflows](../docs/introduction.md), [development criteria](../docs/DEVELOPMENT.md), [implementation](../docs/GRC_IMPLEMENTATION.md) and [operations](../docs/GRC_OPERATIONS.md).
