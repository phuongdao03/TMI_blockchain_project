# Repository Standardization Audit and Handoff

Date: 2026-11-10

## Scope and result

The repository was audited before editing. The working tree was clean on
`main...origin/main`. Git tracks 2,396 files: 1,046 backend, 950 frontend, 265
docs, 40 infrastructure, 38 contracts, 12 root tests, and 45 files across GitHub
configuration, root configuration/assets, and planning directories. The
workstation also had 583 ignored paths, mostly caches, build output, test
artifacts, and logs. No tracked `.env`, cache, build output, or test report was
found. The local `.env` was not read.

The application roots already form a coherent monorepo. Frontend and backend
features are grouped by domain, contracts and infrastructure have clear roots,
and existing tests cover critical workflows. The initial conclusion that no
source move was justified was too broad: later file-level review found an
oversized community workspace and domain API DTOs mixed in shared files. Those
boundaries have since been split. This increment fixes verified documentation
and ignore-policy gaps and adds repository-specific agent guidance.

## Verified implementation map

| Area                              | Evidence                                                                   | Status                                                                            |
| --------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Identity and access               | `backend/app/modules/auth/`, `users/`; `frontend/src/app/(auth)/`          | Implemented                                                                       |
| Dossiers and evidence             | `backend/app/modules/dossiers/`, `supplements/`; frontend dossier features | Implemented                                                                       |
| Review and approval               | `reviews/`, `council/`, `voting/` modules and API routes                   | Implemented                                                                       |
| Certificates and proof            | `certificates/`, `blockchain/`; Solidity contracts and release checks      | Implemented, with legacy blockchain files excluded from active production runtime |
| Payments, wallet, withdrawals     | `payments/`, `billing/`, `wallet/`                                         | Implemented; high-risk behavior                                                   |
| Affiliate and promotions/vouchers | `affiliate/`, `promotions/`                                                | Implemented                                                                       |
| Membership and advertising        | `memberships/`, `advertising/`                                             | Implemented                                                                       |
| Community and moderation          | `community/`, `audit/`, administrative API routes                          | Implemented                                                                       |

The backend has 32 tracked feature packages, 51 Python files in `app/api/v1/`
(including the package initializer), 370 test files, and 160 ordered Alembic
revisions. `app/main.py` registers routers from `app/api/v1/`; tests are
centralized in `backend/app/tests/`. The migration chain is contiguous and ends
at `0160_dynamic_dossier_fees`. The frontend uses route groups under
`frontend/src/app/`, feature components under `frontend/src/components/`, and
the `@/*` alias.

## Findings

| Severity | Evidence                                                                              | Finding and action                                                                                                                                                                                                                                                                                                                                                                            |
| -------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Low      | `backend/README.md`                                                                   | It described a planned layout and claimed every module owned a router and tests. Updated it to match the current API, domain, migration, and centralized test locations.                                                                                                                                                                                                                      |
| Low      | `README.md`, `docs/UX_COPY_QA_REPORT.md`, `docs/payment-qr-and-admin-history-plan.md` | Each linked to an existing handoff that `.gitignore` hid from Git. Added narrow allowlist entries so the referenced documents are reviewable.                                                                                                                                                                                                                                                 |
| Low      | Root cache directories and `.gitignore`                                               | `.mypy*`, `.tmp-mypy*`, `.tmp-quality-*`, and `.tmp-playwright-*` were local generated artifacts without root ignore coverage. Added targeted patterns; kept all local artifacts in place.                                                                                                                                                                                                    |
| Medium   | `docs/` root and local Markdown-link scan                                             | Git tracked 134 Markdown files directly under `docs/` at audit time. Four clearly categorized runbooks/guides have since moved to existing folders, leaving 130 at the root. The updated scan checked 348 relative links with no missing local targets; six UIUX evidence outputs remain local-only text paths. The moved files and four handoffs are untracked review items until committed. |
| Review   | Root brand assets and `frontend/public/assets/brand/`                                 | `logo-tinh-hoa-viet.png` and `trong-dong.png` are byte-identical across root, frontend, and backend copies; root `chim-lac.jpg` also duplicates a browser asset. Application code references the frontend/backend copies. Root copies may be source artwork, so they were preserved.                                                                                                          |
| Review   | `frontend/tsconfig.json`, `frontend/next.config.ts`                                   | Type exclusions include several `.next-*` preview/build names. Next supports configurable output directories; validate against typecheck and E2E use before pruning.                                                                                                                                                                                                                          |
| Review   | `backend/app/modules/*/*service.py`                                                   | Several business services are large: HR 3,616 lines, advertising inventory 2,009, payments 2,008, reviews 1,915, dossiers 1,822, and withdrawals 1,673. These need domain-specific design and regression coverage; no splitting was done.                                                                                                                                                     |
| Review   | Root media and `rank_assest/`                                                         | Some filenames look temporary and root brand copies are duplicated, but these may be design sources. The `rank_assest` directory is referenced by its own README. Preserve until an asset owner confirms disposition.                                                                                                                                                                         |
| Review   | `frontend/src/lib/api/client.ts`, `types.ts`; backend feature packages                | Frontend naming and tests are mostly consistent. Backend has 32 feature packages with recurring but non-uniform service/repository files. No unused source or duplicate service was proven; similarly named helpers remain imported. See Phase 3 proposals below.                                                                                                                             |

GitHub Actions and deployment are path-sensitive. Keep `infrastructure/`,
workflow paths, Vercel routing, contract release files, API routes, assets,
environment variables, and migration names stable until every consumer is
mapped. Authentication, review decisions, payments, wallet/ledger behavior,
webhooks, and withdrawals remain high-risk change areas.

## Current and proposed structure

Current application structure is retained:

```text
frontend/src/app/                 route groups and public URLs
frontend/src/components/<domain>/ feature UI
backend/app/api/v1/               HTTP routers
backend/app/modules/<domain>/     business capabilities
backend/app/{core,db,workers}/    shared runtime and workers
backend/alembic/versions/         ordered Alembic history
backend/app/tests/                backend tests
contracts/                        Solidity, Foundry tests, release tooling
infrastructure/                   local, deployment, and operations tooling
tests/                            root repository checks
```

For future documentation cleanup, use a consistent `docs/` taxonomy:

```text
docs/
  architecture/
  adr/
  guides/
  runbooks/
  specs/
  handoffs/
  audits/
  evidence/
```

Some of these directories already exist. Do not move the current root documents
as one batch: first assign each document an owner/category, then update and
verify all relative links. Keep Next.js-required files, migrations, deployment
configuration, contracts, and currently served assets in their existing paths.

## File migration matrix

No application source file was moved. Four existing documents were moved into
directories that already match their responsibility; their inbound references
were updated. All changes are documentation-only and reversible by moving each
file back and restoring the listed references.

| Old path                                   | New path                                                    | Reason                                                    | Verified dependencies updated                                  | Risk and verification                  |
| ------------------------------------------ | ----------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------- |
| `docs/FINANCIAL_RECONCILIATION_RUNBOOK.md` | `docs/runbooks/financial-reconciliation.md`                 | Operations runbook belongs with existing runbooks         | `docs/WALLET_LEDGER_DESIGN.md`                                 | Low; Markdown-link scan and root tests |
| `docs/DEPLOYMENT_NOTES.md`                 | `docs/runbooks/community-deployment-and-rollback.md`        | Community deployment/rollback guide belongs with runbooks | `docs/TASKS.md`; internal link to `deployment-and-rollback.md` | Low; Markdown-link scan and root tests |
| `docs/DEPLOYMENT_AND_ROLLBACK.md`          | `docs/runbooks/wallet-affiliate-deployment-and-rollback.md` | Wallet/Affiliate release procedure belongs with runbooks  | `docs/WALLET_WITHDRAWAL_FLOW.md`                               | Low; Markdown-link scan and root tests |
| `docs/VOUCHER_ADMIN_GUIDE.md`              | `docs/guides/voucher-administration.md`                     | Operator guide belongs with existing guides               | `docs/VOUCHER_SYSTEM.md`                                       | Low; Markdown-link scan and root tests |

Duplicate brand assets, legacy blockchain files, and generated screenshots
remain review items, not deletion instructions. No generated artifact was
tracked or removed in this increment.

## Changes made

- Added root `AGENTS.md` with the monorepo map, high-risk boundaries,
  verification expectations, and ignore/commit rules.
- Updated `backend/README.md` to describe the existing FastAPI layering and
  centralized tests.
- Updated `.gitignore` for observed local cache/output prefixes and allowlisted
  the handoffs referenced by tracked docs, plus this audit.
- Linked this handoff from the root README.
- Moved four runbooks/guides into the existing `docs/runbooks/` and
  `docs/guides/` folders and updated all verified inbound references.
- Replaced six links to ignored local UIUX outputs with explicit local-only
  paths; the versioned evidence link remains.
- No tracked generated artifact was found. No asset was deleted: identical root
  copies may be source artwork, while frontend/backend copies remain in their
  runtime paths.
- No application source, route, API, migration, contract, or runtime
  configuration was moved or changed.

## Verification baseline and result

Before edits, `npm.cmd test` completed successfully:

- Root: 6 passed.
- Frontend: 1,074 passed across 248 Vitest files.
- Backend: 1,349 passed, 3 skipped, 289 warnings across 1,352 collected tests.

Warnings were deprecations from FastAPI/Starlette, `websockets`, SQLAlchemy
reflection of an expression index, and Python's SQLite datetime adapter. No test
failed. The available Python is 3.12.8; the repository pins 3.12.13.

After Stage 2, root structure tests passed again (6/6), `git diff --check`
passed, and the Markdown scan found 348 links with no missing local targets. The
focused run of the three environment-gated integration tests confirmed the
expected skips. The full application suite was not rerun because Stage 2 changed
documentation paths only. Stage 1 `format:check`, `lint`, and `typecheck`
passed; the changed docs are not included in the root formatting command. A
targeted Prettier check found eight docs that were already unformatted at
`HEAD`; they were left alone to avoid unrelated whole-file formatting changes.

### Backend warning classification

The previous full run reported 289 warnings. Its complete warning log was not
saved, so the total is known but exact per-cause counts cannot be recovered. The
only saved pytest log is from 2026-08-16 and has different test counts; it was
not used to infer this run's distribution.

| Cause                                                                      | Severity                  | Assessment                                                                                                                   |
| -------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Starlette `TestClient` using `httpx`                                       | Low                       | Third-party deprecation; tests passed, but should be updated before the supported dependency removes the compatibility path. |
| `websockets.legacy` import                                                 | Low                       | Third-party deprecation; update the affected test/runtime import when the dependency migration is planned.                   |
| SQLite cannot reflect expression index `uq_community_profiles_username_ci` | Medium test-fidelity risk | SQLite migration tests cannot verify that PostgreSQL expression index. Keep a PostgreSQL migration/concurrency gate.         |
| Python SQLite default datetime adapter                                     | Low                       | Test-runtime deprecation that could become an error under a later Python version.                                            |

### Skipped backend tests

| Test                                                            | Skip condition                                                       | Risk not covered                                                                                         |
| --------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `test_postgres_serializes_simultaneous_final_slot_reservations` | `ADVERTISING_TEST_DATABASE_URL` must point to disposable PostgreSQL. | High: real row-lock protection against overselling is not verified by SQLite tests.                      |
| `test_gateway_reads_certificate_from_anvil`                     | `BLOCKCHAIN_INTEGRATION=1` is opt-in.                                | Medium: the backend-to-Anvil read path is not exercised in the default suite.                            |
| `test_concurrent_acceptance_creates_exactly_one_staff_account`  | Requires `STAFF_INVITATION_POSTGRES_TEST_URL`.                       | High: concurrent staff invitation acceptance/unique account creation is not verified against PostgreSQL. |

These tests use explicit `skipif` conditions; their assertions are intact. The
repository workflows do not configure the three opt-in variables, so CI also
does not exercise these integration paths by default. The Gitleaks wrapper could
not run locally: Docker Engine was unavailable and Docker configuration access
was denied. No local Gitleaks executable was installed. CI retains the redacted
full-history scan and synthetic canary. No secret values were read.

## Stage 3 - Increment 1: community admin workspaces

The community admin content module combined post, comment, and member workspaces
in one 1,430-line file. The three responsibilities now live in separate
feature-local modules. Common pagination, loading/error/empty states, date
formatting, and class tokens live in one shared primitives module. The original
module remains a re-export facade, so the parent workspace and tests keep their
existing import path. No API call, query key, action, copy, markup, route, or
authorization check changed.

| Old path                                                                 | New path(s)                                                                                                                                                  | Reason / affected dependencies                                                                                                                                                      | Verification                                                                                                                                                               |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| frontend/src/components/community/community-admin-content-workspaces.tsx | community-admin-posts-workspace.tsx; community-admin-comments-workspace.tsx; community-admin-members-workspace.tsx; community-admin-workspace-primitives.tsx | Isolate three independently tested workspaces; share existing repeated UI primitives. Parent workspace and both workspace test files still import through the compatibility facade. | Baseline 10/10 focused tests; after 10/10 focused and 1,074/1,074 frontend tests; frontend lint/typecheck, root formatting check, production build, and root tests passed. |

The first post-extraction check caught missing PAGE_SIZE and PostAction
declarations at the new module boundaries. They were restored in the shared
primitives and posts module; no assertions were changed or skipped. Final checks
pass. The generated .next output remains ignored and is not in Git status.

## Stage 3 - Increment 2: frontend API DTO modules

The shared `frontend/src/lib/api/types.ts` mixed several domain contracts. The
API envelope/activity, Community, Membership, and Advertising DTO declarations
now live in `api-contract-types.ts`, `community-types.ts`, `membership-types.ts`,
and `advertising-types.ts`. `types.ts` remains a type-only compatibility facade;
domain-only consumers import their types from the owning module. These changes
move declarations and type imports only; no runtime code or API contract
changed. Frontend typecheck, lint, 1,074 tests across 248 files, root tests,
format check, and production build passed.

## Stage 3 - Increment 3: backend user profile types

`backend/app/modules/users/service.py` no longer owns the `ProfileChanges`,
`EmploymentView`, and `ProfileView` declarations; they live in the feature-local
`users/types.py`. The API and tests import from that module. The service still
re-exports the same names through its imports for compatibility. No fields,
validation, persistence, or API response behavior changed. The two focused
profile suites passed 8/8; the full backend suite passed 1,349 tests, with 3
environment-gated skips. Backend Ruff, format check, and mypy passed.

## Stage 3 - Increment 4: CMS DTO boundaries

Frontend CMS contracts now live in `frontend/src/lib/api/cms-types.ts`; all
tracked consumers import them from that module. The unused CMS re-export was
removed from `types.ts`. Backend input dataclasses now live in
`backend/app/modules/cms/types.py`; the API and tests import them there, while
`CmsService` imports them for its annotations. No fields, routes, requests,
sanitization, authorization, persistence, or content behavior changed.

CMS/guide baseline tests passed 19/19 in the frontend and the corrected focused
backend run passed 17/17. After the move, the full frontend suite passed
1,074/1,074; lint, typecheck, production build, root tests/format, backend Ruff,
mypy, and format checks passed. A focused backend run without importing the
ranking model registry failed during test setup because SQLite metadata lacked
`ranking_snapshots`; preloading that model before the same tests passed. This is
an existing test-collection dependency, not a test assertion failure.

## Stage 3 - Increment 5: voting eligibility types

Static import analysis found a type dependency cycle between
`voting/eligibility.py` and `voting/vote_repository.py`: the repository builds an
`EligibilitySnapshot` declared by the eligibility service and used a local
import to avoid the cycle. The immutable snapshot now lives in
`voting/types.py`; the engine and repository both import it from there. The
static backend cycle scan is now clean. No eligibility rules, database queries,
transactions, or locking behavior changed. Focused CMS/voting tests passed
17/17; backend Ruff, mypy, and format checks passed.

## Second-pass structure and cleanup review

- `frontend/src/lib/api/client.ts` remains about 4,300 lines and owns many API
  objects. Its shared transport handles cookies, CSRF, refresh, and request
  errors; splitting it would cross authentication behavior, so it remains a
  separate reviewed project.
- `frontend/src/lib/api/types.ts` remains large after domain extractions. HR,
  wallet/affiliate, dossier/payment, review, certificate/blockchain, and
  public/search contracts still need separate dependency analysis before
  further moves.
- Largest remaining UI files include public work editor (1,947 lines), dossier
  workspace (1,344), blockchain signing (1,150), and dossier creation (1,109).
  They combine workflow state, permissions, or data editing; no safe extraction
  with existing coverage was established in this pass. CMS workspace also has
  four managers in one file and no dedicated component test, so it was kept.
- The duplicate scan found 16 exact-byte asset groups. Copies across backend
  and frontend are used by separate runtimes; root brand artwork is referenced
  by the brand specification, and `rank_assest/` has its own README. These were
  kept as source artwork or required runtime assets. Other suspicious filename
  matches were documentation screenshots, backup tooling, or real tests.
- No additional tracked file was safe to remove. The completed community audit
  plan remains the only cleanup deletion in this branch.

Local Gitleaks remains unavailable (no executable; Docker Engine unavailable).
The delivery workflow's `secret-scan` job checks out full history and runs
`infrastructure/scripts/verify-gitleaks.sh`. Its `e2e` job installs Chromium
and runs `npm --prefix frontend run test:e2e`; neither was run locally. Run the
workflow jobs `secret-scan`, `quality`, `e2e`, `migration`,
`operational-readiness`, and `public-security` before merge. The PostgreSQL
Advertising/staff-invitation tests remain explicitly environment-gated and
still need an isolated PostgreSQL CI database; Anvil coverage remains opt-in.

## Task commits

- `f187465` chore(repo): remove completed community audit plan.
- `2b0f62b` refactor(frontend): split community admin workspaces.
- `4b39c85` refactor(frontend): split domain API types.
- `5d03dd8` refactor(frontend): split advertising API types.
- `bf7b133` refactor(backend): separate user profile types.
- `3f369f0` refactor(cms): isolate contract types.
- `1217137` refactor(voting): isolate eligibility snapshot type.

Existing Stage 1/2 documentation and ignore-policy edits remain in the working
tree, unstaged and outside these task commits. No push, merge, or deployment
was performed.
