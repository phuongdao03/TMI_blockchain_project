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
3. Smoke login, dossier read, public verification and notification worker.
4. Monitor errors, P95 latency, queue backlog and pending blockchain age for 30
   minutes.

## Rollback

Use the protected GitHub Actions **Rollback** workflow with the previous
immutable image tag, or run `infrastructure/scripts/rollback.sh
<previous-commit-sha>` directly on the VPS. This changes only application
images, waits for health and records the release state. Do not automatically
downgrade the database. If the release migration is incompatible, follow its
reviewed Alembic downgrade plan after taking a fresh backup and confirming no
newer data would be lost.

Rollback immediately for data-integrity risk, security exposure, error rate
above twice baseline or P95 latency above 150% of baseline.
