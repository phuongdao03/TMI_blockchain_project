# CI/CD operations

Pull requests run formatting, lint, strict type checks, backend/frontend tests,
critical browser E2E, production build, dependency audit, Foundry tests and a
reversible PostgreSQL migration gate.

The `document-proof-production-gate` job also runs the integrated encrypted
document qualification with `npm run gate:document-proof`. It uploads a redacted
result matrix and checksum for 30 days. Any failed category blocks immutable
image publication. The artifact is one input to the integrated release review,
not an independent production approval.

Pushes to `main` build immutable SHA-tagged images and deploy to the protected
`staging` environment. Production runs only through `workflow_dispatch` with an
existing immutable tag and approval on the protected `production` environment.

Required repository secrets:

- `STAGING_DEPLOY_HOST`, `STAGING_DEPLOY_USER`, `STAGING_DEPLOY_SSH_KEY`
- `PRODUCTION_DEPLOY_HOST`, `PRODUCTION_DEPLOY_USER`,
  `PRODUCTION_DEPLOY_SSH_KEY`
- `STAGING_SSH_KNOWN_HOSTS`, `PRODUCTION_SSH_KNOWN_HOSTS` containing the pinned
  OpenSSH host-key line for each VPS
- `GHCR_PULL_TOKEN`, a package-read token used only by the VPS deploy user to
  pull immutable images from GitHub Container Registry

Production credentials must not be shared with CI or staging. Failed browser
runs and each release produce short-lived diagnostic or rollback artifacts. The
PostgreSQL service in CI uses a repository-local ephemeral credential that is
never accepted by staging or production.

## Secret scanning

The `Secret scan` job checks both full Git history and the checked-out working
tree with the pinned `ghcr.io/gitleaks/gitleaks:v8.30.1` image. Output is always
redacted. The same script creates a runtime-only synthetic canary and requires
the scanner to reject it, proving the gate is active.

Run locally when Docker is available:

```bash
bash infrastructure/scripts/verify-gitleaks.sh
```

Do not add a baseline or allowlist merely to make CI green. Confirm whether a
finding is live, rotate it when necessary, then add the narrowest reviewed
exception only for a proven false positive.

## Release flow

1. A pull request runs all quality, security, migration and browser gates.
2. A successful push to `main` publishes backend and frontend images tagged by
   the commit SHA, syncs only deployment manifests and public contract ABI to
   staging, then deploys that exact SHA.
3. Production is a protected manual workflow. Enter an image tag that already
   exists in GHCR; the workflow never rebuilds a production tag.
4. The deploy script serializes releases with `flock`, validates Compose and the
   0600 environment file, waits for container health, then verifies local TLS
   health at `https://APP_DOMAIN/health`.
5. If the new application images fail health checks, the script restores the
   previously recorded image tag. Database downgrade is never automatic, so
   migrations must follow an expand/contract compatibility strategy.

The VPS must have Docker Compose v2, Bash, curl, rsync, flock, a pre-created
`/var/www/tmi_blockchain` directory owned by the deploy user, and a valid
`.env.production` file that is never copied from CI.
