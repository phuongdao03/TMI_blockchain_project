# Production deployment and rollback

## Preconditions

- The release uses an immutable commit SHA image tag.
- `.env.production` exists only on the server with mode `0600`.
- TLS certificates exist under `TLS_CERTIFICATE_DIR/live/APP_DOMAIN`.
- Neon PITR/backup status is green and the previous image tag is recorded.
- Staging smoke, migration upgrade/downgrade gate and image scan passed.
- Docker Compose v2, Bash, curl, rsync and flock are installed for the deploy
  user, and `/var/www/tmi_blockchain` is writable by that user.
- The deploy user has a GHCR login with package-read access. GitHub Actions
  supplies it via `GHCR_PULL_TOKEN`; never add it to `.env.production`.

## Deploy

1. Let the protected GitHub Actions workflow sync the release manifests and
   invoke `deploy.sh <commit-sha>` over SSH with a pinned host key.
2. The script validates the environment file, runs the approved Alembic
   migration, waits for Compose health and checks `https://APP_DOMAIN/health`.
   With `RELEASE_MODE=full`, it automatically enables the Compose `full` profile
   and waits for ClamAV, worker and scheduler; preview releases keep that
   profile disabled.
3. Smoke login, dossier read, public verification and notification worker.
4. Monitor errors, P95 latency, queue backlog and pending blockchain age for 30
   minutes.

### Attendance geolocation on the shared VPS

The deployment workflow copies `infrastructure/` to the VPS, but it does not
replace `/etc/nginx/sites-available/decu.tinhhoaviet.org.vn`. When the host
Nginx site is stale, it can add `geolocation=()` beside the frontend's
`geolocation=(self)` policy. Browsers apply the restrictive policy and block
attendance even when the user has allowed location.

After a change to the host Nginx template, update its active site separately:

```bash
sudo cp -a /etc/nginx/sites-available/decu.tinhhoaviet.org.vn \
  /etc/nginx/sites-available/decu.tinhhoaviet.org.vn.bak
sudo install -m 644 \
  /var/www/tmi_blockchain/infrastructure/nginx/decu.tinhhoaviet.org.vn.conf.example \
  /etc/nginx/sites-available/decu.tinhhoaviet.org.vn
sudo nginx -t && sudo systemctl reload nginx
curl -sSI https://decu.tinhhoaviet.org.vn/login | grep -i '^permissions-policy:'
```

The last command must show `geolocation=(self)` once and must not show
`geolocation=()`. If `nginx -t` fails, restore the `.bak` file, test again and
reload. Check for a second policy in other active Nginx config or an outer proxy
if the response still contains `geolocation=()`.

## Rollback

Use the protected GitHub Actions **Rollback** workflow with the previous
immutable image tag, or run
`infrastructure/scripts/rollback.sh <previous-commit-sha>` directly on the VPS.
This changes only application images, waits for health and records the release
state. Do not automatically downgrade the database. If the release migration is
incompatible, follow its reviewed Alembic downgrade plan after taking a fresh
backup and confirming no newer data would be lost.

Rollback immediately for data-integrity risk, security exposure, error rate
above twice baseline or P95 latency above 150% of baseline.
