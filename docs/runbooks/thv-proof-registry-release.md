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

The application runtime must use the full workflow and allow both active
contracts (omit the legacy address only after its certificate routes are
retired):

```dotenv
APP_ENV=production
RELEASE_MODE=full
BLOCKCHAIN_NETWORK=polygon
BLOCKCHAIN_CHAIN_ID=137
BLOCKCHAIN_RPC_URL=https://<restricted-polygon-mainnet-rpc>
CERTIFICATE_CONTRACT_ADDRESS=<legacy-certificate-registry-address>
THV_PROOF_REGISTRY_CONTRACT_ADDRESS=<deployed-thv-proof-registry-address>
BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES=<legacy-address>,<proof-registry-address>
BLOCKCHAIN_SIGNER_MODE=human
BLOCKCHAIN_SIGNING_ENABLED=true
BLOCKCHAIN_REQUIRED_CONFIRMATIONS=3
BLOCKCHAIN_TRANSACTION_INTENT_TTL_SECONDS=300
```

Recreate `backend`, `worker` and `frontend` containers after changing this
file. Confirm the variables reached the backend without printing the RPC URL:

```bash
docker compose --env-file infrastructure/.env.production \
  -f infrastructure/compose.production.yaml exec backend \
  python -c "from app.core.config import get_settings; s=get_settings(); print(s.release_mode, s.blockchain_network, s.blockchain_chain_id, s.thv_proof_registry_contract_address, s.blockchain_signer_mode, s.blockchain_signing_enabled)"
```

Expected values are `full polygon 137 <deployed-address> human True`.

## Bootstrap the first application Super Admin

Create the Firebase credential in Firebase Console first. The application
bootstrap only binds that existing Firebase UID to the application database;
it never accepts or stores the Firebase password. Run migrations, then execute
the guarded command inside the production backend container:

```bash
docker compose --env-file infrastructure/.env.production \
  -f infrastructure/compose.production.yaml exec backend \
  python -m app.scripts.bootstrap_production_super_admin \
  --email <exact-firebase-email> \
  --firebase-uid <exact-firebase-uid> \
  --confirm BOOTSTRAP_PRODUCTION_SUPER_ADMIN
```

The command is idempotent for the same identity and refuses a UID collision or
a second distinct Super Admin. Sign out and sign in again after it succeeds so
the application session is rebuilt with the new role.

## One-time Firebase email-verification bootstrap for Super Admin

Use this only when an existing, active `SUPER_ADMIN` Firebase identity cannot
complete the normal verification email flow. It is not a replacement for email
verification and must never be exposed as an API, UI action, or normal-user
bypass.

The command rejects every account except the exact database-bound Firebase UID
and email that already has `SUPER_ADMIN`. It rejects inactive/deleted accounts,
does not create credentials or change roles, revokes Firebase and application
sessions after a successful verification lookup, and writes immutable requested
and completed audit records. A retry reconciles a partial prior run safely.

The production runtime intentionally has read-only Firebase verification scope.
Run this through a temporary container with a Firebase Admin credential mounted
for this one command only. Keep the credential outside the repository and do
not add it to `infrastructure/.env.production` or the long-running services.

1. Deploy the image that contains
   `verify_production_super_admin_email.py`.
2. Create a temporary Firebase service-account credential for the same Firebase
   project with the minimum approved user-management permission. Firebase's
   built-in `roles/firebaseauth.admin` includes `firebaseauth.users.update`;
   remove the role and revoke/delete the key immediately after this operation.
3. Store that JSON file on the VPS with owner-only permissions, then run:

```bash
export PRODUCTION_ENV_FILE=/var/www/tmi_blockchain/infrastructure/.env.production
export FIREBASE_ADMIN_CREDENTIAL_FILE=/root/tmi-secrets/firebase-auth-admin.json

docker compose \
  --env-file "$PRODUCTION_ENV_FILE" \
  -f infrastructure/compose.production.yaml \
  run --rm --no-deps --user 0:0 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/firebase-admin.json \
  -v "$FIREBASE_ADMIN_CREDENTIAL_FILE:/run/secrets/firebase-admin.json:ro" \
  backend \
  python -m app.scripts.verify_production_super_admin_email \
  --email <exact-firebase-email> \
  --firebase-uid <exact-firebase-uid> \
  --confirm VERIFY_PRODUCTION_SUPER_ADMIN_FIREBASE_EMAIL
```

The container is temporary and the mounted credential is read-only. The
`--user 0:0` override exists solely so it can read an owner-only host secret;
it does not modify the running backend service. After success, remove the
temporary host file and revoke/delete the Firebase service-account key. Then
fully sign out and sign in again: an already-issued Firebase ID token retains
its old `email_verified` claim until a new token is issued.

## Recover Super Admin after Firebase account deletion

Do not hard-delete the former application user: it can own audit history and
other protected records. If its Firebase credential was irrecoverably deleted,
the following guarded recovery makes the supplied Firebase identity the sole
Super Admin. It removes the former Super Admin role, marks every former Super
Admin account as deleted in the application, revokes its active sessions, and
writes immutable audit records.

Create the replacement Firebase account first, verify its UID in Firebase
Console, then run this only after deploying the image that contains the command:

```bash
docker compose --env-file infrastructure/.env.production \
  -f infrastructure/compose.production.yaml exec backend \
  python -m app.scripts.recover_production_super_admin \
  --email <exact-replacement-firebase-email> \
  --firebase-uid <exact-replacement-firebase-uid> \
  --confirm RECOVER_PRODUCTION_SUPER_ADMIN_AFTER_FIREBASE_DELETION
```

This is an emergency recovery operation, not a normal staff-management flow.
Do not use it to add a second Super Admin. Sign out and sign in again with the
replacement account after the command completes.

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
