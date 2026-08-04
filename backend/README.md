# Backend

This root will contain the FastAPI modular monolith, Celery workers, and Alembic
migrations.

The approved module shape is:

```text
app/
  api/v1/
  core/
  db/
  modules/
  workers/
  tests/
alembic/
```

Each business module owns its models, schemas, repository, service, router,
exceptions, and tests. Routers validate and translate HTTP requests;
repositories exclusively handle database access; services orchestrate
transactions and business rules.

## Runtime

Install the backend and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn app.main:app --reload
```

Public operational endpoints:

- `GET /health` returns the standard success envelope when the process is alive.
- `GET /ready` checks Redis and Anvil, returning HTTP 200 when both are
  available and the standard `SERVICE_NOT_READY` error envelope with HTTP 503
  otherwise.

Both endpoints return `X-Request-ID`. A valid UUID supplied by the caller is
preserved; otherwise the middleware generates one. Application logs are JSON and
must not include credentials, tokens, private keys, or request payloads.

Run backend quality gates from this directory:

```bash
ruff check .
mypy app
pytest app/tests
```

## Database migrations

Runtime repositories use the pooled `DATABASE_URL`. Alembic exclusively uses the
direct `DATABASE_DIRECT_URL`; both values must use an async SQLAlchemy URL such
as `postgresql+asyncpg://...`.

Apply or roll back migrations from `backend/`:

```bash
python -m alembic upgrade head
python -m alembic downgrade -1
```

Domain services own transaction boundaries. Repository dependencies receive an
`AsyncSession` from `app.db.session` and must not create independent engines.
