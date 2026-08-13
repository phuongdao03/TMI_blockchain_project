# Blockchain release

## Polygon Amoy staging

Copy `infrastructure/.env.staging.example` to an ignored environment file and
replace every placeholder. Never commit RPC credentials, private keys or
explorer API keys. Use separate deployer, contract administrator and issuer
addresses; fund only the deployer with enough Amoy test token for the release.

Export the variables into the current shell, then run:

```bash
bash infrastructure/scripts/deploy-contract-amoy.sh
```

The release fails before broadcast unless the RPC reports chain `80002`, the
private key resolves to `EXPECTED_DEPLOYER`, and the deployment script confirms
the administrator and issuer allowlists. After deployment it exports the
deterministic manifest, waits for Polygonscan source verification, and writes:

- `contracts/artifacts/releases/amoy/manifest.json`
- `contracts/artifacts/releases/amoy/explorer-evidence.json`
- `contracts/deployments/amoy.json`

Copy the verified address into both `CERTIFICATE_CONTRACT_ADDRESS` and
`BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES` in the staging secret store. Do not
enable the worker until the address and transaction hash match the two evidence
files and the explorer displays verified source code.

Run the staging issue/read/revoke/read smoke with a disposable certificate ID.
Retain the transaction links with the release evidence. On any chain, signer,
role, verification or smoke mismatch, stop the release; do not reuse a partially
qualified address.

## Polygon production dry run

Trigger `Contract production dry run` with the full commit that passed Amoy.
The `production-blockchain` environment must require an authorized reviewer.
The workflow checks out that immutable commit, runs the pinned build/tests and
executes only read-only Polygon calls. It verifies chain 137, HTTPS RPC, signer
balance, contract allowlist, runtime bytecode and administrator/pauser/issuer
roles before writing the dry-run artifact. It never broadcasts a transaction.

Before cutover, rehearse on Amoy with a disposable certificate: issue, verify,
revoke, verify revoked, pause, prove writes are rejected, then unpause. Record
the transaction links and alert timestamps. Stop the canary immediately for a
role mismatch, state mismatch, RPC instability or unexpected signer balance.

## Document evidence release check

The registry release must expose `anchorDocumentEvidence`,
`getDocumentEvidence` and `verifyDocumentEvidence`. Before enabling workers:

1. Confirm the deployed ABI/runtime match the qualified release manifest.
2. Grant `ISSUER_ROLE` only to the managed application signer.
3. Anchor a disposable document commitment on Amoy and retain the transaction.
4. Read it back and compare commitment, predecessor, version and timestamp.
5. Verify a matching commitment returns true and a modified commitment false.
6. Confirm the API transaction reaches `EVIDENCE_CONFIRMED` after the configured
   confirmations and reconciliation reports no chain-state mismatch.

Never place a filename, email, user UUID, storage locator, encryption metadata,
key material or document bytes in contract arguments. This feature requires a
new deployment and allowlist qualification; do not pair the new ABI with the
old certificate-only runtime.
