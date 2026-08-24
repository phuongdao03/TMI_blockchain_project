# Runtime environment setup

The repository no longer enables preview users or mock data in the frontend. The
only mock implementation is the payment gateway used by local tests. It is
blocked for staging and production.

## Local development

```powershell
Copy-Item .env.example .env
npm run local:bootstrap
npm run local:smoke
```

On Linux/CI, run `./infrastructure/scripts/bootstrap-local.sh` and then
`./infrastructure/scripts/smoke-local.sh`. Stop the stack with
`npm run local:down` (or `docker compose --profile frontend down`). Named
database, Redis and Mailpit volumes are retained unless an operator explicitly
adds `--volumes`.

The default Compose stack is self-contained: PostgreSQL (`5432`), Redis, Mailpit
SMTP/UI (`1025`/`8025`), Firebase Auth Emulator (`9099`), Anvil (`8545`), the
migration gate, backend, worker and scheduler. The application containers always
use the Compose PostgreSQL and Firebase emulator rather than database or
Firebase endpoints from `.env`; this prevents local startup from mutating an
external environment.

PostgreSQL, Redis and Mailpit use named volumes. Application and emulator
containers use read-only root filesystems with explicit temporary filesystems;
the backend, worker, scheduler, Anvil and Firebase emulator run as non-root
users. The official PostgreSQL and Mailpit images retain their image-defined
runtime users because forcing host UID values breaks their entrypoints.

Keep these local-only values:

```dotenv
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://tmi_local:tmi-local-only@postgres:5432/tmi_local
REDIS_URL=redis://redis:6379/0
BLOCKCHAIN_NETWORK=local
BLOCKCHAIN_CHAIN_ID=31337
BLOCKCHAIN_RPC_URL=http://anvil:8545
PAYMENT_PROVIDER=mock
PAYMENT_WEBHOOK_SECRET=<random-local-secret>
PAYMENT_CHECKOUT_BASE_URL=http://localhost:3000/payments/mock
FIREBASE_PROJECT_ID=tmi-local
FIREBASE_AUTH_EMULATOR_HOST=firebase-emulator:9099
NEXT_PUBLIC_FIREBASE_API_KEY=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_PROJECT_ID=tmi-local
NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL=http://localhost:9099
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_APP_ID=<Firebase Web app config>
```

The local mock is not a payment processor and must never receive real money.

Bootstrap does not create application accounts or credentials. To create the
first local Super Admin, choose an email and enter a new password interactively:

```powershell
docker compose exec backend python -m app.scripts.bootstrap_local_super_admin --email admin@local.test
```

The command is limited to `APP_ENV=local` with the Firebase Auth Emulator. It
does not run in staging or production, never prints the password, and refuses to
promote an existing non-admin account. Use the normal application flows for
Viewer/User registration and the staff-management flow to onboard Moderators.

Bootstrap writes only the deployed local contract address and allowlist to
`.runtime/local-contract.env`; it never extracts or injects an Anvil private
key. Link a disposable wallet through the Super Admin signing screen to test the
same human-signing model used in production.

Useful local URLs: application `http://localhost:3000`, proxied stack
`http://localhost:8080`, API `http://localhost:8000`, and Mailpit
`http://localhost:8025`.

## Production prerequisites

Copy `infrastructure/.env.production.example` to the VPS secret store as
`.env.production`, then replace every `replace` value. Do not commit that file.

Generate application secrets on the VPS (never paste them into chat or source):

```powershell
openssl rand -base64 32 # JWT_SECRET
openssl rand -base64 32 # AUTH_CSRF_SECRET
openssl rand -base64 32 # AUTH_OUTBOX_ENCRYPTION_KEY
openssl rand -base64 32 # PII_ENCRYPTION_KEY
openssl rand -base64 32 # ENGAGEMENT_VISITOR_HMAC_SECRET
```

Required services and values:

| Area         | Variables                                                                                                                                                                               | What to enter                                                                                                                                                                                                                        |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Database     | `DATABASE_URL`, `DATABASE_DIRECT_URL`                                                                                                                                                   | Managed PostgreSQL async URL and direct migration URL; use TLS.                                                                                                                                                                      |
| Sessions     | `JWT_SECRET`, `AUTH_CSRF_SECRET`, `AUTH_OUTBOX_ENCRYPTION_KEY`, `PII_ENCRYPTION_KEY`                                                                                                    | Unique random secrets per environment. Rotating them invalidates sessions or encrypted data as documented.                                                                                                                           |
| Redis        | `REDIS_PASSWORD`, `REDIS_URL`                                                                                                                                                           | Strong password and `redis://:<password>@redis:6379/0`.                                                                                                                                                                              |
| Google login | `FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_*`                                                                                                                                         | Enable Google in Firebase Authentication, copy the Web app config, and add `localhost` plus the production domain to Authorized domains. The backend verifies Firebase ID tokens; no service-account secret belongs in the frontend. |
| Media        | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `MEDIA_SCANNER_HOST=clamav`, `MEDIA_SCANNER_PORT=3310`                                                         | Cloudinary production credentials and the internal ClamAV service. A full release fails configuration validation without Cloudinary credentials; `/ready` reports `cloudinary` or `clamav` as down when either integration is unavailable. |
| Email        | `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`                                                                                                                                                 | TLS-capable SMTP relay and verified sender.                                                                                                                                                                                          |
| Payments     | `PAYMENT_PROVIDER`, `PAYMENT_WEBHOOK_SECRET`, `PAYMENT_CHECKOUT_BASE_URL`                                                                                                               | An implemented provider adapter, its signing secret, and an HTTPS checkout URL. `mock` is rejected outside local.                                                                                                                    |
| Blockchain   | `BLOCKCHAIN_NETWORK=polygon`, `BLOCKCHAIN_CHAIN_ID=137`, `BLOCKCHAIN_RPC_URL`, `CERTIFICATE_CONTRACT_ADDRESS`, `BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES`, `BLOCKCHAIN_SIGNER_MODE=human`, `BLOCKCHAIN_SIGNING_ENABLED=true` | Polygon RPC over HTTPS, an approved contract address/allowlist and human-controlled wallet signing. Keep `BLOCKCHAIN_SIGNER_PRIVATE_KEY` blank; the active verified signer wallet alone receives `ISSUER_ROLE`. |

## Current production blocker

Task 0701 explicitly left the production payment provider out of scope. The
backend now fails closed instead of silently routing staging/production orders
to `MockPaymentGateway`. Choose a provider (for example the organisation's
approved bank/payment gateway), implement its `PaymentGateway` adapter and
webhook verification, then set `PAYMENT_PROVIDER` to that adapter name before
deploying.

After filling the secret store, validate without printing secrets:

```powershell
docker compose --env-file .env.production -f infrastructure/compose.production.yaml config
```

Then run migrations, deploy immutable images, and verify `/ready` plus a signed
provider webhook in staging before production rollout.

`RELEASE_MODE=full` enables the Compose `full` profile during deployment and
rollback. It starts and waits for ClamAV, the worker and the scheduler in
addition to the web stack. Keep `RELEASE_MODE=preview` only for preview releases;
it deliberately does not start those full-profile services.
