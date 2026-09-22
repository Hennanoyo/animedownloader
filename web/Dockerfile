FROM node:24.21.0-slim

RUN corepack enable \
    && mkdir -p /app/web \
    && chown -R node:node /app/web

WORKDIR /app/web

COPY --chown=node:node web/package.json web/pnpm-workspace.yaml web/pnpm-lock.yaml ./
COPY --chown=node:node web/apps/web/package.json apps/web/package.json

USER node

RUN pnpm install --frozen-lockfile

COPY --chown=node:node web/apps ./apps
COPY --chown=node:node web/libs ./libs

WORKDIR /app/web
