# Spec: Production Administration Platform

## Objective

Extend the existing THV operations area into a production administration
platform backed exclusively by real backend data. Preserve the four product
roles (`VIEWER`, `USER`, `MODERATOR`, `SUPER_ADMIN`) and delegate operational
responsibilities through explicit permissions enforced by the backend.

Success means operators can perform only their assigned work, sensitive actions
are reasoned and auditable, large collections are server-paginated, and no
unfinished provider integration is represented as production-ready.

## Approved authorization model

### Roles

- `VIEWER`: public/read-only participant baseline.
- `USER`: applicant/product-user baseline.
- `MODERATOR`: reviewer baseline; retains only review permissions.
- `SUPER_ADMIN`: emergency/platform authority; limited membership and explicit
  bootstrap. Ordinary staff cannot grant or receive this role through standard
  administration flows.

### Fine-grained staff permissions

Non-Super-Admin staff keep `USER` or `MODERATOR` and receive explicit user-level
permission grants. This avoids giving finance/support/technical staff unrelated
review powers and avoids recreating operational roles under different names.

Add a normalized `user_permissions` assignment with user, permission, grant
metadata, reason, grantor, timestamps, and optional expiry. P0 supports explicit
grants only; denial overrides and reusable permission templates are deferred
until a demonstrated need. Removing a grant immediately removes the effective
permission on the next authenticated request because permissions are loaded
from the database, not trusted from client claims.

Effective permissions are:

```text
role_permissions UNION active user_permissions
```

`SUPER_ADMIN` remains an explicit policy bypass only where the policy permits
it. High-risk two-person actions keep their distinct-approver rules.

Staff status is server-derived from `SUPER_ADMIN`, `MODERATOR`, or at least one
active administrative permission. A `USER` with no administrative permission is
not staff. Invitations must carry a safe base role plus an explicit permission
set; acceptance assigns both atomically.

Initial permission namespaces:

```text
dashboard.read
users.read users.update users.suspend users.sessions.revoke
staff.read staff.invite staff.update staff.permissions.assign
submissions.read submissions.review submissions.approve submissions.reject
payments.read payments.reconcile payments.refund payments.export
blockchain.read blockchain.retry
storage.read storage.delete
audit.read
security.read security.manage
system.read system.manage
reports.read reports.export
settings.read settings.manage
```

Existing permission codes remain valid and are migrated/aliased only through an
explicit compatibility plan. Frontend navigation uses effective permissions for
presentation; every API repeats authorization server-side.

## Tech stack

- Backend: Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis,
  Celery.
- Frontend: Next.js 16, React 19, TypeScript, TanStack Query, Tailwind CSS.
- Authentication: Firebase identity plus server sessions, CSRF protection, MFA
  policy and database-loaded permissions.
- Testing: pytest, Vitest, Playwright, Ruff, mypy, ESLint and Next build.

## Commands

```powershell
# Focused backend tests (replace expression per slice)
python -m pytest backend/app/tests -k "admin or authorization"

# Frontend tests and verification
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build

# Backend verification
python -m ruff check backend
python -m ruff format backend --check
Push-Location backend; python -m mypy app; Pop-Location

# Full repository gate
npm.cmd test
npm.cmd run lint
npm.cmd run typecheck
```

## Project structure

```text
backend/app/api/v1/              Admin HTTP contracts under /api/v1/admin/*
backend/app/modules/admin/       Cross-domain admin read models/orchestration
backend/app/modules/auth/        Roles, permissions, staff, sessions
backend/app/modules/*/           Existing domain commands remain authoritative
backend/alembic/versions/        Reviewed additive migrations
backend/app/tests/               Policy, service, API and migration tests
frontend/src/app/(dashboard)/admin/  Admin routes
frontend/src/components/admin/  Admin workspaces and reusable presentation
frontend/src/lib/api/            Typed API client contracts
frontend/e2e/                    Critical permission and operator journeys
docs/                            Architecture, matrix, runbooks and handoffs
```

## API and code style

All list endpoints use bounded page/pageSize, allowlisted sorting and explicit
filters. Mutation payloads include a reason and concurrency/idempotency value
where replay is possible. Responses retain the repository's success envelope
and request ID.

```python
AuthorizationPolicy.require_capability(
    principal,
    PolicyRequirement(permission="users.suspend"),
    AdminUserForbiddenError,
)
```

Admin orchestration may query multiple modules for read models. It must delegate
writes to the existing domain service rather than duplicate state transitions.
Names use `resource.action`; secrets and raw tokens never enter schemas or logs.

## P0 API contract

```text
GET   /api/v1/admin/users
GET   /api/v1/admin/users/{userId}
PATCH /api/v1/admin/users/{userId}/status
POST  /api/v1/admin/users/{userId}/sessions/revocations

GET   /api/v1/admin/staff/{userId}/permissions
PUT   /api/v1/admin/staff/{userId}/permissions
```

The user list supports page, pageSize, search, status, provider, verified,
createdFrom/To, activityFrom/To, sortBy and sortOrder. Unsupported filters fail
validation rather than being ignored. Status changes require reason, expected
current status and CSRF; self-suspension and ordinary Super Admin mutation are
forbidden. Permission replacement requires `staff.permissions.assign`, reason,
expected version, a target permission allowlist, and cannot grant
`SUPER_ADMIN`.

## Analytics definitions

- Total users: accounts not physically deleted.
- New users: `users.created_at` within the selected half-open interval.
- Verified users: `email_verified_at IS NOT NULL`.
- Paying users: distinct dossier owners with at least one `PAID` order, revised
  when refund persistence exists.
- Gross collected: sum of `PAID` order amounts.
- Net collected and revenue: unavailable until refunds and provider fees are
  persisted; the UI must label them unavailable rather than infer values.
- Active user/DAU/WAU/MAU/activation: unavailable until an approved activity
  fact and qualifying-event definition are implemented.
- Pending submission: documented set of dossier workflow statuses, never a new
  replacement status stored beside the domain state machine.

## Testing strategy

- Unit tests: effective-permission calculation, sort/filter validation, status
  transitions, analytics interval definitions and masking.
- Integration/API tests: database queries, pagination stability, permission
  assignment, suspension/session revocation, audit creation and IDOR resistance.
- Migration tests: upgrade/downgrade shape, seed idempotency, no automatic
  Super Admin assignment, and expected indexes.
- Frontend tests: loading, empty, error, permission denied, filters, pagination,
  confirmation/reason forms and permission-derived navigation.
- Browser tests: public user receives 403, scoped staff sees only permitted
  modules, sensitive mutation is audited, desktop/tablet/mobile states work.
- Query-plan tests: admin list/aggregate paths remain indexed at readiness scale.

Every behavioral increment follows red-green-refactor. Existing tests, lint,
typecheck and build must remain green at each checkpoint.

## Boundaries

- Always: deny by default; authorize on the server; use real persisted data;
  paginate; validate filters; mask PII; write append-only audit evidence; reuse
  existing domain services; preserve request IDs and structured logging.
- Ask first: schema migrations, dependencies, CI/deployment changes, provider
  mutations, refund execution, secrets, blockchain signer/RPC/contract changes.
- Never: hard-code admin emails, trust frontend roles, expose credentials/private
  keys/tokens, hard-delete users through normal UI, invent production metrics,
  rewrite dossier/payment/blockchain state machines in the admin layer, or
  overwrite unrelated worktree changes.

## Success criteria

- Four roles remain authoritative and no operational role is added.
- Scoped staff can access only explicitly granted permissions; revoked grants
  cease on the next request.
- Normal users receive 403 from admin APIs; permission combinations match the
  documented matrix.
- Lists are server-paginated/filterable/sortable and backed by verified indexes.
- Sensitive actions require reason and create complete integrity-protected audit
  evidence with actor, before/after state and request context.
- Dashboard/finance/security/storage values are real or explicitly unavailable.
- Migrations, focused/full tests, lint, typecheck and build pass without breaking
  existing flows.

## Open decisions

- Exact activity events and activation window for DAU/WAU/MAU.
- Refund and provider-fee persistence needed for net revenue.
- Whether permission templates are needed after direct grants are operational.
- Storage provider and provider-level metrics available in production.

