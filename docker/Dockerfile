# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.11.8 AS uv

FROM python:3.14.4-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly \
    uv sync --locked --no-install-project

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY management/__init__.py management/manage.py ./management/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM python:3.14.4-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv

RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin --no-create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src
COPY --from=builder --chown=app:app /app/management /app/management

WORKDIR /app
USER app

EXPOSE 8000
