# Infrastructure

Local containers, Nginx configuration, and deployment manifests belong here. The
approved runtime topology contains Nginx, frontend, backend, Celery worker,
scheduler, and Redis containers, with NeonDB, Cloudinary, and Polygon RPC as
managed external services.

Local development uses the root `compose.yaml`. Production uses immutable
backend/frontend images with `infrastructure/compose.production.yaml`; copy
`.env.production.example` to the server secret store as `.env.production` and
replace every `replace` value before validation.

Deployment and rollback commands are documented in
`docs/runbooks/deployment-and-rollback.md`. Monitoring, backup validation and
incident procedures live under `infrastructure/monitoring` and `docs/runbooks`.
Only Nginx publishes host ports in production; PostgreSQL, Cloudinary and the
Polygon RPC remain managed external services.
