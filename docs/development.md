# Development

## Environment

- Windows host
- WSL2 Ubuntu
- VSCode Dev Containers
- Docker Compose

The application is developed and tested inside the containerized development environment.

## Monorepo

The repository contains two package-management domains:

- `web/`: pnpm workspace
- `server/`: uv workspace

Use the root `justfile` as the preferred interface for common operations.

## Initial Workspace

The frontend application currently lives at `web/apps/web`.

The backend workspace currently contains:

- `server/apps/api`
- `server/apps/worker`
- `server/libs/config`

The `server/domains` layer is reserved for domain packages that will be introduced as features are implemented.

## Local Stack

`compose.yaml` provides:

- `web`: Vite development server
- `api`: FastAPI development server
- `worker`: Taskiq worker backed by Redis
- `db`: PostgreSQL 18.6
- `redis`: Redis 8
- `storage`: single-node SeaweedFS with Filer

The development containers mount the repository at `/app`. Backend settings load `/app/server/.env` when the file exists.

Copy `server/.env.example` to `server/.env` when local overrides are required.

## Commands

Start the stack:

```bash
just up
```

Stop it:

```bash
just down
```

Run repository checks:

```bash
just check
```

## Lockfiles

Lockfiles are source-controlled artifacts.

When dependencies are added or changed, regenerate the appropriate workspace lockfile and commit it with the dependency change:

- `web/pnpm-lock.yaml`
- `server/uv.lock`

The initial CI workflow temporarily falls back to non-frozen dependency resolution when a lockfile does not yet exist. Once the initial lockfiles are committed, CI should use locked installs exclusively.

## CI Philosophy

GitHub Actions is the deterministic verification layer.

AI-assisted development should follow:

1. Inspect the repository and relevant documentation.
2. Implement a focused change.
3. Run focused local checks.
4. Commit/push through the normal branch workflow.
5. Let GitHub Actions run the applicable checks.
6. Inspect failed job logs.
7. Fix the root cause.
8. Re-run verification.

CI should not depend on live torrent downloads or large real-world media files.

Use small fixtures for media integration/smoke tests and deterministic fixtures for external protocols.
