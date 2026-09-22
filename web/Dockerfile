FROM node:24.21.0-slim

RUN corepack enable \
    && mkdir -p /app/web \
    && chown node:node /app/web

WORKDIR /app/web

COPY web/package.json web/pnpm-workspace.yaml web/pnpm-lock.yaml ./
COPY web/apps/web/package.json apps/web/package.json

USER node

RUN pnpm install --frozen-lockfile

COPY web/apps ./apps
COPY web/libs ./libs

WORKDIR /app/web
