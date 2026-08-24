# Blockchain production readiness

Status: architecture and controls are ready for controlled deployment; Polygon mainnet has **not** been deployed, funded, role-granted or transacted by this project.

## Environment configuration

```dotenv
BLOCKCHAIN_SIGNING_ENABLED=true
BLOCKCHAIN_SIGNER_MODE=human
BLOCKCHAIN_NETWORK=local            # staging: amoy; production: polygon
BLOCKCHAIN_CHAIN_ID=31337           # Amoy: 80002; Polygon: 137
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
CERTIFICATE_CONTRACT_ADDRESS=        # deployed address for that environment
BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES= # same address; required outside local
BLOCKCHAIN_EXPLORER_BASE_URL=
BLOCKCHAIN_REQUIRED_CONFIRMATIONS=1  # set the approved production value before launch
BLOCKCHAIN_WALLET_CHALLENGE_TTL_SECONDS=600
BLOCKCHAIN_TRANSACTION_INTENT_TTL_SECONDS=600
```

`BLOCKCHAIN_SIGNER_PRIVATE_KEY` must be blank in production. Production configuration rejects non-human signer mode and raw signer keys. `BLOCKCHAIN_SIGNING_ENABLED=false` is the emergency off switch for intent creation; it does not affect login, review or public content. The active signer must also link the same wallet in THV and that address alone receives `ISSUER_ROLE` on the registry.

## Required gates

- Local: run Anvil, deploy the audited test registry, grant its `ISSUER_ROLE` to a disposable MetaMask account, perform the full human-signing E2E and verify the record through THV.
- Amoy: use a different signer wallet and test POL, set chain 80002, validate wallet popup, receipt/read-back and the environment-specific explorer link.
- Before mainnet: approved contract audit, verified bytecode and ABI, governance/multisig procedure, least-privilege signer grant, signer rotation drill, RPC provider/SLA, monitoring, backups, incident/rollback runbook and explicit change approval.

## Explicit non-actions

This repository does not create or fund a production wallet, deploy to Polygon mainnet, grant a production role, or send a mainnet transaction. Those actions require the governance wallet holder and a separately approved release change.
