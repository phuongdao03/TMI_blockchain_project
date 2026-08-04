# Contracts

Solidity sources, Foundry configuration, deployment scripts, ABIs, and
deployment artifacts belong here. TASK-0801 initializes the contract project.

Contracts store only the hashes and public verification data approved by the
blockchain specification; secrets and personally identifiable information must
never be written on-chain.

## Development

Foundry `v1.7.1`, Solidity `0.8.30`, and OpenZeppelin Contracts `5.6.1` are
pinned. Install JavaScript dependencies with `npm ci`, then run:

```bash
forge fmt --check
forge build
forge test
```

## Deployment

The same script only accepts local Anvil (`31337`) or Polygon Amoy (`80002`).
Secrets are read from environment variables and must never be committed.

```bash
export DEPLOYER_ADDRESS=0x... # local unlocked Anvil account
export EXPECTED_CONTRACT_ADMIN=0x...
export CONTRACT_ADMIN=0x...
export ISSUER_ADDRESS=0x...

forge script script/DeployCertificateRegistry.s.sol \
  --rpc-url http://127.0.0.1:8545 --broadcast --unlocked
node scripts/export-artifacts.mjs --network=local --chain-id=31337
```

For Amoy, set `DEPLOYER_PRIVATE_KEY` in the environment, use the Amoy RPC URL,
and export with `--network=amoy --chain-id=80002`. Verify
`EXPECTED_CONTRACT_ADMIN` before broadcasting.
