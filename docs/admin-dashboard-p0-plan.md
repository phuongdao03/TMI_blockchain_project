# Implementation Plan: Admin P0 Foundation

## Overview

Deliver the smallest safe administration foundation under the approved
four-role model: explicit staff permission grants, server-side effective
authorization, real paginated user reads, and audited user suspension/session
revocation. Work proceeds test-first in independently verifiable increments.

## Dependency graph

```text
Permission contract
  -> user permission migration/model
  -> effective principal permissions
  -> permission assignment service/API
  -> admin user read API
  -> audited suspension/session revocation API
  -> frontend users workspace
  -> browser/security verification
```

## Architecture decisions

- Preserve four roles; do not restore legacy operational roles.
- Add direct active user-permission grants. Role permissions remain unchanged.
- Derive staff status server-side; never accept it from Firebase/client claims.
- Keep admin reads in a thin admin module; delegate account/session mutations to
  auth domain services.
- Use offset pagination initially because it matches existing response envelopes;
  require deterministic `created_at, id` ordering. Revisit cursor pagination only
  after measured scale warrants it.
- Introduce no frontend chart/table dependency in P0.

## Tasks

### Task P0.1: Prove permission-assignment migration — completed

**Acceptance criteria:**

- `user_permissions` records user, permission, grantor, reason, optional expiry,
  created/updated timestamps and optimistic version.
- Foreign keys, uniqueness and lookup indexes are additive; no role assignments
  or Super Admin grants are created automatically.
- Upgrade and downgrade tests pass on the repository's migration harness.

**Verification:** focused migration test plus `python -m ruff check` on changed
Python files.

**Likely files:** one Alembic revision; one migration test. Scope: S.

### Task P0.2: Load effective permissions — completed

**Acceptance criteria:**

- Repository permission lookup returns role permissions union non-expired direct
  grants without duplicates.
- Revoked/expired grants do not authorize a subsequent request.
- Existing role-only authorization behavior remains unchanged.

**Verification:** first add failing repository/session/policy tests, then run the
focused authorization suite.

**Likely files:** auth model, repository, session service if needed, focused test.
Dependencies: P0.1. Scope: M.

### Task P0.3: Manage staff permission grants — completed

**Acceptance criteria:**

- Super Admin or a principal with `staff.permissions.assign` can read/replace an
  allowlisted target's direct permissions with reason and expected version.
- The flow rejects self-escalation, Super Admin assignment, unknown permissions,
  stale versions and grants outside the caller's assignable scope.
- Mutation is CSRF-protected, atomic and integrity-audited with before/after data.

**Verification:** RED API/service tests for normal user 403, scoped staff 403,
valid assignment, stale version, forbidden escalation and audit evidence.

**Likely files:** auth schemas/service, admin staff API or existing staff API,
router registration if necessary, focused tests. Dependencies: P0.2. Scope: M;
split schema/service from API if more than five files are required.

### Checkpoint P0-A

- Migration upgrade/downgrade and permission tests pass.
- Existing four-role authorization suite passes.
- Human reviews effective-permission and assignment behavior.

### Task P0.4: Add paginated admin user read model — completed

**Acceptance criteria:**

- `GET /api/v1/admin/users` and `/{id}` return real masked data with stable
  pagination, allowlisted sorting and validated filters.
- Queries avoid N+1 behavior and expose only fields permitted by `users.read`.
- Normal users receive 403; missing users return the standard 404 envelope.

**Verification:** RED repository/API tests for pagination boundaries, filters,
sort stability, masking, 403 and 404; inspect PostgreSQL query plans for primary
list paths before adding indexes.

**Likely files:** admin repository/service/schemas, API file, tests. Dependencies:
P0.2. Scope: split read repository/service and HTTP contract into two S/M tasks.

### Task P0.5: Add audited user status command — completed

**Acceptance criteria:**

- `PATCH /api/v1/admin/users/{id}/status` supports approved suspend/restore
  transitions with reason, expected current status and `users.suspend`.
- It forbids self-suspension, ordinary mutation of Super Admin, hard deletion and
  invalid transitions; suspension revokes active sessions atomically.
- Audit captures actor, target, reason, old/new status and request context.

**Verification:** RED service/API tests for every transition and forbidden case,
session revocation, concurrent conflict and audit integrity.

**Likely files:** existing auth account service/repository, admin API/schema,
tests. Dependencies: P0.4. Scope: M, split service and API if needed.

### Task P0.6: Build admin users workspace — completed

**Acceptance criteria:**

- `/admin/users` uses the real API with server search/filter/sort/pagination.
- Loading, empty, error, retry and permission-denied states are explicit.
- Suspend/restore requires confirmation and reason; controls render from
  effective permissions but never replace backend enforcement.

**Verification:** component tests, TypeScript, lint and browser checks at desktop,
tablet and mobile widths.

**Likely files:** route, workspace, API client/types, component tests. Dependencies:
P0.4 and P0.5. Scope: split read table and mutation dialog into two M tasks.

### Checkpoint P0-B — completed

- Focused backend and frontend suites pass.
- Normal user admin API/browser journey is denied.
- Scoped staff can read but cannot suspend without `users.suspend`.
- Suspension revokes sessions and produces verifiable audit evidence.
- Lint, typecheck and production frontend build pass.

### Task P0.7: Documentation and handoff — completed

**Acceptance criteria:** permission matrix, API docs, migration/deployment notes,
environment impact and rollback procedure reflect the shipped slice.

**Verification:** documentation links resolve and full repository gates pass.

**Likely files:** existing README/docs/runbooks plus one concise handoff. Scope: S.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Direct grants become ungoverned shadow roles | High | Allowlist, reason, version, expiry, assignment scope and audit every replacement |
| Permission revocation appears delayed | High | Load permissions from DB on every authenticated request; test next-request revocation |
| Admin user query leaks PII | High | Explicit response schemas, masking and field-level tests |
| Suspension races with active requests | Medium | Row lock/expected status, atomic session revocation and idempotent outcome |
| Existing dirty frontend work overlaps | Medium | Keep changes localized; inspect diff before each frontend increment |
| Offset pagination shifts during writes | Medium | Stable secondary ID sort and documented semantics; cursor migration remains compatible |

## Deferred from P0

User analytics, finance/reconciliation persistence, refund, dossier administration,
blockchain/storage/security dashboards, settings, notifications, bulk actions,
XLSX and reusable permission templates remain P1/P2. No placeholder production
metrics or mock pages will be created for them.

## Approval gate

Implementation starts only after this spec and task plan are approved. Database
migration P0.1 is the first behavioral increment and requires explicit schema
approval under repository boundaries.
