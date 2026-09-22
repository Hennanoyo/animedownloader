FROM ghcr.io/astral-sh/uv:0.12.17 AS uv

FROM mcr.microsoft.com/devcontainers/javascript-node:24-bookworm

COPY --from=uv /uv /uvx /usr/local/bin/

USER root

RUN corepack enable

USER node

RUN uv python install 3.14.7
RUN pnpm config set store-dir /home/node/.cache/pnpm/store --global

ENV PATH="/home/node/.local/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT="/home/node/.venvs/animedownloader-server"
