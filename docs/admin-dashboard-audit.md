# Admin Dashboard Production Audit

## Scope and assumptions

This Phase 1 audit covers the repository state, not deployed infrastructure or
live production data. The supplied admin-dashboard brief is the product
requirement. No UI, schema, API, provider, or authorization behavior is changed
by this audit.

Assumptions requiring confirmation before implementation:

1. Existing public, applicant, moderator, payment, review, certificate, and
   blockchain flows must retain their current contracts and status semantics.
2. New administration capability will be delivered as permission-based vertical
   slices under `/api/v1/admin/*`, reusing current modules and tables.
3. The four-role product model is approved and remains authoritative. Schema
   migrations, new dependencies, and payment-provider mutations still require
   explicit approval.
4. Metrics initially derive from PostgreSQL; short Redis caching is introduced
   only after query correctness and invalidation behavior are proven.

## Executive finding

The repository does not contain a demo-only admin area. It already has a useful
production foundation: normalized permissions, server-side policy checks,
staff invitations, two-person privileged actions, session revocation, MFA
recovery controls, append-only integrity-protected audit records, payment
webhook deduplication/reconciliation, idempotent durable jobs, reviewer queues,
blockchain signing controls, and operational metrics.

The requested dashboard is nevertheless incomplete. The current admin UI is a
Super Admin operations view, not a complete administration product. Missing
areas are user administration, user analytics, finance reporting, explicit
reconciliation cases, storage monitoring, security-event aggregation, role and
permission management, settings, notifications, broad reporting, and a unified
server-paginated data-table contract.

## Existing implementation

### Admin frontend

- `/admin/dashboard` renders real operational data from
  `/api/v1/admin/operations/metrics`.
- Existing workspaces cover staff accounts/invitations, audit history and CSV
  export, durable jobs, reports, content, search analytics, similarity cases,
  voting, and certificate-update operations.
- The dashboard navigation is role-derived and the backend independently
  authorizes protected operations.
- Current overview metrics are dossier funnel, overdue reviews, reviewer
  workload, payment failures, blockchain failures, cache telemetry, and durable
  job state. User growth, DAU/WAU/MAU, revenue, service latency, and storage
  metrics are absent.
- There is no reusable general-purpose `AdminDataTable`; existing workspaces use
  feature-specific tables and pagination patterns.

### Users and authentication

- `users` stores email, status (`PENDING`, `ACTIVE`, `SUSPENDED`, `DELETED`),
  verification time, last login, disable/delete time, and account type.
- `auth_identities` records Firebase/Google identity subjects and provider last
  login; `auth_sessions` supports expiry, rotation, revocation, device and MFA
  timestamps.
- Profiles store full name, encrypted phone, avatar, locale, and timezone.
- Firebase token/session handling loads roles and normalized permissions into a
  server-owned principal. `AuthorizationPolicy` checks permissions server-side;
  frontend gates are not the authorization boundary.
- The public users API only supports `/users/me`. There is no admin user list,
  user detail, status-action, session-history, internal-note, risk-status, or
  force-logout-all API.
- No durable activity fact defines last activity, DAU, WAU, MAU, or activation.
  These metrics cannot be implemented correctly until event definitions and
  source tables are approved.

### RBAC and staff

- Tables already exist for `roles`, `permissions`, `role_permissions`, and
  `user_roles`; a user can have multiple roles.
- Permission codes use the requested `resource.action` style and policy checks
  default to denial when neither permission, compatibility role, nor permitted
  Super Admin bypass applies.
- Staff invitation, disable, role-change, and session revocation
  flows exist. Privileged role/MFA actions can require a distinct approver and
  carry a reason, status, expiry, and audit evidence.
- A major product conflict exists: migration `0058` intentionally consolidated
  legacy operational roles into `VIEWER`, `USER`, `MODERATOR`, and
  `SUPER_ADMIN`; migration `0061` restricts `MODERATOR` to review capabilities.
  The requested nine operational roles would reverse that approved model.
- There are no admin role/permission CRUD APIs or pages. Direct permission
  overrides per user are not modeled.
- Production Super Admin bootstrap is explicit and controlled; it does not
  promote every existing administrator.

### Dossiers and review

- Dossiers are the repository's existing submission aggregate and already have
  owner/status/time indexes, immutable status history, versioned dossier data,
  evidence visibility, payment state, certificate state, and blockchain links.
- Current statuses are richer than the requested generic submission enum.
  Replacing them would break existing workflow semantics; admin presentation
  should map/group them without rewriting the domain state machine.
- Review assignments store reviewer, status, due time, conflict state, findings,
  and indexed active queues. Similarity cases have separate assignment and
  resolution history.
- Existing APIs cover applicant submissions, review assignment/work, findings,
  completion, similarity cases, and timeline/version reads. A unified admin
  cross-owner dossier search/detail contract is missing.
- Historical decisions are represented through dedicated records and workflow
  history rather than overwriting the dossier alone.

### Payments and finance

- `payment_orders` provides unique order and idempotency keys, provider
  reference uniqueness, amounts in minor units, currency, state, paid/expiry
  timestamps, and dossier linkage.
- `payment_events` deduplicates provider events and stores signature validity,
  redacted payload, received time, and processed time.
- Webhooks validate signatures and reject amount/currency/order mismatches.
  Pending reconciliation queries the provider, uses row locking, updates
  workflow state idempotently, and writes audit records.
- PayOS is implemented as a gateway adapter, but production readiness remains
  configuration/merchant dependent.
- Missing: admin transaction list/detail, finance aggregates, refund records and
  workflow, fees/net collected fields, reconciliation-case persistence, mismatch
  resolution history, and finance export jobs. Current failure counts are not a
  finance dashboard.

### Blockchain and background jobs

- Blockchain transactions have status/time indexes, attempt/error fields,
  receipt provenance, network/chain/contract/hash data, and document evidence.
- Human signing is protected by wallet-link challenges and transaction intents;
  private keys are not part of the production human-signing path.
- Durable jobs enforce unique `(task_name, idempotency_key)`, versioned replay,
  retry attempts, dead-letter state, and audited replay/cancellation.
- Existing APIs expose queue/signing/verification operations, but not the full
  requested admin network-health summary, balance/current-block metrics, or a
  unified transaction explorer.

### Storage and media

- The active media model is Cloudinary-oriented, not Cloudflare R2-oriented.
  It records object identity/version, byte size, MIME/type, owner, inspection,
  hash, confidentiality, encryption, and soft deletion.
- Private media encryption and access controls exist. Credentials and permanent
  signed URLs are not exposed in model responses by design.
- Missing: upload-session/multipart model, abandoned-upload cleanup state,
  orphan-object inventory, aggregate storage metrics, provider health/usage,
  and an admin storage API/page. R2-specific UI must not be claimed unless R2 is
  actually selected and instrumented.

### Audit, security, health, and observability

- `audit_logs` contains actor, action, resource, before/after values, request ID,
  hashed IP, user agent, retention, and integrity metadata. Indexes cover actor,
  action, resource, and time. CSV export and integrity verification exist.
- Audit records are append-only in application behavior and have a documented
  integrity/retention runbook. The schema does not have a standalone `reason`
  or actor-role snapshot column; callers currently place contextual values in
  before/after payloads.
- Request IDs, structured middleware logging, duration/status reporting, CSRF
  enforcement for state changes, and rate limiting are present foundations.
- `/health` and `/ready` expose backend and dependency up/down state. They do not
  provide an admin-only aggregate with latency, error rate, last check, or the
  requested service taxonomy.
- There is no normalized security-event table/stream for suspicious login,
  permission denial, invalid token, CSRF, webhook validation, or unusual admin
  behavior. Audit logs alone are insufficient for efficient security analytics.

## Database and performance gaps

Existing indexes are strong for core workflow queues, including dossier owner
and status, review reviewer/status/due time, payment dossier/status and provider
reference, blockchain status/time, audit actor/action/resource/time, and job
status/schedule.

Before admin list/analytics endpoints, query plans must validate or add:

- users: `created_at`, `status + created_at`, verified time, last login, and
  provider/user lookup paths;
- dossiers: global `status + created_at` and admin search fields;
- payments: `status + created_at`, `order_code`, and an owner path through the
  dossier join (or a deliberately denormalized payer ID);
- review SLA and aggregate date queries;
- audit composite filters used by export;
- security-event and reconciliation-case indexes once those schemas exist.

Admin APIs must use bounded server pagination, explicit sort allowlists,
aggregate queries, and query-plan regression tests. No endpoint should return an
unbounded table for client-side filtering.

## Security gaps and technical debt

### P0

- Preserve the approved four-role model and implement scoped operational access
  with explicit user-level permissions. Silent role expansion remains
  prohibited.
- Define admin-user actions and enforce permissions, reason, recent auth where
  required, session revocation, audit before/after values, and optimistic or
  idempotent mutation semantics.
- Define authoritative analytics facts. `last_login_at` is not user activity and
  payment totals cannot be inferred safely without refund/fee definitions.
- Introduce persisted reconciliation cases before presenting mismatch states as
  production-operable records.
- Preserve audit append-only behavior and add first-class reason/actor-role
  snapshots only through a reviewed migration and retention-compatible design.

### P1

- Add server-paginated user, dossier, transaction, blockchain, audit, and staff
  list contracts under `/api/v1/admin/*`.
- Add normalized security events, admin notification records, safe business
  settings with versioning/audit, and aggregated health snapshots.
- Add storage-provider instrumentation and orphan/upload lifecycle jobs matching
  the provider actually deployed.
- Move large exports to durable background jobs with authorization and audit.

### P2

- Add short-lived cache for proven aggregate queries, saved filters/column
  preferences, XLSX exports if required, richer trend comparisons, and mobile
  compact table views.

## Recommended architecture

Keep existing bounded contexts. Add an `admin` application layer that composes
read models from `auth/users`, `dossiers/reviews`, `payments`, `blockchain`,
`media`, `audit`, and `operations`; do not duplicate their write logic. Sensitive
commands delegate to existing domain services after a named permission policy.

Use contract-first vertical slices:

1. permission catalog and admin route shell;
2. user read/list plus one audited status command;
3. dossier/review operations;
4. finance transactions and persisted reconciliation;
5. blockchain/storage/system read models;
6. security events, reports, settings, and notifications.

Each slice includes schema only when needed, API contract, repository aggregate,
backend authorization tests, frontend states, browser verification, and
documentation. Incomplete modules remain disabled and labeled unavailable; they
must not return mock production data.

## Phase 1 changed files and verification

- Added: `docs/admin-dashboard-audit.md`.
- Updated: `docs/thv-master-remediation-plan.md` with the administration work
  program and approval gate.
- Migrations: none.
- APIs: none.
- Tests: not run; documentation-only audit with no behavior change.
- Next gate: approve the role strategy and Phase 2 plan before implementation.
