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
DATABASE_URL=postgresql+asyncpg://cns_local:cns-local-only@postgres:5432/cns_local
REDIS_URL=redis://redis:6379/0
BLOCKCHAIN_NETWORK=local
BLOCKCHAIN_CHAIN_ID=31337
BLOCKCHAIN_RPC_URL=http://anvil:8545
PAYMENT_PROVIDER=mock
PAYMENT_WEBHOOK_SECRET=<random-local-secret>
PAYMENT_CHECKOUT_BASE_URL=http://localhost:3000/payments/mock
FIREBASE_PROJECT_ID=cns-local
FIREBASE_AUTH_EMULATOR_HOST=firebase-emulator:9099
NEXT_PUBLIC_FIREBASE_API_KEY=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_PROJECT_ID=cns-local
NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL=http://localhost:9099
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=<Firebase Web app config>
NEXT_PUBLIC_FIREBASE_APP_ID=<Firebase Web app config>
NEXT_PUBLIC_OSM_TILE_URL=https://<approved-tile-provider>/{z}/{x}/{y}.png
NEXT_PUBLIC_OSM_TILE_ATTRIBUTION=<provider attribution required by its terms>
```

The local mock is not a payment processor and must never receive real money.

For production worksite maps, set `NEXT_PUBLIC_OSM_TILE_URL` and
`NEXT_PUBLIC_OSM_TILE_ATTRIBUTION` as GitHub repository variables before the
frontend image build. The URL must use HTTPS and include `{z}`, `{x}` and
`{y}`. Choose a provider that permits the expected traffic, supplies the
required attribution and can restrict any public browser token to the
production domain. These public variables are frozen into the Next.js image
at build time; changing only the VPS environment does not update the map.
Map tile requests reveal the viewed map area to the provider, including when
an admin inspects attendance evidence; review that data flow before choosing
an external provider, or use approved self-hosted tiles.
Without both values, the production UI shows a coordinate-entry fallback
instead of relying on volunteer OSM tiles. Verify tile requests and labels on
the deployed domain before approving the release.

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

| Area         | Variables                                                                                                                                                                                                                 | What to enter                                                                                                                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Database     | `DATABASE_URL`, `DATABASE_DIRECT_URL`                                                                                                                                                                                     | Managed PostgreSQL async URL and direct migration URL; use TLS.                                                                                                                                                                            |
| Sessions     | `JWT_SECRET`, `AUTH_CSRF_SECRET`, `AUTH_OUTBOX_ENCRYPTION_KEY`, `PII_ENCRYPTION_KEY`                                                                                                                                      | Unique random secrets per environment. Rotating them invalidates sessions or encrypted data as documented.                                                                                                                                 |
| Redis        | `REDIS_PASSWORD`, `REDIS_URL`                                                                                                                                                                                             | Strong password and `redis://:<password>@redis:6379/0`.                                                                                                                                                                                    |
| Google login | `FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_*`                                                                                                                                                                           | Enable Google in Firebase Authentication, copy the Web app config, and add `localhost` plus the production domain to Authorized domains. The backend verifies Firebase ID tokens; no service-account secret belongs in the frontend.       |
| Media        | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `MEDIA_SCANNER_HOST=clamav`, `MEDIA_SCANNER_PORT=3310`                                                                                            | Cloudinary production credentials and the internal ClamAV service. A full release fails configuration validation without Cloudinary credentials; `/ready` reports `cloudinary` or `clamav` as down when either integration is unavailable. |
| Email        | `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_TIMEOUT_SECONDS`                                                                                         | Verified sender and authenticated SMTP relay. Use STARTTLS with port `587` (`SMTP_USE_TLS=true`) or implicit TLS with port `465` (`SMTP_USE_SSL=true`), never both.                                                                        |
| Payments     | `PAYMENT_PROVIDER`, `PAYMENT_WEBHOOK_SECRET`, `PAYMENT_CHECKOUT_BASE_URL`                                                                                                                                                 | An implemented provider adapter, its signing secret, and an HTTPS checkout URL. `mock` is rejected outside local.                                                                                                                          |
| Blockchain   | `BLOCKCHAIN_NETWORK=polygon`, `BLOCKCHAIN_CHAIN_ID=137`, `BLOCKCHAIN_RPC_URL`, `CERTIFICATE_CONTRACT_ADDRESS`, `BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES`, `BLOCKCHAIN_SIGNER_MODE=human`, `BLOCKCHAIN_SIGNING_ENABLED=true` | Polygon RPC over HTTPS, an approved contract address/allowlist and human-controlled wallet signing. Keep `BLOCKCHAIN_SIGNER_PRIVATE_KEY` blank; the active verified signer wallet alone receives `ISSUER_ROLE`.                            |

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
addition to the web stack. Keep `RELEASE_MODE=preview` only for preview
releases; it deliberately does not start those full-profile services.

For production email delivery, verify the sender domain with the SMTP provider,
store the password only in `.env.production`, and keep the worker running. The
worker consumes encrypted outbox events and sends account, dossier, review,
council, payment, certificate and blockchain notifications. Validate the relay
from the container without printing credentials, then confirm delivery and
bounce handling in the provider dashboard.

## Public video stuck on the original MP4

The public work API may expose a video with `streamingUrl: null`. In that state
the viewer falls back to the retained MP4; it does not mean visitors must log
in. For the published work `52504e0f-09d9-45f4-a167-d3ca710a8dbc`, this was
observed on 2026-09-25: the fallback is a 4K, 52.6 MB source. Do not enable
bulk eager HLS generation or replace the source before the cause is known.

Read-only checks from the deployment directory (do not paste `.env.production`,
Cloudinary credentials, cookies or full log files into a ticket):

1. In the Super Admin publication editor, inspect the affected video's media
   status and failure code. `READY` should expose a derivative URL; `PENDING`
   should be picked up by the worker/scheduler, while `PROCESSING` needs a
   recent completion or an investigated worker interruption.
2. Confirm whether deployment is `RELEASE_MODE=full` without printing the
   environment file. A preview deployment intentionally does not start the
   `worker` and `scheduler` Compose services.
3. From `/var/www/tmi_blockchain`, with the same Compose environment used by
   deployment, inspect service health using `docker compose --env-file
   infrastructure/.env.production -f
   infrastructure/compose.production.yaml --profile full ps worker scheduler`.
   Do not start/restart them merely to make the check pass.
4. Inspect only recent relevant task logs using `docker compose --env-file
   infrastructure/.env.production -f infrastructure/compose.production.yaml --profile full
   logs --since=30m --tail=200 worker scheduler`; redact sensitive details
   before sharing. Look for `generate_public_media_derivative`,
   `reconcile_pending_public_media`, provider timeouts, memory kills and
   `PROVIDER_UNAVAILABLE`/`SOURCE_INTEGRITY_FAILED`.

If services are unhealthy, treat it as an operational incident and use the
approved deployment/rollback procedure. If they are healthy but the media is
still pending, inspect the queue and the specific media row with an authorized
read-only administrator; avoid manually changing database status. A code fix
or selective regeneration should follow the confirmed failure mode. Verify a
new `streamingUrl`, playback and seek on mobile before closing the incident.
