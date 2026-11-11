# Repository Guide for Coding Agents

## Project map

- `frontend/` is the Next.js App Router application. Routes live in `src/app/`;
  feature components live in `src/components/`.
- `backend/` is the FastAPI application. Routers are in `app/api/v1/`, domain
  code in `app/modules/`, workers in `app/workers/`, migrations in
  `alembic/versions/`, and tests in `app/tests/`.
- `contracts/` contains Solidity sources, Foundry tests, and release artifacts.
- `infrastructure/` contains deployment, local-stack, and operational scripts.
  `.github/workflows/` depends on these paths.
- `tests/` contains root repository and operations checks. `docs/` contains
  architecture, specs, runbooks, evidence, and handoffs.

Read [frontend/AGENTS.md](frontend/AGENTS.md) before Next.js changes; its
Next.js rules are generated and include a local documentation requirement. Read
[backend/README.md](backend/README.md) for backend boundaries and commands.

## Change boundaries

- Search the existing domain before adding a component, utility, route, service,
  script, or document. Reuse an existing module when it already owns the
  behavior.
- Keep public URLs, API contracts, database schema, applied migration history,
  environment-variable names, contract addresses, and deployment paths stable.
- Treat authentication and authorization, payment and webhook handling, wallet
  balances and ledger entries, withdrawals, review decisions, migrations, smart
  contracts, and production configuration as high-risk areas. Prepare a separate
  plan and get approval before changing their behavior or contracts.
- Before moving a path, search static and dynamic imports, aliases, routes,
  asset URLs, tests, CI, deployment scripts, and Markdown links. Update every
  verified reference and run the checks that cover those consumers.
- Keep route handlers at the HTTP boundary and business rules in existing domain
  modules. Follow existing test placement: frontend tests are generally
  colocated; backend tests are centralized under `backend/app/tests/`.

## Verification

Use the root scripts as the source of truth. Before handing off source changes,
run the relevant format, lint, typecheck, and test commands from `package.json`.
Run `npm test` for root, frontend, and backend suites; run `npm run test:e2e`
for browser-flow changes. Use `contracts/README.md` for contract-specific
verification.

For deployment or production-configuration changes, also verify the affected
GitHub Actions workflow and the matching `infrastructure/` scripts. Report
checks that could not run and the reason.

## Repository hygiene

- Keep `.env` files, credentials, personal data, caches, build output,
  screenshots from local runs, and test reports out of Git. Never print secret
  values in audit output.
- `docs/handoffs/` and `docs/specs/` use explicit allowlists in `.gitignore`.
  Add an exception only for a durable document that is linked from tracked
  documentation or is a required handoff; verify its Git status afterward.
- Add only the files in scope to Git. Do not use `git add .` or `git add -A` by
  default.
- Do not commit, push, merge, or deploy unless the user explicitly asks.
- Keep runtime and design assets, plans, screenshots, logs, test reports, and
  exported output out of the repository root. Keep required workspace config
  files there.
- Before adding an asset, search for an equivalent and check every reference.
  Keep runtime assets with their owning app; keep design-only source files in
  `docs/design/source-assets/`. Use descriptive lowercase kebab-case names.
- Do not create root `plans/`, `animation-plans/`, or `design-plans/`
  directories. Put durable specifications and design guidance in the existing
  `docs/` structure and update verified links when files move.
- Keep local test output and session-only agent notes out of Git. Update an
  existing durable document when it needs correction; do not add a report just
  to record cleanup work.
