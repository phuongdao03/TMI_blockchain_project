# THV Master Remediation Plan

## P0-BILLING-V2 — Listed-price billing and finance operations

- [x] Preserve verified PayOS payment as the only automatic trigger for the
  blockchain/certificate pipeline.
- [ ] Add a versioned listed-price catalog and lock its snapshot at approval.
- [ ] Create one durable fee obligation automatically after dossier approval.
- [ ] Deliver in-app and email notifications that deep-link to the obligation.
- [ ] Create short-lived PayOS checkout sessions on user demand and allow safe
  regeneration after expiry.
- [ ] Replace the admin issue form with finance overview, transactions,
  reconciliation and a separate pricing configuration page.
- [ ] Verify service, API, RBAC, migration, UI, E2E, lint and build.

The completed admin-issued request flow is retained only as migration input; it
must not remain as a parallel production write path after Billing V2 cutover.

Specification: `docs/admin-issued-payment-flow-spec.md`.

### Billing V2 implementation slices

- [ ] B1 — Price catalog foundation (schema, repository, validation, seed).
  - [x] Versioned catalog/entry schema, effective-price resolver and reversible
    migration `0067`.
  - [ ] Publish/immutability API, permission checks and controlled initial seed.
  - Acceptance: exactly one effective published price resolves per dossier
    type/time; published versions are immutable.
  - Verify: migration, overlap, missing-price and permission tests.
  - Dependencies: approved initial price/tax decisions. Scope: M.
- [ ] B2 — Automatic obligation on approval.
  - [x] Durable obligation schema/migration `0068`, immutable price snapshot,
    idempotent domain service and fail-closed rollback tests.
  - [ ] Atomic council-approval integration (after checkout cutover is ready).
  - Acceptance: approval and obligation creation are atomic/idempotent and lock
    the catalog snapshot; failures alert operations without a fallback price.
  - Verify: workflow transaction, retry and concurrency tests. Dependencies: B1.
- [ ] B3 — Durable notification delivery.
  - [x] Atomic in-app payment-due notification with obligation deep link.
  - [ ] Email delivery intent/worker retry and delivery observability.
  - Acceptance: owner receives one in-app item and one email with a safe link to
    the obligation; retries do not duplicate notifications.
  - Verify: outbox, email-delivery and deep-link tests. Dependencies: B2.
- [ ] B4 — On-demand PayOS checkout.
  - [x] Owner-only idempotent checkout endpoint, locked obligation amount,
    30-minute TTL, migration link and webhook settlement.
  - [ ] Provider-state check before replacing an expired checkout.
  - Acceptance: checkout has a short TTL, can be regenerated safely, checks
    provider state before replacement and settles once from verified evidence.
  - Verify: gateway/service/webhook/expiry/idempotency tests. Dependencies: B2.
- [ ] B5 — Applicant billing UX.
  - Acceptance: account/dossier surfaces obligation automatically; mobile live
    QR, countdown, expiry recovery and delayed-webhook states have no overlap.
  - Verify: component tests and browser checks at 320/360/390/768px.
  - Dependencies: B3-B4. Scope: split by account card then billing page.
- [ ] B6 — Finance read model and reconciliation.
  - Acceptance: real summary definitions, paginated transactions and persisted
    mismatch cases reconcile to transaction evidence.
  - Verify: aggregate, pagination, permission and reconciliation tests.
  - Dependencies: B2-B4. Scope: split API/read model from UI.
- [ ] B7 — Pricing and finance UI cutover.
  - Acceptance: admin navigation uses `Tài chính`; pricing is separately
    permissioned; manual issue write path is removed after backfill verification.
  - Verify: RBAC, audit, responsive E2E, lint, typecheck and build.
  - Dependencies: B1-B6.

Checkpoint Billing 0: approve assumptions/open decisions before schema changes.
Checkpoint Billing 1: B1-B4 backend lifecycle and migration are green.
Checkpoint Billing 2: B5-B7 responsive E2E and finance totals are green before
legacy route removal.

## Objective

Deliver the THV brand migration and production hardening incrementally, without
changing existing service contracts, authorization semantics, blockchain
workflows, or release-gate behaviour unless explicitly approved.

## Dependencies

```text
Green baseline
  -> dynamic dossier persistence/API authorization
  -> semantic THV tokens and shared states
  -> public/applicant/operations shell migration
  -> browser and production release gates
```

## Tasks

### Task 1: Restore the quality baseline

- Acceptance: all frontend shell tests reflect the approved public versus
  authenticated navigation behavior; dynamic-dossier tests collect.
- Verify: `npm.cmd --prefix frontend run test`; `python -m pytest backend/app/tests/test_dossier_dynamic_schema.py backend/app/tests/test_dynamic_dossier_models.py`.
- Scope: S.

### Task 2: Complete dynamic dossier persistence as one vertical slice

- Acceptance: versioned dossier types, form data, evidence role/visibility, and
  reviewer/applicant feedback have models, migration, repository/service/API
  validation, server-side access enforcement, and tests.
- Verify: focused migration, service, API, authorization, and IDOR tests.
- Dependencies: Task 1. Scope: M, split by model/migration then service/API.

### Checkpoint A

- Backend and frontend focused suites are green; no schema or permission change
  occurs without approval.

### Task 3: Establish semantic THV design tokens

- Acceptance: the green/light/dark palette, Be Vietnam Pro, spacing, radii,
  focus, reduced motion, and central status mappings are authoritative tokens.
- Verify: token/theme tests, contrast review, `npm.cmd --prefix frontend run typecheck`.
- Dependencies: Task 1. Scope: M.

### Task 4: Migrate shells without changing authorization

- Acceptance: public remains public after sign-in; applicant and operations use
  separate responsive navigation; mobile bottom navigation respects safe areas.
- Verify: shell unit tests and real-browser checks at 360, 768, 1024, and 1440px.
- Dependencies: Task 3. Scope: M.

### Task 5: Migrate public experience vertically

- Acceptance: home, discovery/search, work detail, process, policy, and
  certificate verification use real APIs/release gates and public-safe copy.
- Verify: component/API/browser and accessibility tests.
- Dependencies: Task 4. Scope: split into page-sized S/M tasks.

### Task 6: Migrate applicant and operations workflows

- Acceptance: applicant dossier journey and invitation-only operations views
  preserve their existing permissions and show loading, empty, error, and
  permission states.
- Verify: workflow, permission, and responsive browser tests.
- Dependencies: Tasks 2 and 4. Scope: split by workflow.

### Checkpoint B

- Format, lint, typecheck, unit/API tests, E2E accessibility tests, and
  document-proof gate pass.

### Task 7: Production evidence review

- Acceptance: approved staging/production evidence covers DNS/TLS, environment
  configuration, Firebase, storage, Redis, Neon, blockchain signer/RPC,
  monitoring, backups, and rollback.
- Verify: runbooks and approved environment checks.
- Dependencies: Checkpoint B. Scope: operational; ask first before changes.

## Boundaries

- Always: preserve existing APIs, authorization, document access rules, and
  release gates; test each vertical slice.
- Ask first: schema migrations, dependencies, CI/CD changes, provider settings,
  deployment, chain/RPC/signer changes.
- Never: commit secrets, fake production API behavior, expose private evidence,
  or overwrite existing uncommitted work.

## Administration work program

Detailed evidence and gaps are recorded in
[`admin-dashboard-audit.md`](admin-dashboard-audit.md). This work extends the
existing remediation plan; it does not create a parallel planning system.

### Approval gate: administration role model

- [x] Retain `VIEWER`, `USER`, `MODERATOR`, and `SUPER_ADMIN`; express scoped
  operational responsibility through explicit permissions. No new operational
  role will be introduced.
- [ ] Approve analytics definitions for active user, activation, gross revenue,
  net collected, refund, and reconciliation mismatch.
- [ ] Approve schema changes before implementation.

### P0 Critical

- [x] Task P0-PAYOS: Complete the existing payOS payment lifecycle
  - Acceptance: authenticated applicants can resume/cancel unpaid orders;
    finance can reconcile provider state; webhook remains signature-verified,
    deduplicated and amount-checked; every mutation is audited.
  - Verify: gateway/service/API/UI tests plus mobile browser and production
    build gates documented in [`payos-payment-upgrade-spec.md`](payos-payment-upgrade-spec.md).
  - Dependencies: payOS merchant channel credentials and HTTPS callback URLs
    are deployment dependencies, not source-code defaults. Scope: M slices.

- [ ] Task A1: Freeze admin API and permission contracts
  - Acceptance: every route and sensitive command has a permission, audit
    payload, error contract, pagination/sort rules, and recent-auth requirement.
  - Verify: contract review and authorization-matrix tests are enumerated.
  - Dependencies: administration role-model approval. Scope: M.
  - Contract: [`admin-dashboard-spec.md`](admin-dashboard-spec.md).
  - P0 tasks: [`admin-dashboard-p0-plan.md`](admin-dashboard-p0-plan.md).
- [ ] Task A2: Deliver admin user read and suspension vertical slice
  - Acceptance: real server-paginated user list/detail and an audited,
    reason-required suspend/restore command; public users receive 403.
  - Verify: migration/query-plan tests if needed, API tests, frontend tests,
    browser permission/error/loading/empty checks.
  - Dependencies: A1. Scope: split into S/M increments.
- [ ] Task A3: Persist finance reconciliation cases
  - Acceptance: provider/DB comparisons produce idempotent `MATCHED`,
    `MISMATCH`, `NEEDS_REVIEW`, or `RESOLVED` records with resolution history.
  - Verify: duplicate webhook/order, amount mismatch, missing transaction, and
    permission tests.
  - Dependencies: A1 and approved finance definitions. Scope: M.
- [ ] Task A4: Preserve and extend audit evidence
  - Acceptance: all new sensitive commands capture actor, role snapshot, reason,
    before/after values, request ID, hashed IP, user agent, and integrity data;
    ordinary admins cannot mutate or delete logs.
  - Verify: append-only, integrity, retention, permission, and export tests.
  - Dependencies: A1. Scope: M.

### P1 Important

- [ ] Task A5: Add dossier/review administration read models and actions.
- [ ] Task A6: Add finance summary, transaction list/detail, and CSV export job.
- [ ] Task A7: Add blockchain transaction/health and safe retry read models.
- [ ] Task A8: Add provider-backed storage metrics and cleanup observability.
- [ ] Task A9: Add normalized security events and admin notifications.
- [ ] Task A10: Add aggregated admin system health snapshots.
- [ ] Task A11: Add audited, versioned non-secret business settings.
- [ ] Task A12: Build the responsive admin shell and reusable server-driven
  table/chart states against completed APIs only.

Each P1 task must be expanded into an S/M vertical slice with explicit files,
acceptance criteria, focused tests, and a checkpoint before implementation.

### P2 Enhancement

- [ ] Task A13: Add 30-120 second caching for measured aggregate bottlenecks.
- [ ] Task A14: Add saved views, column preferences, and richer comparisons.
- [ ] Task A15: Add XLSX and scheduled reports only if operations requires them.
- [ ] Task A16: Add compact mobile representations for complex admin tables.

### Administration checkpoints

- Checkpoint Admin 0: role model, definitions, contracts, and schema approved.
- Checkpoint Admin 1: P0 backend authorization/audit tests and query plans pass.
- Checkpoint Admin 2: each P1 vertical slice passes focused backend/frontend and
  real-browser checks before the next slice starts.
- Checkpoint Admin 3: full test, lint, typecheck, build, migration, security, and
  deployment-readiness gates pass with no mock production metrics.

## Type-specific review rubric

- [x] P0: Validate versioned specialist rubric definitions inside the existing
  dossier-type schema and freeze them in submission snapshots.
- [x] P0: Persist gate answers, specialist criterion answers, rubric version,
  and weighted specialist score through migration `0066`.
- [x] P0: Enforce locked evidence references, complete criteria, approval
  thresholds, and mandatory gates on the server while preserving legacy 5T
  reviews.
- [x] P1: Render the specialist rubric before 5T in the reviewer workspace with
  mobile-first controls, evidence selection, progress, and decision guidance.
- [x] P1: Seed version `2026.1` rubrics for all 12 default dossier types.
- [ ] P2: Add an admin rubric-version editor with preview and activation.
- [ ] P2: Add reviewer calibration and inter-reviewer variance reporting.

Contract: [`type-specific-review-rubric-spec.md`](type-specific-review-rubric-spec.md).
