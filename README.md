# TMI Blockchain Certificate Platform

Monorepo for the TMI Group blockchain-verifiable digital asset certificate
platform.

## Repository layout

- `frontend/` — Next.js web application (initialized in TASK-0005).
- `backend/` — FastAPI modular monolith and workers (initialized in TASK-0003).
- `contracts/` — Solidity contracts and deployment artifacts.
- `infrastructure/` — Local and production infrastructure configuration.

Frontend code must communicate with the backend API; it must never access the
database or blockchain directly. Backend modules use repository interfaces for
data access and services for use-case orchestration.

## Prerequisites

- Node.js `24.18.0`
- npm `11.16.0`
- Python `3.12.8`

The exact versions are recorded in `.nvmrc`, `.node-version`, `.python-version`,
and `package.json`.

## Local setup

Install the pinned root tooling from a clean checkout:

```bash
npm ci
```

Run the repository quality gates:

```bash
npm run lint
npm run typecheck
npm test
```

Use `npm run format` to apply formatting.

## Local containers

Copy the environment contract, then start the currently executable local stack:

```bash
cp .env.example .env
docker compose up --build
```

This starts the backend API, Celery worker and scheduler, Redis, and Anvil.
Check container state with `docker compose ps`; the backend is ready when
`http://localhost:8000/ready` returns HTTP 200. Stop and remove containers with
`docker compose down`.

The `frontend` and `nginx` services are isolated in the `frontend` profile until
TASK-0005 creates the Next.js application. After that task:

```bash
docker compose --profile frontend up --build
```

Local hot reload is enabled only for the application source bind mounts.

Never commit `.env` files, private keys, certificates, tokens, or generated
build output.
