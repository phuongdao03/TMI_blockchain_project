# Đề cử Tinh Hoa Việt V1 public preview

The canonical production hostname is `decu.tinhhoaviet.org.vn`. This release is
a controlled product preview. It serves the public nomination catalog,
Firebase registration/login and basic account access. Dossier uploads, object
storage, payment, internal operations, workers and blockchain transactions are
not available. The backend denies those mutations even if a client calls the API
directly.

> Account data is real. Enabling registration does store real account data: a
> Firebase identity and may create application user/session/audit records in
> PostgreSQL. If the release must store absolutely no user data, do not publish
> the login/register links; deploy a separate static showcase instead of this
> authenticated preview.

## Runtime topology

The VPS runs only:

- `nginx`: TLS termination and request limits; ports 80/443 only.
- `frontend`: Next.js standalone server.
- `backend`: FastAPI API and Alembic migration runner.
- `redis`: rate limits and short-lived application state.

PostgreSQL is an external managed service. The default Compose invocation does
not start Celery, the scheduler, ClamAV, Cloudinary upload processing, payOS or
blockchain services. Never add `--profile full` for V1.

## Image packaging

Images are built in GitHub Actions and pushed to GHCR with the commit SHA. The
VPS pulls them; it does not compile application source. BuildKit cache is used,
both containers run non-root, and runtime layers exclude tests, local `.env`
files and package-manager caches.

Approved uncompressed image budgets are:

- Backend: 150 MiB maximum (current local build: 110.5 MiB).
- Frontend: 90 MiB maximum (current local build: 59.2 MiB).

The frontend uses Next.js standalone output. Firebase web values and
`NEXT_PUBLIC_RELEASE_MODE=preview` are build-time values; changing them only in
the VPS environment does not change an existing image. Configure these GitHub
repository variables before the image workflow runs:

```text
NEXT_PUBLIC_FIREBASE_API_KEY
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
NEXT_PUBLIC_FIREBASE_APP_ID
```

These identify the Firebase web application and are not server private keys.
Restrict the API key in Google Cloud and add the production domain to Firebase
Authentication authorized domains. Enable only the intended Firebase sign-in
providers.

## VPS prerequisites

- Ubuntu LTS or another supported Linux host with Docker Engine and Compose v2.
- A non-root deploy user allowed to use Docker.
- At least 2 vCPU, 4 GiB RAM and 25 GiB free disk for a comfortable first
  release; monitor actual use before downsizing.
- DNS `A`/`AAAA` record for `decu.tinhhoaviet.org.vn` pointing to the VPS.
- Firewall/UFW allows SSH from the administration source and public TCP 80/443
  only. Do not expose 3000, 8000, 5432 or 6379.
- A TLS certificate at
  `${TLS_CERTIFICATE_DIR}/live/${APP_DOMAIN}/{fullchain.pem,privkey.pem}`.
- A managed PostgreSQL database with TLS, backup/PITR and connection limits.
- Read-only GHCR credentials for the deploy user.

This VPS already uses the operating-system Nginx for other applications. Do not
stop it and do not publish the project Nginx container on ports 80/443. The
preview Compose override binds frontend and backend only to
`127.0.0.1:3100` and `127.0.0.1:8100`; the host Nginx owns TLS and routing.

After DNS points to the VPS, bootstrap the certificate without interrupting the
existing virtual hosts:

```bash
install -d -m 755 /var/www/certbot
install -m 644 \
  /var/www/tmi_blockchain/infrastructure/nginx/decu.tinhhoaviet.org.vn.bootstrap.conf.example \
  /etc/nginx/sites-available/decu.tinhhoaviet.org.vn
ln -sfn /etc/nginx/sites-available/decu.tinhhoaviet.org.vn \
  /etc/nginx/sites-enabled/decu.tinhhoaviet.org.vn
nginx -t
systemctl reload nginx
certbot certonly --webroot -w /var/www/certbot \
  -d decu.tinhhoaviet.org.vn
install -m 644 \
  /var/www/tmi_blockchain/infrastructure/nginx/decu.tinhhoaviet.org.vn.conf.example \
  /etc/nginx/sites-available/decu.tinhhoaviet.org.vn
nginx -t
systemctl reload nginx
```

Certbot's system timer renews the certificate. Verify `certbot renew --dry-run`
and keep the Nginx reload hook enabled for renewed certificates.

## Server configuration

Keep the release under `/var/www/tmi_blockchain`. Copy
`infrastructure/.env.preview.example` to
`/var/www/tmi_blockchain/infrastructure/.env.preview`, fill every placeholder and
protect it:

```bash
chmod 600 /var/www/tmi_blockchain/infrastructure/.env.preview
bash /var/www/tmi_blockchain/infrastructure/scripts/validate-preview-environment.sh \
  /var/www/tmi_blockchain/infrastructure/.env.preview
```

Keep `EDGE_PROXY_MODE=host-nginx`, `FRONTEND_HOST_PORT=3100` and
`BACKEND_HOST_PORT=8100` aligned with the host Nginx virtual host. These ports
must remain loopback-only and must not be opened in UFW.

Generate independent random values of at least 32 characters for every
application secret. Do not reuse a Firebase key, database password or GHCR
token. Do not place secrets in Git, Docker build arguments or frontend
variables.

The preview needs PostgreSQL, Redis, Firebase project identity, application
session/CSRF secrets, PII/outbox encryption keys, an audit integrity key and an
engagement HMAC secret. It does not need Cloudinary, payOS, a contract address,
POL, an RPC URL or a blockchain signer.

## CI and deployment credentials

Configure the protected GitHub `production` environment with:

```text
PRODUCTION_DEPLOY_HOST
PRODUCTION_DEPLOY_USER
PRODUCTION_DEPLOY_SSH_KEY
PRODUCTION_SSH_KNOWN_HOSTS
GHCR_PULL_TOKEN
```

Use a restricted deploy key and a pre-recorded SSH host key. Do not disable
strict host verification. The delivery workflow builds and scans the images; the
manually approved production job syncs only deployment manifests and runs the
preview environment.

For a manual release on the VPS:

```bash
cd /var/www/tmi_blockchain
export PRODUCTION_ENV_FILE=/var/www/tmi_blockchain/infrastructure/.env.preview
bash infrastructure/scripts/deploy.sh <approved-commit-sha>
```

The script validates the environment, pulls immutable images, runs
`alembic upgrade head`, starts the stack, waits for container health and probes
the public HTTPS health endpoint. A failed health gate restores the previous
image tag automatically when one exists.

## Smoke and rollback

After deployment, verify:

1. `/`, `/works`, `/process`, `/policies`, `/login` and `/register` render over
   HTTPS without console/network errors.
2. `/health` and `/ready` are healthy and expose no configuration details.
3. One test account can verify email, sign in and sign out.
4. Dossier, payment, internal-operation and blockchain mutation requests return
   the preview `FEATURE_NOT_AVAILABLE` response.
5. Ports 3000, 8000, 5432 and 6379 are unreachable from the Internet.

Rollback images without automatically downgrading the database:

```bash
cd /var/www/tmi_blockchain
export PRODUCTION_ENV_FILE=/var/www/tmi_blockchain/infrastructure/.env.preview
bash infrastructure/scripts/rollback.sh <previous-commit-sha>
```

Keep the previous SHA, database backup status and operator contact in the
release record.

## Content and promotion rules

Publish only introductory nominations TMI has permission to display. Do not invent a
certificate number, transaction hash or verification status. Preview content
must remain labelled as introductory.

Promotion to `full` is a separate release. It requires payOS qualification,
staff MFA, document storage and malware scanning, Polygon contract/signing,
security/E2E evidence and the existing production go/no-go approval. Rebuild the
frontend with `NEXT_PUBLIC_RELEASE_MODE=full`; changing the VPS environment
alone is insufficient.

## Pre-DNS qualification

DNS is not required to build and test the release candidate. Before the record
is delegated, deploy the same immutable images to a temporary HTTPS hostname and
set `APP_BASE_URL` plus `CORS_ALLOWED_ORIGINS` to that exact origin. Add only
that temporary hostname to Firebase Authentication authorized domains.

Do not issue a certificate for `decu.tinhhoaviet.org.vn` or claim the canonical
URL is live until public DNS resolves to the selected ingress. At cutover:

1. add the canonical hostname to Firebase authorized domains;
2. publish the DNS record with a pre-approved TTL;
3. issue and verify TLS;
4. switch `APP_BASE_URL` and CORS to the canonical HTTPS origin;
5. rerun smoke, authentication and mutation-denial checks;
6. keep the temporary hostname only if it is access-controlled and documented.
