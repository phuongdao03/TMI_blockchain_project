# Spec: THV human blockchain signing

## Objective

Replace the current server-controlled blockchain broadcast path with a human-controlled signing path. A dossier continues through THV's internal review and payment workflow without a wallet. Once its immutable certificate proof is prepared, exactly one active, verified signer wallet may broadcast the contract call from MetaMask or another EIP-1193-compatible wallet. THV verifies the resulting on-chain transaction independently before it marks the blockchain proof confirmed.

The signer is a THV account with the `blockchain.sign` permission and a linked wallet. The wallet is an additional signing identity, never an authentication substitute. The signer owns the private key; THV never stores, requests, or receives a private key, seed phrase, or mnemonic.

## Current-state compatibility

The existing operational status model remains compatible:

| Existing state | Human-signing meaning |
| --- | --- |
| `APPROVED` | Internal approval completed. |
| `PAID` | Existing payment gate completed; certificate proof preparation is allowed. |
| `ANCHOR_PENDING` + transaction `CREATED` | Proof prepared and **waiting for blockchain signature**. |
| transaction `SIGNING` | A short-lived server-created signing intent exists. |
| transaction `BROADCAST` | Wallet broadcast verified by the server; confirmation is pending. |
| transaction `CONFIRMED` + dossier `ANCHORED` | Receipt, event, canonical block and contract read-back match; the proof is verified. |

`DossierStatus` remains internal business state; `BlockchainTransactionStatus` remains the separate blockchain lifecycle. This avoids a destructive rename of historical statuses while making the signer queue explicit.

## Architecture

```text
THV review / council / payment
  -> immutable DossierVersion + certificate metadata
  -> BlockchainTransaction(CREATED)
  -> signer queue
  -> transaction intent (exact calldata, contract, chain and expiry)
  -> MetaMask / EIP-1193 wallet signs and broadcasts
  -> submit transaction hash
  -> RPC verification + receipt/event/read-back + confirmations
  -> BlockchainTransaction(CONFIRMED), dossier ANCHORED
```

The contract's existing `ISSUER_ROLE` is retained as the signer permission. `DEFAULT_ADMIN_ROLE` and `PAUSER_ROLE` stay with the separately controlled governance wallet. There is no contract rewrite solely to rename `ISSUER_ROLE`.

### Data additions

- `blockchain_wallet_links`: verified public wallet links. Only one globally active link is allowed in V1; each link belongs to a THV user, chain, and audited lifecycle.
- `blockchain_wallet_challenges`: single-use, short-lived, hashed nonce challenges. The signature is verified but not stored.
- `blockchain_transaction_intents`: expiring, server-generated authorizations bound to one transaction, frozen dossier version, expected wallet, exact calldata hash, configured chain, and configured contract.
- `blockchain_transactions`: additive signer identity fields (`signer_user_id`, `signer_wallet_address`) for the final signing audit trail.

No private key material is added to database records, logs, API payloads, or environment variables.

## API contract

All APIs are authenticated; mutations also require CSRF protection. The backend derives proof, contract address and calldata itself.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/blockchain/wallet-challenges` | Issue a one-time ownership message for a connected address. |
| `POST /api/v1/blockchain/wallet-links` | Recover and verify the message signature; activate the wallet link. |
| `GET /api/v1/blockchain/wallet` | Return the caller's safe wallet-link state. |
| `GET /api/v1/blockchain/signing-queue` | List waiting/pending/failed proof transactions for an authorized signer. |
| `GET /api/v1/blockchain/transactions/{id}/signing-context` | Read signer-safe dossier and proof details only. |
| `POST /api/v1/blockchain/transactions/{id}/intents` | Revalidate and prepare a short-lived unsigned wallet request. |
| `POST /api/v1/blockchain/transactions/{id}/submissions` | Accept `{ intentId, transactionHash }`, then independently validate it via RPC. |
| `GET /api/v1/blockchain/transactions/{id}/status` | Return the persisted reconciliation state. |

No endpoint accepts a client-selected proof hash, target contract, calldata, final status, or signer identity.

## Security rules

- `blockchain.sign` is required for every wallet and signing operation; `SUPER_ADMIN` remains a deliberate break-glass compatibility path but still needs the active linked wallet.
- Wallet addresses are checksum-normalized and compared by address value, never raw case-sensitive strings.
- A wallet challenge binds THV user, connected address, configured chain, random nonce, issued/expiry timestamps and application domain. A nonce can be consumed only once.
- An intent expires after 10 minutes, becomes invalid if its transaction is no longer `CREATED`/`SIGNING`, and only one active intent may exist per transaction.
- Preparation checks permission, active verified link, chain, on-chain `ISSUER_ROLE`, frozen version/proof integrity, allowed contract, expected method, idempotency and current business state.
- Submission checks RPC transaction existence, `from`, `to`, `chainId`, `value == 0`, and exact encoded input. The callback never sets `CONFIRMED`.
- Reconciliation requires successful receipt, expected event, configured confirmations, canonical block hash and contract state read-back before confirmation.
- RPC degradation must affect only signing/reconciliation endpoints, not login, review or public browsing.

## Configuration

`BLOCKCHAIN_SIGNER_MODE=human` is the production path. It deliberately has no signer private-key or managed-key fields. Local legacy auto-signing remains opt-in solely for regression tests; it cannot be selected in a production full release.

Required per active network: `BLOCKCHAIN_NETWORK`, `BLOCKCHAIN_CHAIN_ID`, `BLOCKCHAIN_RPC_URL`, `CERTIFICATE_CONTRACT_ADDRESS`, `BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES`, `BLOCKCHAIN_EXPLORER_BASE_URL`, `BLOCKCHAIN_REQUIRED_CONFIRMATIONS`, `BLOCKCHAIN_SIGNING_ENABLED`.

Networks: local Anvil (`31337`) is active, Polygon Amoy (`80002`) is staging-ready, Polygon PoS (`137`) is configuration-only. This work does not create/fund production wallets, deploy a mainnet contract, grant a production role, or send a mainnet transaction.

## Commands

```powershell
cd backend; python -m pytest app/tests/test_human_signing_service.py
cd backend; alembic upgrade head
cd frontend; npm.cmd test -- human-signing
cd frontend; npm.cmd run typecheck
cd frontend; npm.cmd run build
```

## Project structure

```text
backend/app/modules/blockchain/  gateway, services, schemas, models and repositories
backend/app/api/v1/              protected blockchain API
backend/alembic/versions/        additive schema migrations
frontend/src/app/(dashboard)/    signer route
frontend/src/components/         wallet + signing queue UI
frontend/src/lib/blockchain/     minimal EIP-1193 browser adapter
docs/                            operational onboarding, rotation and release guidance
```

## Code style

```python
AuthorizationPolicy.require_capability(
    principal,
    PolicyRequirement(permission="blockchain.sign"),
    BlockchainForbiddenError,
)
```

Validate requests at FastAPI/Pydantic boundaries. Keep service methods narrow and use server-owned data to construct contract calls. UI follows existing THV semantic tokens, Be Vietnam Pro, white-first surfaces, clear failure states and keyboard-accessible buttons.

## Testing strategy

- Unit: challenge signature recovery, address normalization, intent expiry, unauthorized/wrong-wallet/wrong-chain and exact-input validation.
- Integration: repository uniqueness/idempotency, callback verification and reconciliation read-back.
- Browser: non-signer denied, verified signer link flow, wrong wallet/network notices and wallet cancellation state.
- Local E2E: Anvil + EIP-1193 test wallet submits a real local transaction; backend observes its receipt and state. No mocked `CONFIRMED` result is accepted.

## Boundaries

- Always: validate authorization and RPC facts server-side; preserve immutable versions; test each incremental slice; maintain audit events.
- Ask first: deployment, funding wallets, external mainnet role grants, production secret changes and contract upgrades.
- Never: store wallet secrets; let frontend choose proof/contract/calldata; treat a hash as verified without receipt/read-back; deploy or transact on mainnet in this task.

## Success criteria

- A reviewer can complete all internal work without a wallet.
- One active linked signer wallet can prepare and broadcast an exact allowed transaction manually.
- Wrong account, wrong chain, role revocation, expired intent, duplicate click and fake/foreign hash are denied.
- The server stores signer identity separately from internal approver identity and marks a dossier anchored only after independent confirmation/read-back.
- Local Anvil supports the real signing path; Amoy is configured/documented; Polygon mainnet is not deployed.
