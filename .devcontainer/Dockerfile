FROM ghcr.io/astral-sh/uv:0.12.17 AS uv

FROM mcr.microsoft.com/devcontainers/javascript-node:24-bookworm

COPY --from=uv /uv /uvx /usr/local/bin/

USER vscode

RUN uv python install 3.14.7

RUN corepack enable

ENV PATH="/home/vscode/.local/bin:$PATH"
