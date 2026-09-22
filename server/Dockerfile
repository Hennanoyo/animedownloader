FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server

COPY server/pyproject.toml server/uv.lock ./
COPY server/apps/api/pyproject.toml apps/api/pyproject.toml
COPY server/apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY server/libs/config/pyproject.toml libs/config/pyproject.toml

RUN uv sync --all-packages --locked --no-install-workspace

COPY server/apps ./apps
COPY server/domains ./domains
COPY server/libs ./libs
COPY server/tests ./tests

RUN uv sync --all-packages --locked

WORKDIR /app/server
