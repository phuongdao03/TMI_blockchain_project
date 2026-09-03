# Implementation Plan: THVProofRegistry-only runtime

## Architecture decisions

- Consolidate wallet linking and proof signing around
  `THVProofRegistryGateway`; do not disguise the THV address as a legacy address.
- Preserve historical database rows and identify protocol explicitly where
  needed; disable legacy dispatch rather than rewriting history.
- Keep the existing proof-registry REST contract as the sole signing contract and
  remove/deprecate old signing endpoints after consumers move.
- Use read-only chain checks in tests/preflight; no Mainnet broadcast is part of
  implementation or verification.

## Phase 1: Safety contract and configuration

- [ ] Add repository/config tests that fail while legacy production variables and
  runtime identifiers remain.
  - Acceptance: production accepts only Polygon/THV/human configuration.
  - Verify: focused config and repository structure tests.
- [ ] Make THV gateway the wallet-link dependency and only blockchain gateway.
  - Acceptance: wallet endpoint boots without `CERTIFICATE_CONTRACT_ADDRESS` and
    checks `VERIFIER_ROLE`.
  - Verify: gateway, wallet service and API tests.
- [ ] Remove legacy config/dependency construction and provide safe 503 mapping.
  - Acceptance: invalid THV config never becomes an unhandled 500.
  - Verify: dependency/API error tests.

## Phase 2: Durable transaction migration

- [ ] Add a reversible protocol discriminator/backfill only if required by the
  existing model semantics.
  - Acceptance: old rows remain unchanged in status/data; new rows are THV-only.
  - Verify: upgrade/downgrade migration test.
- [ ] Route certificate approval/version/correction to `recordProof` versioning.
  - Acceptance: no new issue/update/revoke transaction is created.
  - Verify: focused certificate and proof service integration tests.
- [ ] Retire legacy worker dispatch while preserving historical observation.
  - Acceptance: workers reconcile THV states only and never broadcast.
  - Verify: worker retry/idempotency/status tests.

## Phase 3: Transaction verification hardening

- [ ] Validate exact calldata, chain, recipient, sender and zero value at
  submission.
- [ ] Decode and compare every `ProofRecorded` field before confirmation.
- [ ] Cover confirmation depth, pending, failed, replaced, dropped, timeout and
  retry state transitions.
  - Acceptance: a transaction hash alone can never produce `CONFIRMED`.
  - Verify: gateway/service/API tests with adversarial cases.

## Phase 4: Frontend signing slice

- [ ] Remove legacy client/mock requests and use proof-registry APIs exclusively.
- [ ] Add explicit MetaMask error/status states and safe polling.
- [ ] Keep signing visible and accessible on desktop/mobile navigation.
  - Acceptance: correct chain/wallet signs through MetaMask and all failure states
    are actionable without private-key handling.
  - Verify: component tests and desktop/mobile Playwright journeys.

## Phase 5: Contracts, infrastructure and CI

- [ ] Archive/deprecate legacy contract source, deploy/export/smoke paths and
  tests; exclude them from active runtime and production images while retaining
  rollback evidence.
- [ ] Replace preflight with THV chain/address/bytecode/ABI/role read checks.
- [ ] Update Docker/Compose/env templates and GitHub Actions for THV-only runtime.
  - Acceptance: images contain the THV ABI; production env reaches backend and
    workers; no secret is logged.
  - Verify: repository gates, image build, config and preflight tests.

## Phase 6: Documentation, full verification and review

- [ ] Update README, architecture/security/onboarding/rotation/release runbooks.
- [ ] Add `docs/handoffs/thv-proof-registry-only.md` with changed files, removed
  references, API flow, verification logic, env, test evidence and residual risk.
- [ ] Run format, lint, typecheck, unit/integration, Foundry and E2E suites.
- [ ] Perform a final security/code review and read-only Mainnet evidence check.
  - Acceptance: every success criterion in the migration spec is evidenced.

## Checkpoints

1. After Phase 1: production can load wallet/signing UI with THV-only config.
2. After Phase 3: backend lifecycle is safe under adversarial receipt/event data.
3. After Phase 5: CI image and production preflight use no legacy runtime input.
4. After Phase 6: all required commands pass and rollback is documented.

## Principal risks

| Risk | Mitigation |
| --- | --- |
| Historical rows accidentally reprocessed | Protocol discriminator and fail-closed dispatch |
| False confirmation from unrelated event | Decode and compare event asset/hash/version/signer |
| Mainnet side effect during testing | Mock/local read tests only; no broadcast commands |
| Contract role holder mismatch | Read-only preflight and explicit release blocker |
| Large removal breaks certificates/public verification | Vertical slices plus focused regression tests before deletion |
| Production secret leakage | Masked checks, no RPC/private-key logging, secret scan |
