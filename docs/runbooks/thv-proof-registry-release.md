# THVProofRegistry - Polygon Mainnet release runbook

## Scope and safety boundary

`THVProofRegistry` is an append-only Polygon PoS registry for approved asset proof hashes. It never stores files, URLs, dossier JSON, personal data, seed phrases or a human signer's private key on-chain.

This runbook supports an isolated Anvil check and a direct Polygon Mainnet release. The release script refuses every chain other than Polygon `137` and validates an immutable release commit before broadcasting.

## Fixed governance identities

| Purpose | Wallet |
| --- | --- |
| `DEFAULT_ADMIN_ROLE` | `0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe` |
| Initial `VERIFIER_ROLE` | `0xBfA38182f0D24589e7898DD4892C58c3FDa58042` |

Use a third wallet as the deployment operator. It must fund and create the contract only; it receives neither role and must match `EXPECTED_DEPLOYER`. The human signer wallet remains external to THV and never needs a private key in the application.

## Prepare the secret environment

From `contracts`, copy `config/thv-proof-registry.polygon.env.example` to a secret, ignored file on the release host. Do not put that file in Git.

```dotenv
BLOCKCHAIN_NETWORK=polygon
BLOCKCHAIN_CHAIN_ID=137
BLOCKCHAIN_RPC_URL=https://approved-polygon-mainnet-rpc
ADMIN_WALLET_ADDRESS=0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe
SIGNER_WALLET_ADDRESS=0xBfA38182f0D24589e7898DD4892C58c3FDa58042
EXPECTED_DEPLOYER=<separate-deployer-public-address>
DEPLOYER_PRIVATE_KEY=0x<64-hex-characters-from-secret-manager>
POLYGONSCAN_API_KEY=<explorer-api-key>
MINIMUM_DEPLOYER_BALANCE_WEI=1000000000000000000
THV_PROOF_REGISTRY_TEST_MODE=false
```

`DEPLOYER_PRIVATE_KEY` belongs only to the isolated release operator. The script reads it from the process environment for Foundry's `startBroadcast`; it does not pass it as a command-line argument. The human verifier wallet remains external to the application.

Before broadcasting, restrict the RPC provider key to the production server/IP and allowed origin, then verify the endpoint:

```bash
cast chain-id --rpc-url "$BLOCKCHAIN_RPC_URL"
```

It must return `137`.

## Create the immutable release

The Mainnet plan refuses untracked or changed release inputs. Commit the reviewed THV release files, then use that exact commit:

```bash
git rev-parse HEAD
export SOURCE_COMMIT="$(git rev-parse HEAD)"
```

The locked inputs include the contract, deployment script, tests, role verifier, preflight, provenance exporter, Foundry configuration and locked package files.

## Optional local Anvil smoke test

Use the Anvil template only. It accepts test identities only when `THV_PROOF_REGISTRY_TEST_MODE=true` and chain ID is `31337`.

```bash
anvil
set -a
source .env.thv-proof-registry.anvil
set +a
bash scripts/deploy-thv-proof-registry.sh
```

## Direct Polygon Mainnet deployment

The command first runs `npm ci --ignore-scripts`, then build/tests, pins the release plan, checks RPC chain `137`, estimates the deployment cost, requires the larger of `MINIMUM_DEPLOYER_BALANCE_WEI` and twice the live estimate, broadcasts, checks deployed runtime bytecode, verifies roles, then submits source verification.

Use at least `1 POL` in the deployer wallet for the first deployment and retain operational POL in the Admin and Signer wallets for later role or proof transactions. The live preflight calculation remains the source of truth.

```bash
cd contracts
set -a
source /secure/path/.env.thv-proof-registry.polygon
set +a
export SOURCE_COMMIT="$(git rev-parse HEAD)"
export MAINNET_DEPLOY_CONFIRMATION=DEPLOY_THV_PROOF_REGISTRY_TO_POLYGON_MAINNET
bash scripts/deploy-thv-proof-registry.sh --confirm-mainnet
```

The first irreversible action is the `forge script --broadcast` call inside that command. Keep the RPC and private key in the operator environment; never paste them into chat, source files or shell history.

If a provider or explorer outage happens after broadcast, do not delete `broadcast/DeployTHVProofRegistry.s.sol/137/run-latest.json` and do not invoke Foundry directly a second time. Re-run the wrapper command above: it will only resume postflight after the saved evidence, deployer, on-chain runtime bytecode, and role assignments match the immutable plan. Incompatible evidence aborts before any new contract is created.

## Post-deployment evidence

The deployment command writes a reproducible release manifest to `contracts/artifacts/releases/polygon/thv-proof-registry-manifest.json`, including the deployed address, transaction hash, role holders, ABI hash and compiled bytecode hashes. Put the deployed address into the production backend secret environment as:

```dotenv
THV_PROOF_REGISTRY_CONTRACT_ADDRESS=<deployed-address>
```

To re-check deployed roles independently:

```bash
THV_PROOF_REGISTRY_CONTRACT_ADDRESS=<deployed-address> \
  node scripts/verify-thv-proof-registry-roles.mjs
```

If explorer verification must be retried after a provider outage, use:

```bash
constructor_args="$(cast abi-encode 'constructor(address,address)' "$ADMIN_WALLET_ADDRESS" "$SIGNER_WALLET_ADDRESS")"
forge verify-contract <deployed-address> src/THVProofRegistry.sol:THVProofRegistry \
  --chain 137 --watch --verifier etherscan \
  --etherscan-api-key "$POLYGONSCAN_API_KEY" \
  --constructor-args "$constructor_args"
```

## Operational role rotation

Only the Admin wallet can grant or revoke `VERIFIER_ROLE`. To rotate the human signer, grant the new signer first, validate a proof record, then revoke the prior signer. Never redeploy only to rotate a verifier wallet.
