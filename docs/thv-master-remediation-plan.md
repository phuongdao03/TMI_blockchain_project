# THV Master Remediation Plan

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
