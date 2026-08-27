FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip wheel --wheel-dir /wheels .


FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH

RUN apk upgrade --no-cache \
    && addgroup -g 10001 -S app \
    && adduser -u 10001 -S -D -G app app

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-compile /wheels/*.whl \
    && rm -rf /wheels \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip* \
        /usr/local/bin/pip*

COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
