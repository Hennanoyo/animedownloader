FROM node:24.21.0-slim

WORKDIR /app/web

RUN corepack enable

COPY web/package.json web/pnpm-workspace.yaml web/pnpm-lock.yaml ./
COPY web/apps/web/package.json apps/web/package.json

RUN pnpm install --frozen-lockfile

COPY web/apps ./apps
COPY web/libs ./libs

WORKDIR /app/web
