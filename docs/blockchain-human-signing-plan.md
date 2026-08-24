# Implementation plan: THV human blockchain signing

## Decisions from the audit

- The existing contract already enforces `ISSUER_ROLE` and emits certificate/document events. It is retained.
- Existing `BlockchainTransaction` already provides idempotency, receipt tracking and the blockchain state machine. It is extended rather than duplicated.
- `DossierVersion.canonical_hash` and certificate metadata are already immutable proof inputs. The current payment gate is preserved.
- Current `BlockchainTransactionService` auto-broadcasts with a backend signer. Human mode disables that dispatcher path; reconciliation remains backend-owned.
- RBAC already supports normalized permissions. Add `blockchain.sign` to the existing `BLOCKCHAIN_ADMIN` role; the sole active verified wallet is the practical single-signer control. No broad new role is introduced.

## Phase 1 — foundation

### Task 1: Define human-signing entities and permission

- Acceptance: wallet links, hashed one-time challenges, expiring intent records and signer audit fields are additive; at most one active wallet exists.
- Verify: model/migration tests and `alembic upgrade head` locally.
- Dependencies: none.

### Task 2: Make human signing a first-class configuration mode

- Acceptance: `human` mode cannot auto-sign and is mandatory for a production full release; legacy modes remain explicit local-only compatibility paths.
- Verify: configuration tests reject production private/managed signing.
- Dependencies: Task 1.

## Checkpoint — foundation

- Existing blockchain regression suite remains green; no service can instantiate a private signer in human mode.

## Phase 2 — protected signer flow

### Task 3: Wallet ownership and signer authorization

- Acceptance: signed one-time message recovers only the requested wallet and creates/revokes an audited active link.
- Verify: test expiry, replay, incorrect signature, missing permission and second active wallet.
- Dependencies: Task 1.

### Task 4: Transaction intent and submission validation

- Acceptance: backend creates exact unsigned call, checks `ISSUER_ROLE`, and rejects arbitrary calldata/contracts, stale state, incorrect sender/chain/hash and double submission.
- Verify: service/API tests with a deterministic gateway fake.
- Dependencies: Tasks 1–3.

### Task 5: Reconciliation and proof lifecycle integration

- Acceptance: existing `CREATED -> SIGNING -> BROADCAST -> CONFIRMED` lifecycle works without server broadcast; receipt, event and read-back gate `ANCHORED`.
- Verify: transaction/reconciliation tests including reverted and canonical mismatch cases.
- Dependencies: Task 4.

## Checkpoint — backend

- Local migration succeeds, focused backend tests pass and legacy admin transaction APIs continue to work.

## Phase 3 — signer experience

### Task 6: EIP-1193 wallet adapter and API client

- Acceptance: browser detects/connects wallet, listens for account/chain changes and never asks for a secret.
- Verify: unit tests for hex/chain/error normalization.
- Dependencies: API contract Tasks 3–4.

### Task 7: Signer dashboard and signing detail

- Acceptance: only permitted users see the signing navigation; queue, wallet status, wrong-account/network state, intent expiry/cancel and submission progress are clear and accessible.
- Verify: component and Playwright tests at mobile/desktop/light/dark.
- Dependencies: Task 6.

## Phase 4 — operational readiness

### Task 8: Public verification, docs and handoff

- Acceptance: public presentation derives proof facts from persisted verified state; docs cover architecture, signer onboarding/rotation, security and release readiness.
- Verify: public API/UI tests and document review.
- Dependencies: Task 5.

### Task 9: Real local signing E2E and Amoy readiness

- Acceptance: deployed local contract and a local EIP-1193 signer submit a real Anvil transaction; Amoy config checklist is runnable without production actions.
- Verify: Anvil E2E script and no-mainnet guard test.
- Dependencies: Tasks 1–8.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Existing certificate worker assumes auto-sign | Disable enqueue only in explicit `human` mode; retain legacy mode for regression compatibility. |
| Wallet popup cannot run headlessly | Unit/browser tests mock EIP-1193 semantics; local E2E uses a real Anvil transaction and is separately documented for manual MetaMask confirmation. |
| RPC race after broadcast | Reject unknown hashes at callback and let durable reconciliation resume only recorded broadcasts. |
| Multiple staff obtain the permission | DB enforces exactly one active verified signer wallet; governance procedure controls rotation. |
| Historical statuses change | Keep existing business enum and derive waiting status from blockchain transaction state. |
