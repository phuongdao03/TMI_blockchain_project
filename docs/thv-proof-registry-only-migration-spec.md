# Spec: THVProofRegistry-only production runtime

## Objective

Migrate every new blockchain write and verification path to the already deployed
`THVProofRegistry` on Polygon PoS Mainnet (chain `137`) at
`0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F`. The application must use the
browser wallet holding `VERIFIER_ROLE`; it must never sign with an application
private key. Existing database rows and audit history remain immutable and
readable, but no new runtime path may create `CertificateRegistry` transactions.

Deployment transaction evidence:
`0x0d847b7281b67cc229986b0088a1ad59949fcfded6ccf331f2cd7deb6fa7d2e7`.

## Assumptions and decisions

1. The supplied Mainnet contract and transaction are immutable release inputs;
   this migration will not deploy, upgrade, grant roles, or send Mainnet calls.
2. Read-only Polygon RPC and explorer checks are permitted and must not expose
   provider credentials in logs.
3. Historical `blockchain_transactions` rows may continue to contain legacy
   method and contract values. Runtime dispatch will not process them as new
   CertificateRegistry work or silently mark them confirmed.
4. Corrections and revocations remain off-chain business state plus a new,
   monotonically increasing proof version. `THVProofRegistry` records are never
   deleted or overwritten.
5. The existing proof-registry API contract becomes the only signing API. Legacy
   `/api/v1/blockchain/*` signing endpoints are removed or return an explicit
   deprecation response, except the wallet-link API after it is rewired to the
   THV gateway.
6. Contract source, deployment tooling, tests, and historical documentation for
   CertificateRegistry are retained as explicitly archived/deprecated rollback
   references, but excluded from runtime wiring, active APIs and production
   builds. Database history is preserved through a reversible migration rather
   than destructive cleanup.

## Architecture and API contract

The sole gateway is `THVProofRegistryGateway`, configured by
`THV_PROOF_REGISTRY_CONTRACT_ADDRESS` and
`THV_PROOF_REGISTRY_CONTRACT_ABI_PATH`. It supports only:

- `recordProof(bytes32 assetId, bytes32 proofHash, uint64 version)`
- `getProof(bytes32 assetId, uint64 version)`
- `verifyProof(bytes32 assetId, uint64 version, bytes32 expectedHash)`
- read-only AccessControl lookup for `VERIFIER_ROLE`
- read-only transaction, receipt, block and balance queries required to verify
  human-signed transactions

Primary authenticated endpoints:

- `GET /api/v1/blockchain/proof-registry/signing-queue`
- `POST /api/v1/blockchain/proof-registry/dossiers/{id}/versions/{version}/intents`
- `POST /api/v1/blockchain/proof-registry/transactions/{id}/submissions`
- `GET /api/v1/blockchain/proof-registry/transactions/{id}/status`
- `GET /api/v1/blockchain/proof-registry/proofs/{assetId}/versions/{version}`
- `GET /api/v1/blockchain/proof-registry/proofs/{assetId}/versions/{version}/verify`

Wallet challenge/link/revoke operations remain under `/api/v1/blockchain/wallet*`
for compatibility, but must use THV chain/address/`VERIFIER_ROLE` only and must
not instantiate the legacy gateway.

## Transaction lifecycle and invariants

1. Only a server-authenticated principal with `blockchain.sign`, an active wallet
   link, and the exact connected wallet may request an intent.
2. The gateway validates Polygon chain `137`, the exact configured contract, ABI,
   deployed bytecode, `VERIFIER_ROLE`, proof version, asset/proof hashes, dossier
   approval state, gas estimate and balance.
3. An intent freezes `assetId`, `proofHash`, `version`, encoded calldata,
   `chainId`, contract, signer, payload hash and expiry. One open intent is allowed
   per transaction; retries are idempotent and nonce-sensitive operations retain
   their lock.
4. MetaMask sends the transaction. Frontend returns only the public transaction
   hash; no private key enters frontend, backend, image, environment template or
   log.
5. Submission never means confirmation. Backend verifies transaction sender,
   recipient, chain, zero value and exact calldata before recording `BROADCAST`.
6. `CONFIRMED` requires a successful receipt from the configured contract, an
   exact `ProofRecorded` event matching asset, proof hash, version and signer,
   successful `getProof`/`verifyProof`, and at least
   `BLOCKCHAIN_REQUIRED_CONFIRMATIONS` blocks.
7. Missing/dropped/replaced/failed/timed-out transactions remain explicit and
   retryable according to durable status; no background task may reinterpret
   historical CertificateRegistry rows as THV transactions.

## Data migration

- Preserve existing tables, transaction hashes, statuses, audit rows and foreign
  keys.
- Add an explicit registry/protocol discriminator only if existing immutable
  contract/method fields cannot safely distinguish legacy and THV rows.
- Backfill legacy rows deterministically without changing their business status.
- Default all new rows to THV proof-registry protocol.
- Provide an Alembic downgrade that reverses schema/backfill metadata only; it
  never deletes historical transaction data.

## Frontend behavior

- `/blockchain` calls only the proof-registry signing APIs plus THV wallet-link
  endpoints.
- Before `eth_sendTransaction`, require chain `137`, expected contract and linked
  wallet. Offer a keyboard-accessible switch-network action.
- Distinguish wrong chain, wrong wallet, user rejection, insufficient funds/gas,
  pending confirmation, dropped/replaced, failed and confirmed states.
- Poll status without claiming success after hash submission.
- Keep signing reachable in primary mobile navigation and make all actions usable
  by keyboard and assistive technology.

## Production runtime

Required non-secret values:

```dotenv
APP_ENV=production
RELEASE_MODE=full
BLOCKCHAIN_NETWORK=polygon
BLOCKCHAIN_CHAIN_ID=137
BLOCKCHAIN_RPC_URL=https://<approved-polygon-rpc>
THV_PROOF_REGISTRY_CONTRACT_ADDRESS=0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F
BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES=0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F
THV_PROOF_REGISTRY_CONTRACT_ABI_PATH=/contracts/artifacts/THVProofRegistry.abi.json
BLOCKCHAIN_SIGNER_MODE=human
BLOCKCHAIN_SIGNING_ENABLED=true
BLOCKCHAIN_SIGNER_PRIVATE_KEY=
BLOCKCHAIN_REQUIRED_CONFIRMATIONS=3
BLOCKCHAIN_TRANSACTION_INTENT_TTL_SECONDS=300
BLOCKCHAIN_EXPLORER_BASE_URL=https://polygonscan.com
```

`CERTIFICATE_CONTRACT_ADDRESS` and `BLOCKCHAIN_CONTRACT_ABI_PATH` are not runtime
inputs after migration. Production validation rejects non-human signing, private
keys, any non-Polygon chain, a different contract, an allowlist containing a
different address, or a missing/unreadable THV ABI.

## Audit inventory baseline

Legacy dependencies currently exist in these active areas:

- Backend config/dependencies/gateway/services/workers and certificate/public
  verification wiring.
- Blockchain, certificate issuance/version, runtime config, gateway and human
  signing tests.
- Production/staging/local environment templates, Compose bootstrap, blockchain
  preflight and document-proof gate.
- Archived contract source, deployment/export/release/smoke scripts and Foundry
  tests that must be excluded from active production paths.
- GitHub contract release workflow.
- Frontend E2E mock server and legacy client mock expectations.
- Blockchain architecture, security, signer, runtime and release documentation.

The implementation audit must reach zero active runtime occurrences of:
`CertificateRegistry`, `ISSUER_ROLE`, `issueCertificate`, `updateCertificate`,
`revokeCertificate`, `CERTIFICATE_CONTRACT_ADDRESS`, and
`BLOCKCHAIN_CONTRACT_ABI_PATH`. Archived source/tests and historical migration
descriptions may retain legacy identifiers only when clearly marked deprecated
and excluded from runtime, active API and production build scans.

## Commands and testing strategy

```text
Format: npm run format:check
Lint: npm run lint
Types: npm run typecheck
Unit/integration: npm test
Browser E2E: npm --prefix frontend run test:e2e
Contract: forge test (from contracts/)
```

Focused tests cover gateway construction, calldata, event fields, confirmations,
idempotency/expiry/retry, wrong chain/contract/signer, API integration, frontend
wallet errors, desktop/mobile signing, production configuration and a repository
scan proving legacy runtime identifiers are gone.

## Boundaries

- Always: preserve data/audit history; validate server-side; use exact checksummed
  Mainnet address; keep signing human-controlled; keep changes reversible.
- Ask first: any irreversible schema operation, new dependency, on-chain write,
  role change, or deployment.
- Never: deploy/redeploy Mainnet, broadcast a transaction, store a private key,
  use an Anvil address in production, alias THVProofRegistry as
  `CERTIFICATE_CONTRACT_ADDRESS`, or print RPC credentials.

## Success criteria

- New runtime code has one THV gateway and one proof-record transaction path.
- Production boots without CertificateRegistry variables and health/preflight
  verifies chain, bytecode, ABI and read-only role holders.
- Existing rows are preserved; new rows are unambiguously THV proof records.
- Desktop/mobile MetaMask signing completes only after verified receipt, exact
  event data and three confirmations.
- All required quality commands pass and CI builds/deploys the same configuration.
- README, release runbook and handoff record the supplied contract, deployment
  transaction, governance/verifier holders and rollback procedure.
